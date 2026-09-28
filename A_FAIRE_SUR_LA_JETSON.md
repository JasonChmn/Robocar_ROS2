# À faire sur la Jetson

Journal de la mise en route de la première voiture, dans l'ordre. Reporter les résultats (**À noter**) ici et dans `docs/ROBOCAR_TO_DO_ROS2.md`.

Pour préparer une nouvelle voiture, suivre plutôt **`BOOTSTRAP.md`**, qui résume ce fichier. Pour les étudiants : `README.md`.

## Où on en est (2026-09-25)

| Étape | État |
|---|---|
| Sauvegarde de la SD | ✅ `../backups/jetson_sd_2026-09-25.img` (système déjà prêt) |
| Docker + Jazzy, échange Jetson → PC, plugin compose | ✅ |
| Préparation de l'hôte (`setup_host.sh`, chrony sur le PC) | ✅ |
| Build de l'image | ✅ 17 min, 2,2 Go |
| Chaîne de sécurité sans matériel | ✅ 10/10 |
| LiDAR seul | ✅ `/scan` à 10 Hz, visible dans RViz sur le PC |
| Config du VESC dans VESC Tool (EEPROM saine, FOC, limites, timeout) | ✅ `host/vesc/README.md` |
| Contrôle (VESC, F710), roues en l'air : manette, conduite, sécurité | ✅ §1 c à f (sauf débranchement du dongle et `restart`) |
| LiDAR avec `control` : TF et orientation dans RViz | ✅ §1 g |
| Caméra OAK | ⏳ plus tard, §2 |

## 0. Alimentation

- **Prise jack 5 V 4 A, cavalier J48 en place.** Le micro-USB 5 V 2 A ne suffit pas en MAXN (10 W) : sous la charge du build, ou avec des périphériques USB (l'OAK peut tirer jusqu'à ~1 A), la tension chute et la Jetson s'éteint sans prévenir, avec un risque de corrompre la SD. Au pire, en micro-USB : `sudo nvpmodel -m 1` (5 W), rien de branché, et pas de build.
- **Une seule batterie 4S par voiture**, qui alimente le VESC et, par un convertisseur 5 V, la Jetson. Selon la voiture : Ovonic **2200 mAh** 120C (32,56 Wh) ou **3700 mAh** (54,76 Wh). Mêmes seuils pour les deux :
  - pleine à **16,8 V**. 14,8 V est la tension nominale, pas le maximum : à 14,7 V, elle n'est plus qu'à environ 30-40 % ;
  - **arrêter sous 14,0 V** (3,5 V par cellule). Le VESC réduit la puissance à partir de 14,0 V et coupe à 13,2 V (`host/vesc/README.md`) ;
  - la Jetson seule consomme environ 12 W, pertes du convertisseur comprises : environ 4 h d'autonomie avec la 3700, 2 h 30 avec la 2200. Avec le moteur, c'est beaucoup moins.
- **Toujours éteindre proprement** avant de débrancher : `sudo shutdown -h now`, puis attendre que les LED s'éteignent. Une coupure franche se rattrape en général (journal ext4 rejoué au démarrage), mais peut corrompre la SD.
- Juste après la mise sous tension, `ssh` répond `No route to host` pendant environ 1 min, le temps que la Jetson démarre.
- **Pas de `ssh` ni de `ping` après 2 min : vérifier que la carte SD est bien dans la Jetson** (par exemple, restée dans le lecteur du PC après une sauvegarde). Sans SD, le lien Ethernet s'allume quand même, ce qui peut tromper, mais Linux ne démarre pas : aucune demande DHCP (`journalctl --since "-10 min" | grep DHCPACK` sur le PC reste vide).

## 1. Contrôle + LiDAR, ROUES EN L'AIR (fait le 2026-09-25)

### Avant d'allumer

- Voiture sur une cale, **roues en l'air**.
- LiPo chargée. Jetson sur la prise jack (ou sur la batterie, par le convertisseur).
- **VESC (alimenté), LiDAR et dongle F710 branchés *avant* d'allumer la Jetson.** La F710 doit être en mode **X** (interrupteur au dos).
- **`vesc-config.service` est désactivé** (2026-09-25) et ne doit pas être réactivé. L'EEPROM du VESC n'était pas corrompue : c'est ce script de l'ancien projet qui écrasait la config à chaque démarrage. La config est maintenant stockée dans le VESC (`host/vesc/README.md`).

### Mettre à jour la Jetson (sur le PC)

```bash
rsync -a --exclude .env ~/Documents/projects/Robocar_usergroup/robocar/Robocar_ROS2/ robocar@10.42.0.239:~/Robocar_ROS2/
ssh robocar@10.42.0.239 'cd ~/Robocar_ROS2 && docker compose -f docker/compose.yaml build control'
```

- `--exclude .env` : ne pas écraser le `.env` de la Jetson.
- Le build prend quelques secondes si seul `compose.yaml` ou `docker/` change, mais **~8 min** dès qu'un fichier de `ros2_ws/` change (YAML compris) : `colcon` recompile tout.

### a. Périphériques

```bash
lsusb                                                 # VESC 0483:5740, LiDAR 10c4:ea60, F710 046d:c21f (mode X)
ls -l /dev/vesc /dev/lidar /dev/input/
```

**À vérifier** :
- `/dev/vesc → ttyACM*` (major 166) et `/dev/lidar → ttyUSB*` (major 188). Le major est le premier des deux nombres affichés par `ls -l` à la place de la taille ;
- la F710 crée des `event*` dans `/dev/input/`.

> **Résultat** : VESC `0483:5740` (STM32F407) → `/dev/vesc → ttyACM0` ; LiDAR → `/dev/lidar → ttyUSB0` ; F710 `046d:c21f` (XInput Mode), `event0` à `event2` et `js0`.

### b. Lancer `control` + `lidar`

`control` refuse de démarrer si `/dev/vesc` n'existe pas : c'est normal, `devices:` l'exige.

```bash
cd ~/Robocar_ROS2
docker compose -f docker/compose.yaml --profile control --profile lidar up -d
docker compose -f docker/compose.yaml logs -f control          # erreurs de paramètres, port série
# raccourci pour la suite :
rc() { docker compose -f ~/Robocar_ROS2/docker/compose.yaml exec control /entrypoint.sh "$@"; }
```

> **Résultat** : `control` démarre, avec quelques erreurs `Out-of-sync with VESC` au début, puis `Connected to VESC with firmware version 7.0`. Aucune autre erreur de paramètre.

### c. Manette : numéros des boutons

```bash
rc ros2 topic echo /joy
```

Appuyer sur LB, puis sur RB, et bouger les sticks.

**À noter** : les indices réels de LB, de RB, de l'axe « stick gauche vertical » et de l'axe « stick droit horizontal ». S'ils diffèrent de la config, corriger `robocar_bringup/config/joy_teleop.yaml`, puis rebuild et `up -d --force-recreate control`.

> **Résultat (2026-09-25)** : la manette suit la numérotation `xpad` (11 boutons, 8 axes), que `joy` transmet telle quelle, et non celle du mapping GameController de SDL2 qui était supposée (9, 10, 1, 2). Mesuré :
> - LB = **4**, RB = **5**, A = 0 ;
> - stick gauche vertical = axe **1** (haut = +), stick droit horizontal = axe **3** (gauche = +) ;
> - axes 2 et 5 = gâchettes LT et RT, qui valent **1,0 au repos**. L'ancienne config mettait la direction sur l'axe 2 : avec LB, les roues seraient parties en butée.
>
> `joy_teleop.yaml` et `tests/test_safety_chain.py` sont corrigés.
>
> **La LED MODE de la F710 doit être éteinte.** Allumée, elle échange le stick gauche et la croix : la vitesse sort alors sur l'axe 7, en tout ou rien.

Si `/joy` ne publie rien : voir « Manette dans le conteneur » en fin de fichier.

### d. VESC

```bash
rc ros2 topic echo /sensors/core --once
```

**À vérifier** : `voltage_input` ≈ la tension de la LiPo, `fault_code` = 0.

> **Résultat** : 15,7 V, `fault_code` 0, firmware 7.0 reconnu. Quelques erreurs `Out-of-sync` au démarrage, puis plus rien. `temp_fet` et `temp_motor` valent 0,0 (à regarder, sans conséquence pour l'instant).

### e. Conduite manuelle (LB maintenu)

- Stick gauche : les roues tournent dans les deux sens, et s'arrêtent dès que LB est relâché.
- Stick droit : la direction répond.

**À noter** : est-ce qu'un angle positif tourne **à gauche** (REP-103) ? Contrôler avec `rc ros2 topic echo /ackermann_cmd`. Sinon, inverser le signe de `steering_angle_to_servo_gain` dans `config/vesc.yaml`.

Noter aussi : direction centrée à 0 ou non (`steering_angle_to_servo_offset`), butées du servo forcées ou non (`servo_min`/`servo_max`).

> **Résultat** : stick haut → roues vers l'avant, stick bas → vers l'arrière. Stick à gauche → angle +0,34 → servo 0,20 → roues **à gauche** : le signe de `steering_angle_to_servo_gain` (−0,88) est bon. Le servo ne force pas en butée (0,20 / 0,80). Arrêt immédiat au relâchement de LB. Le centrage exact reste à vérifier au sol (§7).

### f. Sécurité : `/drive` publié et RB maintenu

```bash
rc ros2 topic pub -r 20 /drive ackermann_msgs/msg/AckermannDriveStamped "{drive: {speed: 0.5}}"
```

RB maintenu, les roues tournent. Elles doivent **s'arrêter en moins de 0,2 s** dans chacun de ces cas :
- [x] RB relâché : moteur à 0 en **6 ms** ;
- [x] un autre bouton que RB (A), sans RB : `/drive` bloqué, moteur à 0 ;
- [ ] dongle de la F710 débranché : **pas testé** ;
- [x] publication `/drive` coupée, RB maintenu : moteur à 0 en **57 ms** ;
- [ ] `docker compose ... restart control` pendant que ça roule : **pas testé**. Tous les nœuds meurent, et c'est le timeout du VESC (500 ms, `host/vesc/README.md`) qui doit arrêter le moteur.

Vérifier aussi que **la manette garde la priorité** : RB + LB, le stick commande à la place de `/drive`.

> **Résultat** : `/drive` à +0,5 m/s, RB + LB et stick à fond vers le bas : −1 m/s (−4614 ERPM), les roues reculent. La manette a bien la priorité.
>
> Les essais ont été faits avec `/drive` publié à 20 Hz par un petit script Python dans le conteneur (la même chose que `ros2 topic pub`), en enregistrant `/joy`, `ackermann_cmd`, `commands/motor/speed` et `/sensors/core`.

**Rebranchement du dongle** : `/joy` revient-il **sans** redémarrer le conteneur ? Probablement pas avec `devices: /dev/input` (voir fin de fichier). **À noter** : le résultat.

**Rebranchement du VESC ou du LiDAR** : `restart` ne suffit pas, le port peut revenir sous un autre numéro. Utiliser `docker compose -f docker/compose.yaml up -d --force-recreate control` (ou `lidar`).

### g. LiDAR avec `control` : orientation dans RViz (PC)

Avec `control`, `robot_state_publisher` publie la TF `base_link → laser` : on peut prendre `base_link` comme Fixed Frame.

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
rviz2        # Fixed Frame base_link ; Add → LaserScan /scan (Size 0,03) ; Add → TF
```

**À vérifier** :
- un objet **devant** la voiture apparaît en X+ (axe rouge), un objet **à gauche** en Y+ (axe vert). Sinon, `laser_scan_dir` dans `config/lidar.yaml`, ou le lacet (`yaw`) du LiDAR dans l'URDF ;
- le châssis n'apparaît pas dans le scan. S'il apparaît, régler `enable_angle_crop_func` ;
- `/odom` bouge dans le bon sens quand les roues tournent vers l'avant (Add → Odometry `/odom`).

> **Résultat (2026-09-25)** : `/scan` à 10 Hz avec `control`, et TF `base_link → laser` publiée (x = 0,25 m, z = 0,15 m : positions provisoires de l'URDF, à mesurer). Dans RViz, avec la Fixed Frame `base_link` : l'avant est en X+ et la gauche en Y+, donc `laser_scan_dir: true` est bon. Le châssis n'apparaît pas dans le scan, `enable_angle_crop_func` n'est pas nécessaire. `/odom` n'a pas été regardé.

### Si tout passe

Contrôle et LiDAR sont validés pour le bootstrap. Restent pour plus tard :
- calibration au sol (vitesse réelle, ligne droite, `/odom` sur 2 m ; TODO §7) ;
- caméra OAK (§2).

## 2. Plus tard : caméra OAK-D Lite

```bash
docker compose -f docker/compose.yaml --profile camera_3d_oak up -d
docker compose -f docker/compose.yaml logs camera_3d_oak
docker compose -f docker/compose.yaml exec camera_3d_oak /entrypoint.sh ros2 topic echo /oak/rgb/camera_info --once
tegrastats                              # sur l'hôte : CPU, RAM, température
```

**À noter** :
- la taille réelle de l'image RGB (attendu 640×360) ;
- les erreurs de paramètres dans les logs ;
- la charge et la RAM dans `tegrastats` ;
- le débit du flux `compressed` vu depuis le PC : `ros2 topic bw /oak/rgb/image_raw/compressed`.

**À vérifier** :
- noms des paramètres (`i_isp_num`, `i_isp_den`, `i_resolution`) : repris de la doc depthai 2.x, jamais validés sur un appareil. Un nom faux est ignoré sans erreur : d'où le contrôle de la taille réelle de l'image ;
- présence d'une IMU (BMI270) sur notre révision : si oui, activer `i_enable_imu` dans `config/camera_3d_oak.yaml`.

## Manette dans le conteneur (si `/joy` ne publie rien, ou pour le rebranchement)

> **2026-09-25** : `/joy` publie sans ce correctif, avec la manette branchée avant le démarrage. Le rebranchement à chaud n'est pas testé : le correctif ci-dessous reste une piste.

Le `joy` de Jazzy passe par SDL2, qui reconnaît les manettes grâce à la base udev. Cette base est absente du conteneur : la F710 peut ne pas être détectée du tout, même branchée.

Correctif proposé, pas encore appliqué : dans `docker/compose.yaml`, service `control`, remplacer `- /dev/input` sous `devices:` par :

```yaml
    volumes:
      - /dev/input:/dev/input          # un dongle rebranché réapparaît (nouvel event*)
    device_cgroup_rules:
      - 'c 13:* rmw'                   # accès aux périphériques input uniquement
    environment:
      - SDL_JOYSTICK_DISABLE_UDEV=1    # SDL scanne /dev/input lui-même, sans base udev
```

Puis `docker compose -f docker/compose.yaml up -d --force-recreate control`.

**À vérifier** :
- `/joy` publie, manette branchée avant le démarrage ;
- `/joy` revient après débranchement puis rebranchement du dongle, **sans** redémarrer le conteneur ;
- si `SDL_JOYSTICK_DISABLE_UDEV` n'a pas d'effet (version de SDL2 de Noble) : essayer à la place `- /run/udev:/run/udev:ro` dans `volumes:`. La base udev de l'hôte (18.04) sera alors lue par la libudev du conteneur (24.04).

On ne monte pas `/dev` en entier : ce montage recouvre `/dev/pts` du conteneur et peut casser `docker exec -it`. Pour les ports série, `devices:` suffit, puisque `control` et `lidar` ne sont lancés que si leur périphérique est branché.

---

## Déjà fait (2026-09-25) : résultats, et procédure pour refaire une SD

Pour préparer une nouvelle SD à partir d'un JetPack 4.6.1 vierge, refaire ces étapes dans l'ordre. Ou restaurer l'image de sauvegarde (étape A).

### A. Sauvegarde de la SD (sur le PC)

Jetson éteinte proprement, SD dans le lecteur du PC :

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,TRAN   # repérer la carte (~60 Go, 14 partitions L4T, APP en p1) ; NE PAS se tromper de disque
udisksctl unmount -b /dev/mmcblk0p1         # démonter si le bureau l'a montée (pas de sudo)
sudo dd if=/dev/mmcblk0 of=~/Documents/projects/Robocar_usergroup/robocar/backups/jetson_sd_$(date +%F).img bs=4M status=progress conv=fsync
```

- Nom du disque : `mmcblk0` dans un lecteur interne, `sdX` dans un adaptateur USB.
- `if=` est la carte et `of=` le fichier. Les inverser écrase la carte.
- Lancer `dd` dans un vrai terminal : avec le `!` de Claude Code, `sudo` ne peut pas demander le mot de passe.
- Stocker l'image **hors de `Robocar_ROS2/`** : elle fait 60 Go.
- Restauration : même commande avec `if` et `of` inversés, sur une carte d'au moins 64 Go.

> **Fait** après les étapes B à E, donc avec un système déjà prêt : `backups/jetson_sd_2026-09-25.img`, 64 021 856 256 octets en 19 min (55 Mo/s). Taille identique à la carte ; partition `APP` en ext4 propre, avec le même UUID que la carte. L'image peut aussi servir à cloner la carte pour d'autres voitures.

### B. Copier le dépôt, tester Docker et Jazzy

```bash
# PC
rsync -a --exclude .env ~/Documents/projects/Robocar_usergroup/robocar/Robocar_ROS2/ robocar@10.42.0.239:~/Robocar_ROS2/
# Jetson
ping -c 3 8.8.8.8                       # Internet via le partage de connexion du PC (docker pull, apt, rosdep)
docker run --rm -it --network host -e ROS_DOMAIN_ID=42 ros:jazzy-ros-base \
  ros2 topic pub -r 2 /chatter std_msgs/msg/String "{data: hello_jetson}"
# PC (Jazzy natif)
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 topic echo /chatter std_msgs/msg/String
```

Si `ssh` ne répond pas, l'IP a changé : `ip neigh` ou `nmap -sn 10.42.0.0/24`.

> **Résultat** :
> - L4T R32.7.1, Docker 20.10.7 ;
> - Jazzy OK **sans** `seccomp=unconfined` (pas d'erreur `clone3`), donc pas besoin de mettre Docker à jour ;
> - le PC reçoit les messages ;
> - Humble non testé, inutile ;
> - `ros-base` ne contient pas `demo_nodes_cpp` : d'où `ros2 topic pub` pour le test.

### C. Plugin `docker compose`

JetPack 4.6 n'a pas le plugin compose v2, et le `docker-compose` v1 d'apt (1.17) ne gère pas les `profiles` (1.28 minimum). On installe le binaire pour l'utilisateur. Seul le client est touché, `nvidia-container-runtime` n'est pas concerné :

```bash
mkdir -p ~/.docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
  -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version
```

Plugin installé dans `~` : `sudo docker compose` ne le voit pas. Lancer `docker compose` sans `sudo` (groupe `docker`).

> **Résultat** : v5.5.1, fonctionne avec le démon 20.10.

### D. Préparer l'hôte

```bash
# PC : horloge de référence pour la Jetson
sudo apt install chrony
echo -e "allow 10.42.0.0/24\nlocal stratum 10" | sudo tee -a /etc/chrony/chrony.conf
sudo systemctl restart chrony
# Jetson
cd ~/Robocar_ROS2
sudo ./host/setup_host.sh 10.42.0.1     # groupes, swap 4 Go, nvpmodel, chrony, udev
exit                                    # se reconnecter pour les groupes
chronyc sources                         # ^* sur le PC = synchronisé
```

> **Résultat** :
> - chrony `^*` sur le PC ;
> - `/swapfile` de 4 Go en plus du zram (5,9 Go au total) ;
> - MAXN ;
> - `99-robocar.rules` installé ;
> - groupes déjà en place ;
> - 36 Go libres.

### E. Build de l'image et chaîne de sécurité

```bash
cd ~/Robocar_ROS2
nohup bash -c "time docker compose -f docker/compose.yaml build control" > ~/build_control.log 2>&1 &
tail -f ~/build_control.log             # nohup : le build survit à une coupure SSH

docker run -d --rm --name rc_test --network host --ipc host --env-file .env \
  -v $PWD/tests:/tests robocar:jazzy \
  ros2 launch robocar_bringup control.launch.py with_joy:=false with_vesc:=false
sleep 5
docker exec rc_test /entrypoint.sh python3 /tests/test_safety_chain.py --kill-mux
docker stop rc_test
```

> **Résultat du build** : OK du premier coup en arm64.
> - **17 min** (environ 10 min d'`apt`, 6 min de `colcon`) ;
> - 11 paquets ;
> - image de **2,2 Go** ;
> - RAM suffisante, swap non utilisé.
>
> Avertissements sans gravité : `ament_auto_package` (headers) pour `vesc_*`, et `serial_port_baudrate` non initialisé dans `ldlidar_stl_ros2`, sans effet puisque `lidar.yaml` fixe `port_baudrate: 230400`.
>
> **Résultat de la chaîne de sécurité** : **10/10**. Délais d'arrêt :
> - RB relâché : 4 ms ;
> - manette morte : 189 ms ;
> - `/drive` coupé : 85 ms ;
> - mux tué : 139 ms.

### F. LiDAR seul

```bash
docker compose -f docker/compose.yaml --profile lidar up -d
docker compose -f docker/compose.yaml exec lidar /entrypoint.sh ros2 topic hz /scan
```

Sur le PC, la première fois : `sudo ufw allow from 10.42.0.0/24`. Sinon, `ros2 topic list` voit `/scan`, mais `hz` ne reçoit rien. Sans `control`, prendre `laser` comme Fixed Frame dans RViz : la TF `base_link → laser` vient de `control`.

> **Résultat** :
> - CP2102 `10c4:ea60` (pilote `cp210x` présent dans le kernel 4.9), `/dev/lidar → ttyUSB0` ;
> - `/scan` à 9,99 Hz ; 503 points par tour, dont ~400 valides ; distances de 0,09 à 9 m ;
> - sur le PC : 9,8 Hz, 41 Ko/s ;
> - visible dans RViz ;
> - répond à 230400 bauds avec `LDLiDAR_LD19` : c'est un STL-19P / LD19 (étiquette à confirmer).

Réseau : faire les essais en Ethernet ou avec le partage de connexion (10.42.0.x). En Wi-Fi, la découverte multicast peut échouer : voir TODO §6 (Zenoh). Zenoh ne dispense pas du pare-feu : il faut ouvrir le port TCP 7447 du routeur sur le PC.

### Pourquoi ces réglages (à reprendre dans la doc étudiants)

Ce qui est fait une fois pour toutes sur la Jetson, et ce que chaque équipe devra refaire sur **son** PC.

| Réglage | Où | Pourquoi | Sans lui |
|---|---|---|---|
| **chrony** (serveur) | PC | La Nano n'a pas de pile pour son horloge : sans réseau, elle démarre à une date fausse. Le PC sert d'heure de référence, même sans Internet (`local stratum 10`), et `allow 10.42.0.0/24` autorise la Jetson à s'y synchroniser | Voir ligne suivante |
| **chrony** (client, `server <IP_PC>`) | Jetson | ROS horodate chaque message (`/scan`, `/odom`, TF). Les horodatages de la Jetson doivent être cohérents avec l'horloge du PC qui les reçoit. `makestep 1 3` autorise un grand saut d'heure au démarrage | RViz, TF et SLAM rejettent les données (`extrapolation into the future`, `TF_OLD_DATA`, écran vide). `apt`, `docker pull` et `curl` échouent (`certificate not yet valid`) |
| Groupes `docker`, `dialout`, `input` | Jetson | Lancer `docker` sans `sudo` (le plugin compose est installé dans `~`, `sudo` ne le voit pas). Accéder aux ports série (VESC, LiDAR) et à la manette | `permission denied` sur `/var/run/docker.sock`, `/dev/ttyACM0` ou `/dev/input/event*` |
| Swap de 4 Go (`/swapfile`) | Jetson | 4 Go de RAM partagés entre le CPU et le GPU. La compilation C++ de l'image et le SLAM en consomment beaucoup. Le zram d'origine (4 × 495 Mo) ne suffit pas | Build tué (`Killed`, `c++: fatal error`) |
| `nvpmodel -m 0` (MAXN, 10 W) | Jetson | Les 4 cœurs à fréquence maximale. Nécessite l'alimentation jack 5 V 4 A (cavalier J48) : en micro-USB 2 A, la Jetson s'éteint sous charge | Mode 5 W : 2 cœurs, build et nœuds deux fois plus lents |
| Règles udev (`99-robocar.rules`) | Jetson | Des noms fixes (`/dev/vesc`, `/dev/lidar`) quel que soit l'ordre de branchement, et l'accès à l'OAK sans root | `ttyACM0` et `ttyACM1` s'échangent, les configs pointent vers le mauvais périphérique, l'OAK n'est pas détectée |
| Plugin `docker compose` (`~/.docker/cli-plugins/`) | Jetson | JetPack 4.6 n'a que `docker-compose` v1 (1.17), qui ne gère pas les `profiles` (1.28 minimum) | `'compose' is not a docker command` |
| Alimentation jack 5 V 4 A (§0) | Jetson | MAXN, build et périphériques USB | Extinctions au hasard, SD corrompue |
| `ufw allow from 10.42.0.0/24` | PC | Le pare-feu d'Ubuntu bloque le trafic DDS entrant venant de la Jetson | `ros2 topic list` voit les topics, mais `echo` et `hz` ne reçoivent rien |
| `ROS_DOMAIN_ID` dans `.env` | Jetson, PC | Isoler chaque équipe sur le réseau (TODO §6). `entrypoint.sh` refuse tout ce qui n'est pas un entier de 1 à 101 | Une équipe voit, voire commande, la voiture d'une autre |

À faire par chaque équipe sur son PC : chrony (serveur), `ufw`, Jazzy natif, `ROS_DOMAIN_ID` (`cp .env.example .env`, puis choisir son numéro). Si la Jetson est synchronisée sur le PC d'une autre équipe, relancer `setup_host.sh <IP_du_nouveau_PC>`, ou modifier la ligne `server` de `/etc/chrony/chrony.conf`.
