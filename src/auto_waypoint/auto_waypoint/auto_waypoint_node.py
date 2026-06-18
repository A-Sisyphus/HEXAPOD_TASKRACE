#!/usr/bin/env python3
"""
自动路点导航节点
从 waypoint_config.yaml 读取初始位姿与目标路点，按顺序导航，
支持失败重试后跳过，单次遍历完成后退出。
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from std_msgs.msg import Float32
from tf_transformations import quaternion_from_euler
from auto_waypoint.gpio_control import pick_up, put_down
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType

class AutoWaypointNode(BasicNavigator):
    def __init__(self, node_name='auto_waypoint_node'):
        super().__init__(node_name)

        # 声明参数（默认值会被 YAML 覆盖）
        self.declare_parameter('initial_point', [0.0, 0.0, 0.0])
        self.declare_parameter('target_points', [0.0, 0.0, 0.0])
        self.declare_parameter('max_retries', 3)
        self.declare_parameter('body_height_topic', '/hexapod/body_height')

        self.initial_point_ = self.get_parameter('initial_point').value
        self.target_points_ = self.get_parameter('target_points').value
        self.max_retries_ = self.get_parameter('max_retries').value
        self.body_height_topic_ = self.get_parameter('body_height_topic').value

        self.body_height_pub_ = self.create_publisher(
            Float32, self.body_height_topic_, 10)

        # 动态参数客户端（修改 controller_server 参数用）
        self.param_client_ = self.create_client(
            SetParameters, '/controller_server/set_parameters')

        self.get_logger().info(f'初始位姿: {self.initial_point_}')
        self.get_logger().info(f'目标路点原始数据长度: {len(self.target_points_)}')
        self.get_logger().info(f'最大重试次数: {self.max_retries_}')

    # ======================== 工具方法 ========================

    def get_pose_by_xyyaw(self, x: float, y: float, yaw: float) -> PoseStamped:
        """将 x, y, yaw 转为 map 坐标系下的 PoseStamped"""
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        q = quaternion_from_euler(0.0, 0.0, yaw)
        pose.pose.orientation.x = q[0]
        pose.pose.orientation.y = q[1]
        pose.pose.orientation.z = q[2]
        pose.pose.orientation.w = q[3]
        return pose

    def get_target_points(self) -> list:
        """解析 flat array 参数为 [[x, y, yaw], ...] 列表"""
        points = []
        self.target_points_ = self.get_parameter('target_points').value
        n = len(self.target_points_)
        if n % 3 != 0:
            self.get_logger().error(
                f'target_points 长度 {n} 不是 3 的倍数，请检查 YAML 配置')
            return points

        for i in range(n // 3):
            x = self.target_points_[i * 3]
            y = self.target_points_[i * 3 + 1]
            yaw = self.target_points_[i * 3 + 2]
            points.append([x, y, yaw])
            self.get_logger().info(f'路点 {i}: ({x:.2f}, {y:.2f}, {yaw:.2f})')
        return points

    # ======================== 导航逻辑 ========================

    def init_robot_pose(self):
        """设置初始位姿并等待 Nav2 就绪"""
        self.get_logger().info('正在设置初始位姿...')
        self.initial_point_ = self.get_parameter('initial_point').value
        init_pose = self.get_pose_by_xyyaw(
            self.initial_point_[0],
            self.initial_point_[1],
            self.initial_point_[2])
        self.setInitialPose(init_pose)
        self.waitUntilNav2Active()
        self.get_logger().info('Nav2 已激活，初始位姿设置完成')

    # ======================== 动态参数 ========================

    def set_rotation_shim_threshold(self, value: float) -> bool:
        """动态修改 controller_server 的 angular_dist_threshold"""
        if not self.param_client_.wait_for_service(timeout_sec=3.0):
            self.get_logger().error('无法连接 controller_server 参数服务')
            return False

        param = Parameter()
        param.name = 'FollowPath.angular_dist_threshold'
        param.value.type = ParameterType.PARAMETER_DOUBLE
        param.value.double_value = value

        req = SetParameters.Request()
        req.parameters = [param]

        future = self.param_client_.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)

        if future.result() is not None:
            results = future.result().results
            if results and results[0].successful:
                self.get_logger().info(
                    f'已设置 angular_dist_threshold = {value:.2f}')
                return True
            else:
                self.get_logger().error(
                    f'设置 angular_dist_threshold 失败: {results[0].reason if results else "无响应"}')
                return False
        self.get_logger().error('设置 angular_dist_threshold 超时')
        return False

    def nav_to_pose_with_retry(self, target_pose: PoseStamped,
                               waypoint_index: int) -> bool:
        """导航到目标位姿，失败时自动重试，返回是否成功"""
        for attempt in range(1, self.max_retries_ + 1):
            self.get_logger().info(
                f'路点 {waypoint_index} 第 {attempt}/{self.max_retries_} 次尝试...')
            self.waitUntilNav2Active()
            self.goToPose(target_pose)

            # 等待导航完成
            while not self.isTaskComplete():
                rclpy.spin_once(self, timeout_sec=0.1)
                feedback = self.getFeedback()
                if feedback and feedback.estimated_time_remaining.sec >= 0:
                    self.get_logger().info(
                        f'  预计剩余: '
                        f'{feedback.estimated_time_remaining.sec} s',
                        throttle_duration_sec=5.0)

            result = self.getResult()
            if result == TaskResult.SUCCEEDED:
                self.get_logger().info(
                    f'路点 {waypoint_index} 导航成功 ✓')
                return True
            elif result == TaskResult.CANCELED:
                self.get_logger().warn(
                    f'路点 {waypoint_index} 第 {attempt} 次被取消，'
                    f'准备重试...')
            elif result == TaskResult.FAILED:
                self.get_logger().error(
                    f'路点 {waypoint_index} 第 {attempt} 次失败，'
                    f'准备重试...')
            else:
                self.get_logger().error(
                    f'路点 {waypoint_index} 第 {attempt} 次返回状态无效')

            # 重试前取消当前任务
            if attempt < self.max_retries_:
                self.cancelTask()

        self.get_logger().error(
            f'路点 {waypoint_index} 已重试 {self.max_retries_} 次全部失败，跳过')
        return False


def main():
    rclpy.init()
    node = AutoWaypointNode()

    # 1. 初始化位姿
    node.init_robot_pose()

    # 2. 获取目标路点
    target_points = node.get_target_points()
    if not target_points:
        node.get_logger().error('未配置有效路点，退出')
        rclpy.shutdown()
        return

    # 3. 按序导航
    succeeded = 0
    failed = 0
    total = len(target_points)

    # 路点到达后的身体高度映射
    waypoint_height_map = {
        1: 50.0,   # 到达路点2时身体高度设为50
        2: 130.0,  # 到达路点3时身体高度设为130
    }

    for i, (x, y, yaw) in enumerate(target_points):
        node.get_logger().info(
            f'===== 路点 {i}/{total - 1}: ({x:.2f}, {y:.2f}, {yaw:.2f}) =====')
        target_pose = node.get_pose_by_xyyaw(x, y, yaw)
        if node.nav_to_pose_with_retry(target_pose, i):
            succeeded += 1
            # 到达路点后设置身体高度
            if i in waypoint_height_map:
                height = waypoint_height_map[i]
                height_msg = Float32()
                height_msg.data = height
                node.body_height_pub_.publish(height_msg)
                node.get_logger().info(
                    f'已发布身体高度命令: {height:.1f} mm (路点 {i})')

            # 到达路点后的夹爪动作
            if i == 1:
                pick_up()
                node.get_logger().info('路点 2: 执行 pick_up (夹爪抓取)')
            elif i == 5:
                put_down()
                node.get_logger().info('路点 6: 执行 put_down (夹爪释放)')

            # 路点 4 到达后：放宽 RotationShim，下一段允许倒退
            if i == 3:
                node.set_rotation_shim_threshold(3.14)
                node.get_logger().info('路点 4: 已放宽 angular_dist_threshold → 3.14 (允许倒退)')

            # 路点 5 到达后：恢复 RotationShim 正常阈值
            if i == 4:
                node.set_rotation_shim_threshold(0.25)
                node.get_logger().info('路点 5: 已恢复 angular_dist_threshold → 0.25')
        else:
            failed += 1

    # 4. 汇总报告
    node.get_logger().info('==================== 导航完成 ====================')
    node.get_logger().info(f'总计路点: {total}')
    node.get_logger().info(f'成功: {succeeded}')
    node.get_logger().info(f'失败/跳过: {failed}')
    node.get_logger().info('==================================================')

    rclpy.shutdown()


if __name__ == '__main__':
    main()
