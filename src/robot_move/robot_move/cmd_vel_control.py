# ROS 2 cmd_vel subscriber for the hexapod controller.
import os
import sys
import threading
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


def _add_hexapod_path():
	current_dir = Path(__file__).resolve().parent
	hexapod_dir = current_dir.parent / 'hexapod' / 'hexapod1'
	if str(hexapod_dir) not in sys.path:
		sys.path.insert(0, str(hexapod_dir))


_add_hexapod_path()

import Hexapod as pd


class CmdVelControlNode(Node):
	def __init__(self):
		super().__init__('cmd_vel_control')

		self.declare_parameter('cmd_vel_topic', '/cmd_vel')
		self.declare_parameter('vx_scale', 1000.0)
		self.declare_parameter('vy_scale', 1000.0)
		self.declare_parameter('omega_scale', 1000.0)
		self.declare_parameter('cmd_timeout', 0.5)
		self.declare_parameter('publish_rate_hz', 20.0)
		self.declare_parameter('separate_linear_angular', True)
		self.declare_parameter('turn_priority_ratio', 0.7)
		self.declare_parameter('cmd_deadband', 1.0)

		self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
		self.vx_scale = float(self.get_parameter('vx_scale').value)
		self.vy_scale = float(self.get_parameter('vy_scale').value)
		self.omega_scale = float(self.get_parameter('omega_scale').value)
		self.cmd_timeout = float(self.get_parameter('cmd_timeout').value)
		self.separate_linear_angular = bool(self.get_parameter('separate_linear_angular').value)
		self.turn_priority_ratio = float(self.get_parameter('turn_priority_ratio').value)
		self.cmd_deadband = float(self.get_parameter('cmd_deadband').value)
		publish_rate_hz = float(self.get_parameter('publish_rate_hz').value)
		timer_period = 1.0 / publish_rate_hz if publish_rate_hz > 0.0 else 0.05

		self._last_cmd_time = self.get_clock().now()
		self._last_cmd = (0.0, 0.0, 0.0)
		self._motion_thread_started = False

		pd.hexapod_init()
		pd.move_flag = True
		self._start_motion_thread()

		self.subscription = self.create_subscription(
			Twist,
			self.cmd_vel_topic,
			self.cmd_vel_callback,
			10,
		)
		self.timer = self.create_timer(timer_period, self._watchdog)

		self.get_logger().info(
			f'Subscribed to {self.cmd_vel_topic}, scales: '
			f'vx={self.vx_scale}, vy={self.vy_scale}, omega={self.omega_scale}; '
			'mapping: Vx=-cmd.linear.y, Vy=cmd.linear.x, omega=cmd.angular.z; '
			f'separate_linear_angular={self.separate_linear_angular}, '
			f'turn_priority_ratio={self.turn_priority_ratio}, deadband={self.cmd_deadband}'
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

	def cmd_vel_callback(self, msg: Twist):
		# Robot frame in Hexapod.py: +Vx right, +Vy forward.
		# ROS cmd_vel convention: +linear.x forward, +linear.y left.
		vx = -float(msg.linear.y) * self.vx_scale
		vy = float(msg.linear.x) * self.vy_scale
		omega = float(msg.angular.z) * self.omega_scale

		if self.separate_linear_angular:
			linear_mag = max(abs(vx), abs(vy))
			angular_mag = abs(omega)
			if linear_mag > self.cmd_deadband and angular_mag > self.cmd_deadband:
				if angular_mag >= self.turn_priority_ratio * linear_mag:
					# Rotate in place when turn command dominates.
					vx = 0.0
					vy = 0.0
				else:
					# Keep translation and suppress rotation.
					omega = 0.0

		pd.set_velocity(vx, vy, omega)
		self._last_cmd = (vx, vy, omega)
		self._last_cmd_time = self.get_clock().now()

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
	node = CmdVelControlNode()
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
