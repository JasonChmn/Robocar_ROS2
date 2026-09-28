#!/bin/bash
# Préparation de l'hôte Jetson Nano (L4T R32.7.1, Ubuntu 18.04). À lancer sur la Jetson :
#   sudo ./setup_host.sh <IP_PC>
# IP_PC : l'adresse du PC sur le réseau partagé avec la Jetson (ip -4 addr sur le PC).
# Faire d'abord une image dd de la carte SD (docs/ROBOCAR_TO_DO_ROS2.md, phase 0).
# Ne met pas Docker à jour : à faire à la main seulement si le test de la phase 0 échoue.
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage : sudo $0 <IP_PC>   (IP du PC qui sert d'horloge, voir ip -4 addr sur le PC)" >&2
    exit 1
fi
PC_IP="$1"
USER_NAME="${SUDO_USER:-robocar}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" != "0" ]; then
    echo "À lancer avec sudo" >&2
    exit 1
fi

echo "== Groupes docker, dialout, input pour $USER_NAME"
usermod -aG docker,dialout,input "$USER_NAME"

echo "== Swap de 4 Go (/swapfile)"
if ! swapon --show | grep -q /swapfile; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== Mode puissance max (nvpmodel -m 0)"
nvpmodel -m 0

echo "== chrony, synchronisé sur le PC ($PC_IP)"
# Côté PC : chrony installé avec « allow <sous-réseau> » et « local stratum 10 »
apt-get install -y chrony
cat > /etc/chrony/chrony.conf <<CONF
server $PC_IP iburst
# Pas de pile RTC sur la Nano : autoriser un saut d'heure aux premières mesures
makestep 1 3
driftfile /var/lib/chrony/chrony.drift
rtcsync
CONF
systemctl restart chrony

echo "== Règles udev"
cp "$HERE/99-robocar.rules" /etc/udev/rules.d/
udevadm control --reload-rules
udevadm trigger

echo "== Espace disque"
df -h /
docker system df || true

echo "Terminé. Se reconnecter pour que les groupes soient pris en compte."
