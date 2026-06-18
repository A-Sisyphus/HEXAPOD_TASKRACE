#!/usr/bin/env python3
"""
一体式任务 Launch 文件
序号:
  1. 启动 robot_nav_rviz_ekf.launch.py（导航栈）
  2. 等待 Nav2 就绪
  3. 弹出路径选择器 UI（GUI 或终端）
  4. 用户确认后启动 auto_waypoint_node
"""

import os
import subprocess
import sys
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


# ======================== 工具函数 ========================

def _include_launch(pkg: str, launch_file: str):
    """返回 IncludeLaunchDescription 动作"""
    pkg_share = get_package_share_directory(pkg)
    path = os.path.join(pkg_share, 'launch', launch_file)
    return IncludeLaunchDescription(
        PythonLaunchDescriptionSource(path))


def _wait_nav2_ready(timeout: float = 60.0) -> bool:
    """
    轮询 Nav2 关键 service，等待导航栈就绪。
    返回 True 表示就绪，False 表示超时。
    """
    required_services = [
        '/controller_server/set_parameters',
        '/planner_server/set_parameters',
    ]
    print('[Mission Master] 等待 Nav2 就绪...')
    start = time.time()

    while time.time() - start < timeout:
        try:
            result = subprocess.run(
                ['ros2', 'service', 'list'],
                capture_output=True, text=True, timeout=5.0)
            available = result.stdout

            missing = [s for s in required_services if s not in available]
            if not missing:
                elapsed = time.time() - start
                print(
                    f'[Mission Master] Nav2 已就绪 ✓ '
                    f'(等待 {elapsed:.1f}s)')
                return True

            print(
                f'[Mission Master] 等待中... '
                f'缺少: {missing} '
                f'({time.time() - start:.0f}s / {timeout:.0f}s)')
        except Exception as e:
            print(f'[Mission Master] 检查异常: {e}')

        time.sleep(2.0)

    print('[Mission Master] 警告: Nav2 就绪检查超时，仍将继续')
    return False


# ======================== OpaqueFunction ========================

def _select_and_launch(context, *args, **kwargs):
    """
    OpaqueFunction 回调：
    1. 等待 Nav2 就绪
    2. 弹出路径选择 UI
    3. 返回 auto_waypoint_node 动作
    """
    # 等待导航栈就绪
    _wait_nav2_ready(timeout=60.0)

    # 导入路径选择器
    try:
        from auto_waypoint.waypoint_selector import show_selector
    except ImportError:
        print('[Mission Master] 错误: 无法导入 waypoint_selector，'
              '请确认已 source install/setup.bash')
        return []

    # 显示 UI 并获取选择
    try:
        selected_config = show_selector()
    except SystemExit:
        print('[Mission Master] 用户取消，不启动导航')
        return []

    print(f'[Mission Master] 启动 auto_waypoint_node')
    print(f'  配置文件: {selected_config}')

    return [
        Node(
            package='auto_waypoint',
            executable='auto_waypoint_node',
            name='auto_waypoint_node',
            output='screen',
            parameters=[selected_config, {'use_sim_time': False}],
        ),
    ]


# ======================== Launch Description ========================

def generate_launch_description():
    # ---- 可配置的等待时间 ----
    nav_ready_delay = LaunchConfiguration(
        'nav_ready_delay', default='10.0')

    # ---- 导航栈 ----
    nav_stack = _include_launch(
        'hexapod_navigation2',
        'robot_nav_rviz_ekf.launch.py',
    )

    # ---- 延迟后弹出 UI + 启动 auto_waypoint ----
    # TimerAction 给导航栈一个基础启动窗口，
    # OpaqueFunction 内部会再精确轮询 Nav2 就绪。
    waypoint_phase = TimerAction(
        period=nav_ready_delay,
        actions=[
            OpaqueFunction(function=_select_and_launch),
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'nav_ready_delay',
            default_value='10.0',
            description='导航栈初始等待时间 (s)，'
                        '之后开始轮询 Nav2 就绪状态'),

        nav_stack,
        waypoint_phase,
    ])
