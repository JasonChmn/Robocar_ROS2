# Préparer une voiture (encadrants)

Ce guide sert à préparer une Robocar **avant** de la donner aux étudiants : carte SD de la Jetson, VESC et vérifications. Les étudiants, eux, suivent `README.md`.

Détail et historique de chaque étape : `A_FAIRE_SUR_LA_JETSON.md` (section « Déjà fait ») et `docs/ROBOCAR_TO_DO_ROS2.md`.

## 0. Matériel de référence

| Élément | Référence | Remarque |
|---|---|---|
| Châssis | Traxxas Ford Fiesta ST Rally **BL-2s** (74154-4) | Moteur **BL-2s 3300 kV**, 4 pôles, sans capteur, prévu pour 2S |
| Contrôleur moteur | VESC Flipsky, **Hw 60, Fw 7.00** | USB `0483:5740` → `/dev/vesc` |
| Calculateur | Jetson Nano 4 Go, **JetPack 4.6.1** (L4T R32.7.1, Ubuntu 18.04), microSD 64 Go | Alimentation **jack 5 V 4 A, cavalier J48** (le micro-USB ne suffit pas) |
| LiDAR | LDRobot **LD19 / STL-19P**, 230400 bauds | Adaptateur CP2102 `10c4:ea60` → `/dev/lidar` |
| Manette | Logitech **F710**, mode **X** | `046d:c21f` |
| Caméra | Luxonis OAK-D Lite | Pas encore validée |
| Batterie | **Une** LiPo **4S** par voiture : 2200 mAh ou 3700 mAh selon la voiture. Elle alimente le VESC et, par un convertisseur 5 V, la Jetson | Pleine à 16,8 V, **arrêt sous 14,0 V** |

## 1. PC de l'encadrant

À faire une seule fois.

```bash
# ROS 2 Jazzy en natif (Ubuntu 24.04) : https://docs.ros.org/en/jazzy/Installation.html, avec RViz2
sudo apt install ros-jazzy-desktop ros-jazzy-ackermann-msgs

# Horloge de référence pour la Jetson (elle n'a pas de pile RTC)
sudo apt install chrony
echo -e "allow 10.42.0.0/24\nlocal stratum 10" | sudo tee -a /etc/chrony/chrony.conf
sudo systemctl restart chrony

# Pare-feu : laisser passer le trafic ROS venant de la Jetson
sudo ufw allow from 10.42.0.0/24
```

Réseau : un câble Ethernet entre le PC et la Jetson, avec le **partage de connexion** de NetworkManager (*Paramètres → Réseau → Filaire → IPv4 → Partagé avec d'autres ordinateurs*). La Jetson reçoit une adresse en `10.42.0.x`, d'habitude `10.42.0.239`. Si l'adresse change : `ip neigh`, ou `nmap -sn 10.42.0.0/24`.

## 2. Carte SD : deux chemins

### A. Cloner l'image de référence (recommandé, ~20 min)

L'image contient un système prêt : Docker, le plugin compose, chrony, le swap, udev, le dépôt et l'image `robocar:jazzy` déjà construite.

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,TRAN   # repérer la carte ; NE PAS se tromper de disque
sudo dd if=backups/jetson_sd_<date>.img of=/dev/<carte> bs=4M status=progress conv=fsync
```

- Carte d'**au moins 64 Go**. `if=` est l'image et `of=` la carte : les inverser écrase l'image.
- Lancer `dd` dans un vrai terminal, pour que `sudo` puisse demander le mot de passe.
- **L'image doit dater d'après le 2026-09-25 (fin de journée)**. Les plus anciennes ont encore `vesc-config.service` activé et l'ancienne config de la manette. Pour une image plus ancienne : `sudo systemctl disable --now vesc-config`, puis refaire les étapes 3 et 4 de la section B.

Ensuite, passer directement au §3.

### B. Partir d'un JetPack 4.6.1 vierge (~1 h)

1. Flasher l'image SD **JetPack 4.6.1** de NVIDIA sur la carte, démarrer, puis créer l'utilisateur **`robocar`**.
2. Vérifier que Jazzy tourne dans Docker (Docker 20.10 est fourni avec JetPack) :
   ```bash
   docker run --rm -it --network host -e ROS_DOMAIN_ID=42 ros:jazzy-ros-base \
     ros2 topic pub -r 2 /chatter std_msgs/msg/String "{data: hello}"
   # sur le PC : ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET ros2 topic echo /chatter
   ```
3. Installer le plugin `docker compose`. JetPack ne fournit que `docker-compose` v1, qui ne gère pas les profils :
   ```bash
   mkdir -p ~/.docker/cli-plugins
   curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64 \
     -o ~/.docker/cli-plugins/docker-compose
   chmod +x ~/.docker/cli-plugins/docker-compose
   ```
   Il est installé dans `~` : lancer `docker compose` **sans `sudo`**.
4. Récupérer le dépôt et préparer l'hôte :
   ```bash
   git clone https://github.com/JasonChmn/Robocar_ROS2.git ~/Robocar_ROS2
   cd ~/Robocar_ROS2
   sudo ./host/setup_host.sh 10.42.0.1   # groupes, swap 4 Go, MAXN, chrony (serveur = PC), udev
   exit                                  # se reconnecter pour les groupes
   chronyc sources                       # « ^* » devant le PC = synchronisé
   ```
5. Construire l'image : **~17 min**, 2,2 Go. `nohup` permet au build de survivre à une coupure SSH :
   ```bash
   cp .env.example .env   # puis choisir ROS_DOMAIN_ID (§5)
   nohup docker compose -f docker/compose.yaml build control > ~/build.log 2>&1 &
   tail -f ~/build.log
   ```

## 3. VESC

Si le VESC a déjà été configuré sur une autre voiture, sa config y reste : elle est stockée dans le VESC. Pour un VESC neuf, dans VESC Tool, sur le PC :

1. Charger `host/vesc/vesc_mcconf.xml` et `host/vesc/vesc_appconf.xml`, puis **Write** pour chacun (deux boutons distincts, **M** et **A**).
2. **Relancer la détection FOC**, roues en l'air : R, L et λ changent d'un moteur à l'autre.
3. Couper tout, rebrancher, relire, et vérifier.

Procédure complète, valeurs et explications : `host/vesc/README.md`. Il n'y a **rien à réappliquer au démarrage**. Si l'ancien `vesc-config.service` existe sur la carte, il doit rester désactivé.

## 4. Vérifications, roues en l'air

LiDAR et dongle F710 branchés **avant** la batterie (elle alimente le VESC et la Jetson). F710 : interrupteur au dos sur **X**, **LED MODE éteinte**.

```bash
lsusb | grep -E "0483:5740|10c4:ea60|046d:c21f"   # 3 lignes
ls -l /dev/vesc /dev/lidar                         # → ttyACM*, ttyUSB*
cd ~/Robocar_ROS2
docker compose -f docker/compose.yaml --profile control --profile lidar up -d
rc() { docker compose -f ~/Robocar_ROS2/docker/compose.yaml exec control /entrypoint.sh "$@"; }
rc ros2 topic echo /sensors/core --once   # voltage_input ≈ LiPo, fault_code 0
rc ros2 topic hz /scan                    # ~10 Hz
```

Au démarrage de `control`, quelques erreurs `Out-of-sync with VESC` sont normales. Elles doivent cesser après `Connected to VESC with firmware version 7.0`.

| Vérification | Attendu |
|---|---|
| LB + stick gauche | Les roues avancent (haut) et reculent (bas). Tout s'arrête au relâchement de LB |
| LB + stick droit | Les roues braquent **à gauche** avec le stick à gauche. Le servo ne force pas en butée |
| `rc ros2 topic pub -r 20 /drive ackermann_msgs/msg/AckermannDriveStamped "{drive: {speed: 0.5}}"` | Rien ne tourne sans RB. Avec RB maintenu, les roues avancent ; au relâchement, arrêt immédiat |
| Même chose, avec **A** au lieu de RB | Rien ne tourne |
| RB maintenu, Ctrl+C sur le `pub` | Arrêt en moins de 0,2 s |
| RViz sur le PC, Fixed Frame `base_link`, LaserScan `/scan`, TF | Un objet devant apparaît en X+ (rouge), un objet à gauche en Y+ (vert) |

Test de la chaîne de sécurité sans matériel (10/10 attendu) : `A_FAIRE_SUR_LA_JETSON.md`, « Déjà fait » E.

## 5. Avant de donner la voiture

- **`ROS_DOMAIN_ID`** : un numéro par équipe dans `~/Robocar_ROS2/.env` (le numéro du département, `README.md` §2). Il doit être identique sur la Jetson et sur le PC de l'équipe. `entrypoint.sh` refuse les valeurs vides, 0, ou au-delà de 101.
- **chrony** : la Jetson se synchronise sur l'IP donnée à `setup_host.sh`. Si l'équipe utilise son propre PC, relancer `sudo ./host/setup_host.sh <IP_du_PC>`, ou modifier la ligne `server` de `/etc/chrony/chrony.conf`.
- **Clé SSH** de l'équipe : `ssh-copy-id robocar@<IP>`.
- **Sauvegarder l'image SD** d'une voiture validée, Jetson éteinte proprement :
  ```bash
  sudo dd if=/dev/<carte> of=backups/jetson_sd_$(date +%F).img bs=4M status=progress conv=fsync
  ```
  60 Go, ~20 min. À stocker **hors du dépôt**.

## 6. Pièges connus

| Symptôme | Cause | Solution |
|---|---|---|
| La Jetson s'éteint sans prévenir | Alimentation micro-USB | Jack 5 V 4 A, cavalier J48 |
| Pas de `ssh` ni de `ping` après 2 min, alors que le lien Ethernet est allumé | Carte SD restée dans le PC | Remettre la carte |
| `ros2 topic list` voit les topics, mais `echo` ne reçoit rien | Pare-feu du PC | `sudo ufw allow from 10.42.0.0/24` |
| TF rejetées dans RViz, `certificate not yet valid` | Horloge de la Jetson fausse | `chronyc sources` : `^*` attendu |
| La config du VESC « se perd » au démarrage | Ancien `vesc-config.service` | `sudo systemctl disable --now vesc-config` |
| LB et RB ne font rien | Mauvais numéros de boutons | `joy_teleop.yaml` : LB = 4, RB = 5 (mesurés sur la F710) |
| La vitesse sort sur l'axe 7, en tout ou rien | LED MODE de la F710 allumée | Appuyer sur MODE |
| `control` refuse de démarrer | `/dev/vesc` absent (VESC non branché ou non alimenté) | Brancher, puis `up -d --force-recreate control` |
| Périphérique rebranché, plus de données | `devices:` est figé à la création du conteneur | `up -d --force-recreate <service>` |
| Build de 8 min pour un simple YAML | La config est dans l'image, `colcon` recompile tout | Normal pour l'instant |
