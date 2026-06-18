from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'auto_waypoint'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install waypoint config
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
        # Install launch files
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jetson',
    maintainer_email='123456@example.com',
    description='Auto waypoint navigation node for hexapod robot patrol',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'auto_waypoint_node = auto_waypoint.auto_waypoint_node:main',
            'waypoint_selector = auto_waypoint.waypoint_selector:main',
        ],
    },
)
