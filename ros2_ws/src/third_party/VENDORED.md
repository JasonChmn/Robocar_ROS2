# Code tiers copié

Copie simple des fichiers (sans `.git`, `.github`, submodule ni lien avec l'amont). Copié le 2026-09-24.
Pour mettre à jour : recopier la nouvelle version, puis réappliquer les patchs ci-dessous.

| Dossier | Origine | Branche | Commit (date) |
|---|---|---|---|
| `vesc/` | https://github.com/f1tenth/vesc | `jazzy` | `1bc8251296abb3936da5f30821b6311d67e861b7` (2025-02-18) |
| `ackermann_mux/` | https://github.com/f1tenth/ackermann_mux | `foxy-devel` | `b3c0b083ac03aa8c648537d7e4d22608fcd3440c` (2021-11-10) |
| `teleop_tools/` | https://github.com/f1tenth/teleop_tools | `humble-devel` | `163827aa96039a70f5fe7f2bb59c332417b64eee` (2025-02-10) |
| `ldlidar_stl_ros2/` | https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2 | `master` | `bf668a89baf722a787dadc442860dcbf33a82f5a` (2023-05-08) |

Les commits de `vesc`, `ackermann_mux` et `teleop_tools` sont ceux référencés par `f1tenth/f1tenth_system@jazzy-devel` (`cffbbd7`).

## Configs reprises de F1TENTH (sans copie de code)

Source : https://github.com/f1tenth/f1tenth_system, branche `jazzy-devel`, commit `cffbbd7a89d14d59bfd6123d8abdc5ad4d955105` (2026-09-11), dossier `f1tenth_stack/`.

| Fichier F1TENTH | Notre fichier | Ce qui change |
|---|---|---|
| `config/vesc.yaml` | `robocar_bringup/config/vesc.yaml` | Valeurs du §7 (servo, vitesse, empattement), `port: /dev/vesc`, `cmd_timeout: 0.1` (watchdog), `throttle_interpolator` retiré |
| `config/mux.yaml` | `robocar_bringup/config/mux.yaml` | Lock `drive_enable` ajouté (priorité 100, 0,1 s) |
| `config/joy_teleop.yaml` | `robocar_bringup/config/joy_teleop.yaml` | Numéros de boutons SDL2, vitesse max 1 m/s au lieu de 5, `autorepeat_rate` 50 Hz, profil `drive_enable` sur RB au lieu de `autonomous_control` |
| `config/f1tenth_online_async.yaml` | `pc/slam/f1tenth_online_async.yaml` | `base_frame: base_link` au lieu de `laser` |
| `launch/bringup_launch.py` | `robocar_bringup/launch/control.launch.py` | Réécrit : mêmes nœuds, sans remapping du mux, sans `urg_node` ni TF statique (URDF), avec `robot_state_publisher` |

## Modifications du code copié

Chaque modification dans le code est marquée `[robocar]`.

### `vesc/vesc_ackermann` : watchdog dans `ackermann_to_vesc`
- Fichiers : `src/ackermann_to_vesc.cpp`, `include/vesc_ackermann/ackermann_to_vesc.hpp`.
- Nouveau paramètre `cmd_timeout` (en s, 0 = désactivé, valeur d'origine). S'il ne reçoit rien sur `ackermann_cmd` pendant `cmd_timeout`, le nœud publie `commands/motor/speed = 0` à 50 Hz jusqu'à la commande suivante. Le servo n'est pas touché.
- Mesure sur horloge monotone (`RCL_STEADY_TIME`), pour ne pas être affectée par un saut d'heure système (chrony).
- Pourquoi : quand le mux se tait, `vesc_driver` ne renvoie pas la dernière commande, et le moteur garde sa consigne jusqu'au timeout du firmware VESC. Voir `docs/ROBOCAR_TO_DO_ROS2.md` §2, chaîne de sécurité.

### `ldlidar_stl_ros2` : include manquant
- Fichier : `ldlidar_driver/include/logger/log_module.h`, ligne 40.
- `#include <pthread.h>` décommenté. Sans lui, le build échoue avec le GCC d'Ubuntu 24.04 (`pthread_mutex_init was not declared`).

### `teleop_tools` : paquets non compilés
- `COLCON_IGNORE` ajouté dans `key_teleop/`, `mouse_teleop/` et `teleop_tools/` (métapaquet). Seuls `joy_teleop` et `teleop_tools_msgs` sont utilisés.

## Sans modification, mais à savoir
- `joy_teleop` (version F1TENTH) : profil `default`, actif quand aucun bouton n'est appuyé. C'est leur modification du paquet d'origine `ros-teleop/teleop_tools`, et la raison pour laquelle on n'utilise pas `ros-jazzy-joy-teleop` en apt.
- `joy_teleop` : un profil `message_value` ne publie qu'une fois, au moment de l'appui. Pour publier en continu tant que le bouton est maintenu, utiliser `axis_mappings` avec une entrée `value` (c'est ce que fait le lock `drive_enable`).
- `ackermann_mux` publie sur `ackermann_cmd`. Un lock qui n'a encore rien reçu, ou qui a expiré, est considéré comme verrouillé.
