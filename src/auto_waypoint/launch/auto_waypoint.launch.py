#!/usr/bin/env python3
"""
自动路点导航 Launch 文件
加载 waypoint_config.yaml 并启动 auto_waypoint_node
"""
import os
import re

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _extract_config_index(params_file_path: str) -> int:
    """从配置文件名提取编号，如 waypoint_config2.yaml → 2"""
    basename = os.path.basename(params_file_path)
    match = re.search(r'waypoint_config(\d+)\.yaml', basename)
    if match:
        return int(match.group(1))
    return 0


def _node_with_config_index(context, *args, **kwargs):
    """OpaqueFunction：提取 config_index 后返回 Node 动作"""
    params_file = LaunchConfiguration('params_file').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time').perform(context)
    config_index = _extract_config_index(params_file)

    return [
        Node(
            package='auto_waypoint',
            executable='auto_waypoint_node',
            name='auto_waypoint_node',
            output='screen',
            parameters=[
                params_file,
                {'use_sim_time': use_sim_time == 'true',
                 'config_index': config_index},
            ],
        ),
    ]


def generate_launch_description():
    # 获取本包 share 目录
    pkg_share = get_package_share_directory('auto_waypoint')

    # 声明参数
    params_file = LaunchConfiguration('params_file', default=os.path.join(
        pkg_share, 'config', 'waypoint_config2.yaml'))
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file',
            default_value=params_file,
            description='Full path to waypoint config YAML'),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value=use_sim_time,
            description='Use simulation (Gazebo) clock if true'),

        OpaqueFunction(function=_node_with_config_index),
    ])
