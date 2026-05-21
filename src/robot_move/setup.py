from pathlib import Path

from setuptools import find_packages, setup

package_name = 'robot_move'


def collect_data_files(source_dir: str, install_dir: str):
    source_path = Path(source_dir)
    data = []

    for file_path in source_path.rglob('*'):
        if not file_path.is_file():
            continue
        if '__pycache__' in file_path.parts or file_path.suffix == '.pyc':
            continue

        relative_parent = file_path.parent.relative_to(source_path)
        target_dir = Path(install_dir) / relative_parent
        data.append((str(target_dir), [str(file_path)]))

    return data

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    include_package_data=True,
    package_data={
        'hexapod.hexapod1': ['*.json'],
    },
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools', 'rclpy', 'geometry_msgs','std_msgs'],
    zip_safe=True,
    maintainer='jetson',
    maintainer_email='123456@example.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'cmd_vel_control = robot_move.cmd_vel_control:main',
            'hexapod_control = robot_move.hexapod_control:main',
        ],
    },
)
