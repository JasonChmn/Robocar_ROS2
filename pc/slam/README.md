# SLAM : construire une carte avec le LiDAR

> **À faire par les étudiants.** Le SLAM n'est **pas** fourni : l'image `robocar:jazzy` ne contient ni `slam_toolbox` ni Nav2. Ce guide donne une méthode de départ et les pièges connus. C'est à vous de l'installer, de le lancer, de le régler, et d'en faire un nœud ou un launch à vous si besoin.

`f1tenth_online_async.yaml` est un point de départ : la config F1TENTH, avec `base_frame` déjà corrigé en `base_link`.

## Ce que la voiture fournit déjà

| Entrée du SLAM | Publiée par | Service |
|---|---|---|
| `/scan` (`sensor_msgs/LaserScan`, ~10 Hz, frame `laser`) | `ldlidar` | `lidar` |
| `/odom` et la TF `odom → base_link` | `vesc_to_odom` | `control` |
| La TF `base_link → laser` (position du LiDAR) | `robot_state_publisher` (URDF) | `control` |

Le SLAM publie la TF `map → odom` et le topic `/map`. Il faut donc que **`control` et `lidar` tournent tous les deux**, sinon l'arbre TF est incomplet et `slam_toolbox` ignore les scans.

```bash
# sur la Jetson
docker compose -f docker/compose.yaml --profile control --profile lidar up -d
```

## Installation (sur le PC)

```bash
sudo apt install ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server
```

Les réglages réseau sont ceux de `README.md` §2 : chrony, `ufw`, même `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET`.

## Lancer

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET   # valeurs de .env

# vérifier les entrées avant de lancer le SLAM
ros2 topic hz /scan                          # ~10 Hz
ros2 topic hz /odom
ros2 run tf2_ros tf2_echo odom laser         # doit afficher une transformée, pas une erreur

ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=$PWD/pc/slam/f1tenth_online_async.yaml use_sim_time:=false
```

Dans RViz2 :
1. Fixed Frame : `map`.
2. Add → Map, topic `/map`.
3. Add → LaserScan, topic `/scan`.
4. Add → TF.

Rouler **lentement** (manette, LB). Faire des boucles et repasser par les mêmes endroits aide le SLAM à fermer les boucles (`do_loop_closing`).

## Sauvegarder la carte

```bash
ros2 run nav2_map_server map_saver_cli -f ma_salle     # ma_salle.pgm + ma_salle.yaml (carte d'occupation)
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph "{filename: 'ma_salle'}"
```

La deuxième commande sauvegarde le graphe de poses. Il permet de reprendre la carte, ou de se localiser dessus (`mode: localization`).

## Régler sans la voiture : enregistrer un bag

```bash
ros2 bag record /scan /odom /tf /tf_static -o essai1     # pendant qu'on roule
ros2 bag play essai1 --clock                             # plus tard, voiture éteinte
# relancer le SLAM avec use_sim_time:=true
```

On peut ainsi rejouer le même trajet autant de fois qu'il faut pour régler les paramètres.

## Pièges connus

- **Pas de carte, ou message `Message Filter dropping message`** : il manque une TF, souvent parce que `control` ne tourne pas. Ou bien les horloges de la Jetson et du PC diffèrent : vérifier `chronyc sources` sur la Jetson.
- **Carte en miroir ou tournée** : vérifier d'abord le LiDAR seul dans RViz (Fixed Frame `laser`). Un objet devant doit apparaître en X+, un objet à gauche en Y+ (REP-103).
- **Carte qui « glisse » ou se dédouble** : l'odométrie est mal calibrée. Voir `speed_to_erpm_gain` et `wheelbase` dans `robocar_bringup/config/vesc.yaml`, et `docs/ROBOCAR_TO_DO_ROS2.md` §7. Le moteur n'a pas de capteur : à basse vitesse, l'odométrie est approximative.
- **`max_laser_range: 20.0`** : le LD19 ne porte qu'à environ 12 m. Mettre 12, ou moins, évite d'intégrer des points aberrants.
- **Sur la Jetson plutôt que sur le PC** : c'est possible, mais il faut ajouter `slam_toolbox` à une image (le Dockerfile ou votre propre conteneur) et mesurer la charge avec `tegrastats`. Voir `docs/ROBOCAR_TO_DO_ROS2.md` §4.

## Pour aller plus loin

- `mode: localization` : se localiser sur une carte déjà faite.
- Nav2 : planification et évitement d'obstacles, une fois le SLAM stable.
- Le simulateur `f1tenth_gym_ros` (branche `dev-jazzy`) publie les mêmes topics : on peut y tester sa méthode avant de passer à la voiture.
