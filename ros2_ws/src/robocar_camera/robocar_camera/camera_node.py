"""Nœud caméra générique, à compléter selon la caméra utilisée (webcam, smartphone...).

Publie sur /camera/image_raw (sensor_msgs/Image) ou /camera/image/compressed
(sensor_msgs/CompressedImage), avec le frame_id camera_link.
"""
import rclpy
from rclpy.node import Node


class CameraNode(Node):

    def __init__(self):
        super().__init__('camera_node')
        self.frame_id = self.declare_parameter('frame_id', 'camera_link').value
        # TODO : ouvrir la caméra, créer le publisher et un timer de capture


def main():
    rclpy.init()
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
