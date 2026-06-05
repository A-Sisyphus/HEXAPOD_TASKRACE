"""Relay odometry while filling covariance for robot_localization."""

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


def _diag_to_covariance(diagonal):
    covariance = [0.0] * 36
    for index, value in enumerate(diagonal[:6]):
        covariance[index * 6 + index] = float(value)
    return covariance


class OdomCovarianceRelayNode(Node):
    def __init__(self):
        super().__init__('odom_covariance_relay')

        self.declare_parameter('input_topic', '/odom_rf2o_raw')
        self.declare_parameter('output_topic', '/odom_rf2o')
        self.declare_parameter(
            'pose_covariance_diagonal',
            [0.04, 0.04, 1e6, 1e6, 1e6, 0.10],
        )
        self.declare_parameter(
            'twist_covariance_diagonal',
            [0.05, 1e6, 1e6, 1e6, 1e6, 0.10],
        )

        self.input_topic = self.get_parameter('input_topic').value
        self.output_topic = self.get_parameter('output_topic').value
        self.pose_covariance = _diag_to_covariance(
            self.get_parameter('pose_covariance_diagonal').value
        )
        self.twist_covariance = _diag_to_covariance(
            self.get_parameter('twist_covariance_diagonal').value
        )

        self.publisher = self.create_publisher(Odometry, self.output_topic, 10)
        self.subscription = self.create_subscription(
            Odometry,
            self.input_topic,
            self._callback,
            10,
        )

        self.get_logger().info(
            f'Relaying {self.input_topic} to {self.output_topic} with covariance'
        )

    def _callback(self, msg):
        out = Odometry()
        out.header = msg.header
        out.child_frame_id = msg.child_frame_id
        out.pose.pose = msg.pose.pose
        out.pose.covariance = self.pose_covariance
        out.twist.twist = msg.twist.twist
        out.twist.covariance = self.twist_covariance
        self.publisher.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = OdomCovarianceRelayNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
