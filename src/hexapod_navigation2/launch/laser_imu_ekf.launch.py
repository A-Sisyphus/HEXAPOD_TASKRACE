import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    ekf_config = os.path.join(
        get_package_share_directory('hexapod_navigation2'),
        'config',
        'ekf_laser_imu.yaml',
    )

    rf2o_node = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic': '/scan',
            'odom_topic': '/odom_rf2o_raw',
            'publish_tf': False,
            'base_frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'init_pose_from_topic': '',
            'freq': 20.0,
        }],
    )

    odom_covariance_relay = Node(
        package='robot_move',
        executable='odom_covariance_relay',
        name='odom_covariance_relay',
        output='screen',
        parameters=[{
            'input_topic': '/odom_rf2o_raw',
            'output_topic': '/odom_rf2o',
            'pose_covariance_diagonal': [0.04, 0.04, 1e6, 1e6, 1e6, 0.10],
            'twist_covariance_diagonal': [0.05, 1e6, 1e6, 1e6, 1e6, 0.10],
        }],
    )

    euler_yaw_to_pose = Node(
        package='robot_move',
        executable='euler_yaw_to_pose',
        name='euler_yaw_to_pose',
        output='screen',
        parameters=[{
            'input_topic': '/euler_only',
            'output_topic': '/imu/yaw_pose',
            'frame_id': 'odom',
            'yaw_in_degrees': True,
            'invert_yaw': False,
            'yaw_offset_rad': 0.0,
            'zero_on_start': True,
            'yaw_variance': 0.03,
        }],
    )

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
        remappings=[
            ('odometry/filtered', '/odom'),
        ],
    )

    return LaunchDescription([
        rf2o_node,
        odom_covariance_relay,
        euler_yaw_to_pose,
        ekf_node,
    ])
