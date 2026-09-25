"""Brique lidar : LDROBOT STL-19P -> /scan (frame laser)."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = get_package_share_directory('robocar_bringup') + '/config/lidar.yaml'

    return LaunchDescription([
        Node(
            package='ldlidar_stl_ros2',
            executable='ldlidar_stl_ros2_node',
            name='ldlidar',
            parameters=[config],
        ),
    ])
