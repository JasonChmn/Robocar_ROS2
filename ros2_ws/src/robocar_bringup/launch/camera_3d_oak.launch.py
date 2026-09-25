"""Brique camera_3d_oak : OAK-D Lite -> /oak/rgb/*, /oak/stereo/*.

Reprend camera.launch.py de depthai_ros_driver. Ses frames sont accrochées sous
oak-d-base-frame, défini dans robocar_description.
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription


def generate_launch_description():
    config = get_package_share_directory('robocar_bringup') + '/config/camera_3d_oak.yaml'
    depthai = get_package_share_directory('depthai_ros_driver') + '/launch/camera.launch.py'

    return LaunchDescription([
        IncludeLaunchDescription(
            depthai,
            launch_arguments={
                'name': 'oak',
                'parent_frame': 'oak-d-base-frame',
                'camera_model': 'OAK-D-LITE',
                'params_file': config,
                # la rectification RGB coûte du CPU sur la Nano : à activer si besoin
                'rectify_rgb': 'false',
            }.items(),
        ),
    ])
