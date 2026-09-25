# Image ROS 2 Jazzy de la Robocar (arm64 sur la Jetson, amd64 pour les tests PC).
# Build depuis la racine du dépôt : docker compose -f docker/compose.yaml build control
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]

# Dépendances apt, dans une couche à part pour que le cache survive aux changements de code
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-ackermann-msgs \
      ros-jazzy-joy \
      ros-jazzy-serial-driver \
      # io_context (dépendance de serial_driver) en a besoin sans le déclarer
      ros-jazzy-asio-cmake-module \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-xacro \
      ros-jazzy-depthai-ros-driver \
      ros-jazzy-image-transport-plugins \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ros2_ws
COPY ros2_ws/src src

# rosdep rattrape les dépendances oubliées dans la liste ci-dessus
RUN apt-get update && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths src --ignore-src -y --rosdistro jazzy \
    && rm -rf /var/lib/apt/lists/*

# 1 seul worker : la Nano n'a que 4 Go de RAM
RUN source /opt/ros/jazzy/setup.bash \
    && colcon build --parallel-workers 1 --cmake-args -DCMAKE_BUILD_TYPE=Release \
    && rm -rf build log

COPY docker/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
