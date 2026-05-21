
"""ROS 2 combined cmd_vel and body-height controller for the hexapod."""
import importlib.util
import sys
import threading
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float32


def body_height_callback(self, msg: Float32):
    height = self._clamp_height(float(msg.data))
    self._apply_body_height(height)
    self.get_logger().info(f'Body height set to {height:.1f}')

def _add_hexapod_path():
    hexapod_spec = importlib.util.find_spec('hexapod.hexapod1')
    if hexapod_spec is not None and hexapod_spec.submodule_search_locations:
        hexapod_dir = Path(next(iter(hexapod_spec.submodule_search_locations)))
        if str(hexapod_dir) not in sys.path:
            sys.path.insert(0, str(hexapod_dir))
        return


    current_dir = Path(__file__).resolve().parent
    hexapod_dir = current_dir.parent / 'hexapod' / 'hexapod1'
    if not hexapod_dir.exists():
        raise RuntimeError(f'Cannot find robot_move hexapod code at {hexapod_dir}')

    if str(hexapod_dir) not in sys.path:
        sys.path.insert(0, str(hexapod_dir))


_add_hexapod_path()

from hexapod.hexapod1 import Hexapod as pd


class HexapodControlNode(Node):
    def __init__(self):
        super().__init__('hexapod_control')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('body_height_topic', '/hexapod/body_height')
        self.declare_parameter('vx_scale', 1.0)
        self.declare_parameter('vy_scale', 1.0)
        self.declare_parameter('omega_scale', 1.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('initial_body_height', 50.0)
        self.declare_parameter('min_body_height', 50.0)
        self.declare_parameter('max_body_height', 130.0)

        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.body_height_topic = self.get_parameter('body_height_topic').value
        self.vx_scale = float(self.get_parameter('vx_scale').value)
        self.vy_scale = float(self.get_parameter('vy_scale').value)
        self.omega_scale = float(self.get_parameter('omega_scale').value)
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.min_body_height = float(self.get_parameter('min_body_height').value)
        self.max_body_height = float(self.get_parameter('max_body_height').value)
        initial_body_height = float(self.get_parameter('initial_body_height').value)
        publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        timer_period = 1.0 / publish_rate_hz if publish_rate_hz > 0.0 else 0.05

        self._last_cmd_time = self.get_clock().now()
        self._last_cmd = (0.0, 0.0, 0.0)
        self._motion_thread_started = False

        pd.hexapod_init()
        pd.set_body_pos(0.0, 0.0, self._clamp_height(initial_body_height))
        pd.move_flag = True
        self._start_motion_thread()

        self.cmd_vel_subscription = self.create_subscription(
            Twist,
            self.cmd_vel_topic,
            self.cmd_vel_callback,
            10,
        )
        self.body_height_subscription = self.create_subscription(
            Float32,
            self.body_height_topic,
            self.body_height_callback,
            10,
        )
        self.timer = self.create_timer(timer_period, self._watchdog)

        self.get_logger().info(
            f'Subscribed to {self.cmd_vel_topic} and {self.body_height_topic}; '
            f'height range: {self.min_body_height}..{self.max_body_height}; '
            'cmd_vel mapping: Vx=-cmd.linear.y, Vy=cmd.linear.x, omega=cmd.angular.z'
        )

    def _start_motion_thread(self):
        if self._motion_thread_started:
            return

        motion_thread = threading.Thread(
            target=pd.hexapod_move,
            name='hexapod_motion_thread',
            daemon=True,
        )
        motion_thread.start()
        self._motion_thread_started = True

    def _clamp_height(self, height):
        return max(self.min_body_height, min(self.max_body_height, height))

    def cmd_vel_callback(self, msg: Twist):
        # Robot frame in Hexapod.py: +Vx right, +Vy forward.
        # ROS cmd_vel convention: +linear.x forward, +linear.y left.
        vx = -float(msg.linear.y) * self.vx_scale
        vy = float(msg.linear.x) * self.vy_scale
        omega = float(msg.angular.z) * self.omega_scale

        pd.set_velocity(vx, vy, omega)
        self._last_cmd = (vx, vy, omega)
        self._last_cmd_time = self.get_clock().now()

    def body_height_callback(self, msg: Float32):
        height = self._clamp_height(float(msg.data))
        pd.set_body_pos(0.0, 0.0, height)
        self.get_logger().info(f'Body height set to {height:.1f}')

    def _watchdog(self):
        timeout_ns = int(self.cmd_timeout * 1e9)
        elapsed_ns = (self.get_clock().now() - self._last_cmd_time).nanoseconds
        if elapsed_ns > timeout_ns:
            if self._last_cmd != (0.0, 0.0, 0.0):
                pd.set_velocity(0.0, 0.0, 0.0)
                self._last_cmd = (0.0, 0.0, 0.0)

    def stop_robot(self):
        pd.set_velocity(0.0, 0.0, 0.0)
        pd.move_flag = False


def main(args=None):
    rclpy.init(args=args)
    node = HexapodControlNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
