# Configuration du VESC (VESC Tool)

Configuration faite le 2026-09-25, VESC branché en USB sur le PC. Elle est stockée **dans le VESC** : elle survit aux coupures, et il n'y a rien à réappliquer au démarrage.

- `vesc_mcconf.xml` : configuration moteur (*Motor Settings*) ;
- `vesc_appconf.xml` : configuration de l'application (*App Settings*).

Pour une autre voiture avec le même matériel : dans VESC Tool, *File → Load Motor Configuration XML* et *Load App Configuration XML*, puis **Write** pour chacune. **Relancer quand même la détection FOC** (§3) : R, L et λ varient d'un moteur à l'autre.

## Matériel

| Élément | Valeur |
|---|---|
| VESC | **Hw 60** (famille VESC 6, probablement le Flipsky Mini V6.7 Pro), **Fw 7.00** (stable), MCU STM32F407 (`0483:5740`) |
| Châssis | Traxxas Ford Fiesta ST Rally **BL-2s**, 74154-4 |
| Moteur | **BL-2s 3300 kV**, inrunner 540, **4 pôles**, sans capteur, sans sonde de température. Prévu pour 2S |
| Batterie moteur | **Ovonic 4S 2200 mAh 120C** (14,8 V, 32,56 Wh). Ce n'est pas la batterie 3700 mAh notée ailleurs |
| Transmission (README du pédago) | pignon 13, couronne 36, roues de 83 mm (à confirmer à la règle). Ces valeurs ne servent qu'à l'affichage dans VESC Tool |

## EEPROM : pas corrompue

On pensait l'EEPROM corrompue, car la config semblait perdue à chaque démarrage. **Test du 2026-09-25** : on écrit une valeur, on coupe tout (LiPo et USB), on relit. **La valeur est gardée.**

La cause probable du problème était `vesc_autoconfig.sh` (`vesc-config.service`, ancien projet). À chaque démarrage, ce script modifie la config à des positions d'octets fixées à la main (`vesc_cli.py`, « ancre empirique »), puis relance une détection. Il écrasait donc la config.

**`vesc-config.service` est désactivé sur la Jetson** (`sudo systemctl disable --now vesc-config`). Ne pas le réactiver : avec un autre firmware, les positions ne correspondent plus, et le script écrirait n'importe quoi.

## Procédure suivie

### 1. Connexion

VESC en USB sur le PC, **LiPo moteur branchée** (nécessaire pour la détection), **roues en l'air**. L'utilisateur doit être dans le groupe `dialout`. **Connect**.

### 2. Assistant *Setup Motors FOC*

| Page | Choix | Remarque |
|---|---|---|
| Remise aux valeurs d'usine | **Yes** | Faire d'abord une sauvegarde XML. Les anciens scripts avaient modifié des réglages internes (openloop, etc.) |
| Usage | **Generic** | *Override advanced* décoché |
| Motor | **Small Inrunner** | Une catégorie plus grande autorise trop de courant pendant la détection et peut griller le moteur |
| Battery | **Li-ion 3.0/4.2 V**, **4** cellules, **2.2 Ah** | Même chimie que la LiPo. Les tensions de coupure sont corrigées ensuite (§4) |
| Setup | Direct drive décoché, 13 / 36, 83 mm, **4 pôles**, **pas de sonde de température** | Sans sonde branchée, une sonde NTC déclarée donnerait une température absurde |

Le README du pédago indiquait *Medium Outrunner*, 14 pôles et une sonde NTC : c'est une config de skate, qui ne correspond pas au BL-2s.

### 3. Détection

Le moteur siffle au début (mesure de R et L, rotor à l'arrêt), puis tourne quelques secondes (mesure de λ). Résultat :

| Mesure | Valeur |
|---|---|
| Motor R | 16,30 mΩ |
| Motor L | 8,82 µH |
| Lq − Ld | 3,81 µH |
| Flux linkage λ | 0,79 mWb (≈ 3500 kV avec 4 pôles : les 4 pôles sont confirmés) |
| Courant proposé par l'assistant | 45,17 A (réduit ensuite) |
| VESC ID | 70 |

### 4. Réglages manuels (*Motor Settings → General*)

| Onglet | Réglage | Valeur | Pourquoi |
|---|---|---|---|
| Current | Motor Current Max / Brake | **30 / −30 A** | Valeur de référence choisie (les anciens scripts allaient de 5 à 30 A) |
| | Battery Current Max / Regen | **20 / −10 A** | |
| | Absolute Maximum Current | 67,76 A (assistant) | Seuil de coupure d'urgence, laissé tel quel |
| Voltage | Battery Cutoff Start / End | **14,0 / 13,2 V** | 3,5 / 3,3 V par cellule. L'assistant (profil Li-ion) mettait 13,6 / 12,0 V, trop bas pour une LiPo |
| RPM | Max ERPM / Reverse | **30000 / −30000** | Limite matérielle : le BL-2s est prévu pour 2S (~55000 ERPM à vide) et tourne ici en 4S. ROS limite en plus à ±5000 (`vesc.yaml`) |

Le firmware refuse un *Battery Current Max* supérieur au *Motor Current Max* : il le tronque, et VESC Tool affiche « Parameters truncated ». Ce n'est pas un échec de l'écriture.

Puis **Write Motor Configuration** (icône **M** avec une flèche vers le bas).

### 5. App Settings → General

| Réglage | Valeur | Pourquoi |
|---|---|---|
| App to Use | **No App** | ROS passe par l'USB, qui marche avec n'importe quelle application. Pas PPM : l'entrée PPM utilise la même broche que le servo |
| Enable Servo Output | **True** | Sinon, la direction ne répond pas |
| Timeout | **500 ms** | Dernier filet de la chaîne de sécurité : le moteur s'arrête si plus aucune commande n'arrive (`vesc_driver` ou `ackermann_to_vesc` planté) |
| Timeout Brake Current | **5 A** | |

Puis **Write App Configuration** (icône **A** avec une flèche vers le bas). **Attention** : c'est un bouton distinct de celui du **M**. La première fois, seul le M avait été cliqué, et la config app n'avait pas été écrite.

### 6. Vérification

Couper tout (LiPo et USB), rebrancher, **Read** les deux configs et vérifier les valeurs, puis sauvegarder les deux en XML (*File*).

## Vérifié ensuite sous ROS (Jetson, 2026-09-25)

- `vesc_driver` : `Connected to VESC with firmware version 7.0`. Au démarrage, quelques erreurs `Out-of-sync` / `Invalid end-of-frame` (des octets restés dans le tampon), puis plus rien.
- `/sensors/core` : `voltage_input` 15,7 V, `fault_code` 0. `temp_fet` et `temp_motor` valent 0,0, peut-être un décalage de format entre le firmware 7.0 et le driver (à regarder).
- Le moteur suit la consigne : 2307 ERPM demandés → ~2350 mesurés, 3928 → ~4000, 4614 → ~4650. ~1,7 A à vide, avec un pic de ~26 A au démarrage.
