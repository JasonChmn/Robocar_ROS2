"""Brique camera : nœud caméra générique -> /camera/* (frame camera_link)."""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = get_package_share_directory('robocar_bringup') + '/config/camera.yaml'

    return LaunchDescription([
        Node(
            package='robocar_camera',
            executable='camera_node',
            name='camera_node',
            parameters=[config],
        ),
    ])
