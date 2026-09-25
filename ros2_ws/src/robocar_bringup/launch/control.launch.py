"""Brique control : manette, mux, VESC, odométrie et URDF.

Chaîne : joy -> joy_teleop -> /teleop ┐
                     nœud étudiant -> /drive ┴> ackermann_mux -> ackermann_cmd
         -> ackermann_to_vesc -> vesc_driver -> /sensors/core -> vesc_to_odom -> /odom
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    config = get_package_share_directory('robocar_bringup') + '/config/'
    urdf = get_package_share_directory('robocar_description') + '/urdf/robocar.urdf.xacro'

    # false : permet de tester la chaîne sans manette ni VESC (ros2 topic pub /joy ...)
    with_joy = LaunchConfiguration('with_joy')
    with_vesc = LaunchConfiguration('with_vesc')

    return LaunchDescription([
        DeclareLaunchArgument('with_joy', default_value='true'),
        DeclareLaunchArgument('with_vesc', default_value='true'),

        Node(
            package='joy',
            executable='joy_node',
            name='joy',
            parameters=[config + 'joy_teleop.yaml'],
            condition=IfCondition(with_joy),
        ),
        Node(
            package='joy_teleop',
            executable='joy_teleop',
            name='joy_teleop',
            parameters=[config + 'joy_teleop.yaml'],
        ),
        # Pas de remapping : le mux publie ackermann_cmd, qu'écoute ackermann_to_vesc
        Node(
            package='ackermann_mux',
            executable='ackermann_mux',
            name='ackermann_mux',
            parameters=[config + 'mux.yaml'],
        ),
        Node(
            package='vesc_ackermann',
            executable='ackermann_to_vesc_node',
            name='ackermann_to_vesc_node',
            parameters=[config + 'vesc.yaml'],
        ),
        Node(
            package='vesc_driver',
            executable='vesc_driver_node',
            name='vesc_driver_node',
            parameters=[config + 'vesc.yaml'],
            condition=IfCondition(with_vesc),
        ),
        Node(
            package='vesc_ackermann',
            executable='vesc_to_odom_node',
            name='vesc_to_odom_node',
            parameters=[config + 'vesc.yaml'],
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            parameters=[{
                'robot_description': ParameterValue(Command(['xacro ', urdf]), value_type=str),
            }],
        ),
    ])
