#!/bin/bash
set -e

# ROS_DOMAIN_ID obligatoire, entier de 1 à 101 (docs/ROBOCAR_TO_DO_ROS2.md §6)
if ! [[ "$ROS_DOMAIN_ID" =~ ^[0-9]+$ ]] || [ "$ROS_DOMAIN_ID" -lt 1 ] || [ "$ROS_DOMAIN_ID" -gt 101 ]; then
    echo "ERREUR : ROS_DOMAIN_ID='$ROS_DOMAIN_ID' invalide. Mettre dans .env un nombre de 1 à 101 :" >&2
    echo "  le numéro de votre département (ex. 92), jamais 0. Voir .env.example." >&2
    exit 1
fi

source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
exec "$@"
