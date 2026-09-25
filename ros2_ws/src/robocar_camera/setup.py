from setuptools import setup

package_name = 'robocar_camera'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Jason Chemin',
    maintainer_email='jason.chemin@epitech.eu',
    description='Nœud caméra générique : n\'importe quelle source d\'images, publiée sur /camera.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'camera_node = robocar_camera.camera_node:main',
        ],
    },
)
