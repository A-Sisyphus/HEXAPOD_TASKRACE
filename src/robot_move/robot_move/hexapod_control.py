
"""ROS 2 combined cmd_vel and body-height controller for the hexapod."""
import importlib.util
import math
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


class MotionState:
    """Three-state hysteresis machine to decouple translation from rotation."""
    TRANSLATE = 0   # prioritize translation, suppress rotation
    ROTATE = 1      # prioritize rotation, suppress translation
    HYBRID = 2      # allow both (when both are small)


class HexapodControlNode(Node):
    def __init__(self):
        super().__init__('hexapod_control')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('body_height_topic', '/hexapod/body_height')
        self.declare_parameter('vx_scale', 1000.0)
        self.declare_parameter('vy_scale', 1000.0)
        self.declare_parameter('omega_scale', 1000.0)
        self.declare_parameter('cmd_timeout', 0.5)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('initial_body_height', 50.0)
        self.declare_parameter('min_body_height', 50.0)
        self.declare_parameter('max_body_height', 130.0)
        self.declare_parameter('separate_linear_angular', True)
        self.declare_parameter('enter_rotate_factor', 1.5)
        self.declare_parameter('exit_rotate_factor', 0.6)
        self.declare_parameter('hysteresis_time_sec', 1.0)
        self.declare_parameter('cmd_deadband', 1.0)

        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.body_height_topic = self.get_parameter('body_height_topic').value
        self.vx_scale = float(self.get_parameter('vx_scale').value)
        self.vy_scale = float(self.get_parameter('vy_scale').value)
        self.omega_scale = float(self.get_parameter('omega_scale').value)
        self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
        self.min_body_height = float(self.get_parameter('min_body_height').value)
        self.max_body_height = float(self.get_parameter('max_body_height').value)
        self.separate_linear_angular = bool(self.get_parameter('separate_linear_angular').value)
        self.enter_rotate_factor = float(self.get_parameter('enter_rotate_factor').value)
        self.exit_rotate_factor = float(self.get_parameter('exit_rotate_factor').value)
        self.hysteresis_time_sec = float(self.get_parameter('hysteresis_time_sec').value)
        self.cmd_deadband = float(self.get_parameter('cmd_deadband').value)
        initial_body_height = float(self.get_parameter('initial_body_height').value)
        publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
        timer_period = 1.0 / publish_rate_hz if publish_rate_hz > 0.0 else 0.05

        self._last_cmd_time = self.get_clock().now()
        self._last_cmd = (0.0, 0.0, 0.0)
        self._motion_state = MotionState.TRANSLATE
        self._state_entered_time = self.get_clock().now()
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
            'cmd_vel mapping: Vx=-cmd.linear.y, Vy=cmd.linear.x, omega=cmd.angular.z; '
            f'separate_linear_angular={self.separate_linear_angular}, '
            f'enter_rotate_factor={self.enter_rotate_factor}, '
            f'exit_rotate_factor={self.exit_rotate_factor}, '
            f'hysteresis_time={self.hysteresis_time_sec}s, deadband={self.cmd_deadband}'
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

        if self.separate_linear_angular:
            linear_mag = math.hypot(vx, vy)
            angular_mag = abs(omega)
            now = self.get_clock().now()

            # Determine desired state from velocity commands
            if linear_mag <= self.cmd_deadband and angular_mag > self.cmd_deadband:
                desired = MotionState.ROTATE
            elif angular_mag <= self.cmd_deadband:
                # No significant angular command → translate (or idle)
                desired = MotionState.TRANSLATE
            elif angular_mag > self.enter_rotate_factor * max(linear_mag, 0.01):
                desired = MotionState.ROTATE
            elif self._motion_state == MotionState.ROTATE and angular_mag < self.exit_rotate_factor * max(linear_mag, 0.01):
                desired = MotionState.TRANSLATE
            else:
                desired = MotionState.HYBRID

            # Hysteresis: only switch state after holding desired for hysteresis_time_sec
            if desired != self._motion_state:
                elapsed = (now - self._state_entered_time).nanoseconds * 1e-9
                if elapsed >= self.hysteresis_time_sec:
                    old_state = self._motion_state
                    self._motion_state = desired
                    self._state_entered_time = now
                    state_names = {0: 'TRANSLATE', 1: 'ROTATE', 2: 'HYBRID'}
                    self.get_logger().info(
                        f'Motion state: {state_names[old_state]} → {state_names[desired]}'
                    )
            else:
                self._state_entered_time = now

            # Apply state-based suppression
            if self._motion_state == MotionState.ROTATE:
                vx = 0.0
                vy = 0.0
            elif self._motion_state == MotionState.TRANSLATE:
                omega = 0.0
            # HYBRID: allow both (small simultaneous motions)

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
    pd.set_body_pos(0, 0, 130)

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
