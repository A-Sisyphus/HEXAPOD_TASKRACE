"""Convert yesense Euler yaw to a yaw-only PoseWithCovarianceStamped."""

import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from yesense_interface.msg import EulerOnly


def _normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


class EulerYawToPoseNode(Node):
    def __init__(self):
        super().__init__('euler_yaw_to_pose')

        self.declare_parameter('input_topic', '/euler_only')
        self.declare_parameter('output_topic', '/imu/yaw_pose')
        self.declare_parameter('frame_id', 'odom')
        self.declare_parameter('yaw_in_degrees', True)
        self.declare_parameter('invert_yaw', False)
        self.declare_parameter('yaw_offset_rad', 0.0)
        self.declare_parameter('zero_on_start', True)
        self.declare_parameter('yaw_variance', 0.03)

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.frame_id = self.get_parameter('frame_id').value
        self.yaw_in_degrees = bool(self.get_parameter('yaw_in_degrees').value)
        self.invert_yaw = bool(self.get_parameter('invert_yaw').value)
        self.yaw_offset_rad = float(self.get_parameter('yaw_offset_rad').value)
        self.zero_on_start = bool(self.get_parameter('zero_on_start').value)
        self.yaw_variance = float(self.get_parameter('yaw_variance').value)
        self._initial_yaw = None

        self.publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            self.output_topic,
            10,
        )
        self.subscription = self.create_subscription(
            EulerOnly,
            self.input_topic,
            self._callback,
            10,
        )

        self.get_logger().info(
            f'Converting {self.input_topic} yaw to {self.output_topic}; '
            f'frame_id={self.frame_id}, zero_on_start={self.zero_on_start}, '
            f'yaw_variance={self.yaw_variance}'
        )

    def _callback(self, msg):
        yaw = float(msg.euler.yaw)
        if self.yaw_in_degrees:
            yaw = math.radians(yaw)
        if self.invert_yaw:
            yaw = -yaw

        yaw = _normalize_angle(yaw + self.yaw_offset_rad)
        if self.zero_on_start:
            if self._initial_yaw is None:
                self._initial_yaw = yaw
                self.get_logger().info(
                    f'Initial IMU yaw zeroed at {math.degrees(yaw):.2f} deg'
                )
            yaw = _normalize_angle(yaw - self._initial_yaw)

        out = PoseWithCovarianceStamped()
        out.header.stamp = self.get_clock().now().to_msg()
        out.header.frame_id = self.frame_id
        out.pose.pose.orientation.z = math.sin(yaw * 0.5)
        out.pose.pose.orientation.w = math.cos(yaw * 0.5)

        covariance = [0.0] * 36
        covariance[0] = 1e6
        covariance[7] = 1e6
        covariance[14] = 1e6
        covariance[21] = 1e6
        covariance[28] = 1e6
        covariance[35] = self.yaw_variance
        out.pose.covariance = covariance

        self.publisher.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = EulerYawToPoseNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
