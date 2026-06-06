import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def _include_launch(package_name: str, launch_file: str):
    package_share = get_package_share_directory(package_name)
    launch_path = os.path.join(package_share, 'launch', launch_file)
    return IncludeLaunchDescription(PythonLaunchDescriptionSource(launch_path))


def generate_launch_description():
    hexapod_control_node = Node(
        package='robot_move',
        executable='hexapod_control',
        name='hexapod_control',
        output='screen',
        parameters=[{
            'separate_linear_angular': True,
            'enter_rotate_factor': 1.5,
            'exit_rotate_factor': 0.6,
            'hysteresis_time_sec': 1.0,
            'cmd_deadband': 1.0,
        }],
    )

    lsn10_launch = _include_launch('lslidar_driver', 'lsn10_launch.py')
    imu_launch = _include_launch('yesense_std_ros2', 'yesense_node.launch.py')
    laser_imu_ekf_launch = _include_launch(
        'hexapod_navigation2',
        'laser_imu_ekf.launch.py',
    )
    navigation2_launch = _include_launch('hexapod_navigation2', 'navigation2.launch.py')

    return LaunchDescription([
        hexapod_control_node,
        TimerAction(
            period=2.0,
            actions=[lsn10_launch, imu_launch],
        ),
        TimerAction(
            period=4.0,
            actions=[laser_imu_ekf_launch],
        ),
        TimerAction(
            period=8.0,
            actions=[navigation2_launch],
        ),
    ])
