# Robocar ROS 2

Une voiture autonome 1/10 (Traxxas) pilotée par **ROS 2 Jazzy**. La voiture fournit les briques de base :
- la conduite, par le VESC et la manette ;
- le LiDAR ;
- les caméras ;
- l'odométrie ;
- une chaîne de sécurité.

**Vous, vous écrivez le nœud qui conduit** : il publie `/drive`. Les topics et les frames suivent les conventions **F1TENTH**, donc leurs tutoriels, leur simulateur et leurs configs SLAM marchent tels quels.

- Architecture, topics, TF : `ARCHITECTURE.md`
- SLAM (à faire par vous) : `pc/slam/README.md`
- Séance LiDAR et SLAM (slides, en anglais) : `docs/Bootstrap LiDAR and SLAM.pptx`

## 1. La voiture

| Élément | Ce qu'il faut savoir |
|---|---|
| Jetson Nano | Le calculateur. ROS 2 tourne dans des conteneurs Docker : **n'installez rien sur la Jetson elle-même** |
| VESC | Le contrôleur moteur et direction. A configurer avec VESC Tools (voir https://tek5-robocar.github.io/robocar_documentation/vesc-calibration/ + les changements dans le bootstrap lidar) |
| Manette F710 | Interrupteur au dos sur **X**, **LED MODE éteinte** |
| Batterie LiPo 4S | Une par voiture (2200 ou 3700 mAh) : elle alimente le VESC et la Jetson. Pleine à 16,8 V. **Arrêter sous 14,0 V** (3,5 V par cellule) : en dessous, la batterie s'abîme |

**Allumer** : branchez le LiDAR et le dongle de la manette, **puis** la batterie (elle alimente le VESC et la Jetson). Comptez environ 1 min avant que `ssh` réponde.

**Éteindre** : `sudo shutdown -h now`, puis attendez que les LED s'éteignent avant de débrancher. Une coupure franche peut corrompre la carte SD.

## 2. Préparer son PC (une seule fois)

Sous Ubuntu 24.04.

**Réseau : à définir.** Pistes à l'étude, rien n'est encore fixé :
- première mise en route de la Jetson avec un écran HDMI, un clavier et une souris, pour la connecter au Wi-Fi depuis l'interface graphique. Alimentation par le jack : **5 V, jamais plus**, au moins 4 A ;
- ensuite, la Jetson et le PC sur le même réseau Wi-Fi, par exemple un point d'accès créé par le PC ;
- Internet sur le PC par le partage de connexion USB d'un téléphone.

Plus tard, si la Jetson manque de RAM, on peut désactiver son interface graphique : `sudo systemctl set-default multi-user.target` (pour la remettre : `graphical.target`).

Une fois la Jetson et le PC sur le même réseau, relevez ces valeurs :

| Valeur | Comment la trouver | Exemple |
|---|---|---|
| IP du PC et sous-réseau | `ip -4 addr` sur le PC, sur l'interface du point d'accès (ou du câble) | `10.42.0.1/24` → sous-réseau `10.42.0.0/24` |
| IP de la Jetson | Sur la Jetson : `ip -4 addr`. Depuis le PC : `ip neigh`, ou `nmap -sn <sous-réseau>` | `10.42.0.239` |

Connexion : `ssh robocar@<IP_Jetson>`.

```bash
# ROS 2 Jazzy : https://docs.ros.org/en/jazzy/Installation.html
sudo apt install ros-jazzy-desktop ros-jazzy-ackermann-msgs

# Horloge de référence pour la Jetson
sudo apt install chrony
echo -e "allow <sous-réseau>\nlocal stratum 10" | sudo tee -a /etc/chrony/chrony.conf
sudo systemctl restart chrony

# Pare-feu : laisser passer ROS
sudo ufw allow from <sous-réseau>

# Le code
git clone https://github.com/JasonChmn/Robocar_ROS2.git
```

**`ROS_DOMAIN_ID` : obligatoire, et différent pour chaque équipe.** Tous les appareils qui ont le même ID sur un même réseau se voient. Deux équipes avec le même ID pourraient **commander la voiture de l'autre**.
- La règle : le numéro de votre département sur deux chiffres (Hauts-de-Seine → 92). Avec plusieurs équipes dans le même département, arrangez-vous en faisant ±1.
- Corse → 20. Outre-mer → entre 96 et 101.
- Jamais 0 (la valeur par défaut de tout le monde), jamais plus de 101.
- La valeur doit être **identique** dans `~/Robocar_ROS2/.env` sur la Jetson (lu par les conteneurs) et dans vos terminaux sur le PC (ci-dessous).

Dans chaque terminal du PC (ou dans votre `~/.bashrc`) :

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=<votre numéro> ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
```

### Pourquoi ces réglages

| Réglage | Pourquoi | Sans lui |
|---|---|---|
| chrony sur le PC | La Nano n'a pas de pile pour son horloge : elle démarre à une date fausse, et prend l'heure sur votre PC. ROS horodate tous les messages | RViz et le SLAM rejettent les données (`extrapolation into the future`, écran vide) |
| `ufw allow` | Le pare-feu d'Ubuntu bloque le trafic ROS entrant | `ros2 topic list` voit les topics, mais `echo` ne reçoit rien |
| `ROS_DOMAIN_ID` | Isoler chaque équipe | Une équipe voit, voire commande, la voiture d'une autre |
| `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` | Découvrir les nœuds de la Jetson sur le réseau local | Le PC ne voit aucun topic de la voiture |

La Jetson prend l'heure sur une IP fixe, donnée à `setup_host.sh` (en général `10.42.0.1`). Si l'IP de votre PC est différente, relancez sur la Jetson `sudo ~/Robocar_ROS2/host/setup_host.sh <IP_PC>`.

## 3. Lancer la voiture

Sur la Jetson :

```bash
cd ~/Robocar_ROS2
docker compose -f docker/compose.yaml --profile control --profile lidar up -d   # conduite + LiDAR
docker compose -f docker/compose.yaml logs -f control                           # logs (Ctrl+C pour quitter)
docker compose -f docker/compose.yaml down                                      # tout arrêter
```

Chaque brique est un service, activé par son **profil** : `control` (VESC, manette, odométrie, TF), `lidar`, `camera_3d_oak`, `camera`. Lancez seulement ce qui est branché : `control` refuse de démarrer sans `/dev/vesc`.

Au démarrage de `control`, quelques erreurs `Out-of-sync with VESC` sont normales. Elles cessent après `Connected to VESC`.

Pour taper une commande ROS **sur la Jetson** :

```bash
rc() { docker compose -f ~/Robocar_ROS2/docker/compose.yaml exec control /entrypoint.sh "$@"; }
rc ros2 topic list
rc ros2 topic echo /sensors/core --once   # tension batterie (voltage_input), fautes (fault_code)
```

Sur le **PC** (réglé au §2), les mêmes commandes `ros2` marchent directement. Pour RViz :

```bash
rviz2   # Fixed Frame : base_link ; Add → LaserScan /scan (Size 0,03) ; Add → TF ; Add → Odometry /odom
```

Un périphérique débranché puis rebranché n'est plus vu par son conteneur : `docker compose -f docker/compose.yaml up -d --force-recreate control` (ou `lidar`).

## 4. Manette et sécurité

| Bouton | Effet |
|---|---|
| Rien | La voiture est à l'arrêt, même si votre nœud publie `/drive` |
| **LB maintenu** | Conduite manuelle : stick gauche = vitesse, stick droit = direction |
| **RB maintenu** | **Votre nœud conduit** : `/drive` passe |
| RB + LB | La manette reprend la main sur votre nœud |

**RB est un bouton d'homme mort** : tant qu'il n'est pas maintenu, rien de ce que publie votre nœud n'atteint le moteur. La voiture s'arrête en moins de 0,2 s dans chacun de ces cas :
- RB relâché ;
- manette perdue ;
- votre nœud planté ;
- plus de `/drive` pendant 0,1 s.

Détail : `ARCHITECTURE.md`, « Chaîne de sécurité ».

**Règles :**
- Les **premiers essais d'un nouveau code se font roues en l'air** (la voiture posée sur une cale).
- Au sol, une personne tient **toujours** la manette, le pouce sur RB.
- Surveillez la batterie (`voltage_input` dans `/sensors/core`) : **arrêt sous 14,0 V**.
- La vitesse est limitée à ±5000 ERPM (`config/vesc.yaml`), soit environ 1 m/s. C'est approximatif tant que `speed_to_erpm_gain` n'est pas calibré. N'augmentez la limite que progressivement.

## 5. Écrire son nœud

Votre nœud publie des `ackermann_msgs/msg/AckermannDriveStamped` sur **`/drive`**, à **plus de 10 Hz**. En dessous, la sécurité envoie des zéros entre deux messages et la voiture avance par à-coups.

| Champ | Unité | Limites |
|---|---|---|
| `drive.speed` | m/s, + = avant | ~±1 m/s (limité par `vesc.yaml`). Échelle pas encore calibrée : la vitesse réelle peut différer |
| `drive.steering_angle` | rad, **+ = gauche** (REP-103) | ±0,34 rad |

Exemple minimal, qui avance tout droit à 0,5 m/s :

```python
import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped


class Avance(Node):
    def __init__(self):
        super().__init__('avance')
        self.pub = self.create_publisher(AckermannDriveStamped, 'drive', 10)
        self.create_timer(0.05, self.tick)   # 20 Hz

    def tick(self):
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.drive.speed = 0.5
        msg.drive.steering_angle = 0.0
        self.pub.publish(msg)


def main():
    rclpy.init()
    rclpy.spin(Avance())


if __name__ == '__main__':
    main()
```

Pour lire le LiDAR, abonnez-vous à `/scan` (`sensor_msgs/msg/LaserScan`, ~10 Hz, frame `laser`). Pour l'odométrie : `/odom`. Tous les topics sont listés dans `ARCHITECTURE.md`.

**Où le lancer :**
- **sur le PC** : `python3 mon_noeud.py`. C'est le plus simple pour développer, mais une coupure réseau prive la voiture de commande. La voiture s'arrête, sans danger ;
- **sur la Jetson**, dans un conteneur avec l'image de la voiture (conseillé pour rouler) :
  ```bash
  docker run --rm -it --network host --ipc host --env-file ~/Robocar_ROS2/.env \
    -v ~/mon_code:/code robocar:jazzy python3 /code/mon_noeud.py
  ```

### Où faire tourner quoi

| Brique | Conseil | Pourquoi |
|---|---|---|
| Nœud qui publie `/drive` | Plutôt la Jetson | Pas de latence ni de coupure réseau dans la boucle |
| Perception, traitement d'image | Au choix | La Nano est limitée (4 cœurs A57). Sur le PC, les images passent par le réseau : utilisez `/.../compressed` |
| SLAM, planification | Au choix | Mesurez la charge de la Nano avec `tegrastats` |
| RViz, Foxglove | PC | Pas d'écran sur la voiture pendant qu'elle roule, et RViz est trop lourd pour la Nano |

**Mesurez avant d'optimiser** : `ros2 topic hz <topic>` (fréquence), `ros2 topic bw <topic>` (débit), `tegrastats` sur la Jetson (CPU, RAM, température).

## 6. Dépannage

| Symptôme | Solution |
|---|---|
| `ERREUR : ROS_DOMAIN_ID='' invalide` | Remplir `ROS_DOMAIN_ID` dans `~/Robocar_ROS2/.env` sur la Jetson |
| Le PC ne voit aucun topic | Même `ROS_DOMAIN_ID` des deux côtés ? `ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` ? |
| Les topics sont visibles, mais `echo` ne reçoit rien | `sudo ufw allow from <sous-réseau>` sur le PC |
| RViz vide, `extrapolation into the future` | Horloge : `chronyc sources` sur la Jetson doit afficher `^*` devant votre PC. Sinon, IP du PC changée : relancer `setup_host.sh <IP_PC>` |
| LB et RB ne font rien | Manette en mode X ? Dongle branché avant `up` ? Sinon `up -d --force-recreate control` |
| La vitesse est en tout ou rien, ou sur la croix | LED MODE allumée : appuyez sur MODE |
| Votre nœud publie, mais rien ne bouge | RB maintenu ? `/drive` à plus de 10 Hz ? Vérifiez avec `ros2 topic hz /drive` |
| `control` ne démarre pas | VESC branché **et** alimenté ? `ls -l /dev/vesc` |
| La Jetson s'éteint toute seule | Batterie trop basse, ou alimentation par micro-USB au lieu du jack |
