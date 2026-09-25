"""Test de la chaîne de sécurité (docs/ROBOCAR_TO_DO_ROS2.md §2), sans manette ni VESC.

Simule /joy (50 Hz) et /drive (50 Hz), et observe /commands/motor/speed.
Lancement, dans le conteneur où tourne
`ros2 launch robocar_bringup control.launch.py with_joy:=false with_vesc:=false` :
    python3 tests/test_safety_chain.py [--kill-mux]
--kill-mux tue ackermann_mux en dernier test (il faut relancer le launch ensuite).
"""
import subprocess
import sys
import threading
import time

import rclpy
from ackermann_msgs.msg import AckermannDriveStamped
from rclpy.node import Node
from sensor_msgs.msg import Joy
from std_msgs.msg import Float64

LB, RB, A = 4, 5, 0
GAIN = 4614.0


class Tester(Node):

    def __init__(self):
        super().__init__('safety_tester')
        self.joy_pub = self.create_publisher(Joy, 'joy', 10)
        self.drive_pub = self.create_publisher(AckermannDriveStamped, 'drive', 10)
        self.create_subscription(Float64, 'commands/motor/speed', self.on_speed, 50)
        self.speeds = []  # (t, value)

    def on_speed(self, msg):
        self.speeds.append((time.monotonic(), msg.data))

    def spin_for(self, duration, joy_buttons=None, joy_axes=None, drive=None, on_start=None):
        """joy_buttons None = pas de /joy ; drive None = pas de /drive."""
        if on_start:
            threading.Thread(target=on_start).start()
        end = time.monotonic() + duration
        next_joy = next_drive = time.monotonic()
        while time.monotonic() < end:
            now = time.monotonic()
            if joy_buttons is not None and now >= next_joy:
                j = Joy()
                j.header.stamp = self.get_clock().now().to_msg()
                j.axes = joy_axes or [0.0] * 6
                j.buttons = [0] * 16
                for b in joy_buttons:
                    j.buttons[b] = 1
                self.joy_pub.publish(j)
                next_joy = now + 0.02
            if drive is not None and now >= next_drive:
                d = AckermannDriveStamped()
                d.header.stamp = self.get_clock().now().to_msg()
                d.drive.speed = drive
                self.drive_pub.publish(d)
                next_drive = now + 0.02
            rclpy.spin_once(self, timeout_sec=0.005)


def window(node, t0, t1):
    return [v for t, v in node.speeds if t0 <= t <= t1]


def main():
    rclpy.init()
    n = Tester()
    n.spin_for(3.0)  # découverte DDS
    results = []

    def case(name, expect, **kw):
        n.speeds.clear()
        t0 = time.monotonic()
        n.spin_for(1.5, **kw)
        vals = window(n, t0 + 0.5, time.monotonic())
        ok = bool(vals) and all(abs(v - expect) < 1.0 for v in vals)
        results.append(ok)
        uniq = sorted(set(round(v) for v in vals))
        print(f"{'OK ' if ok else 'ÉCHEC'} {name}: attendu {expect}, reçu {uniq} ({len(vals)} msgs)")

    def stop_case(name, before, after):
        n.spin_for(1.0, **before)
        n.speeds.clear()
        t_cut = time.monotonic()
        n.spin_for(1.0, **after)
        # délai jusqu'au premier 0 après la coupure
        zeros = [t for t, v in n.speeds if abs(v) < 1.0]
        tail = [v for t, v in n.speeds if t > t_cut + 0.4]
        delay = (zeros[0] - t_cut) if zeros else None
        ok = delay is not None and delay < 0.3 and tail and all(abs(v) < 1.0 for v in tail)
        results.append(ok)
        d = f'{delay * 1000:.0f} ms' if delay is not None else 'jamais'
        print(f"{'OK ' if ok else 'ÉCHEC'} {name}: arrêt après {d}")

    case('sans manette, /drive 1 m/s', 0.0, drive=1.0)
    case('RB maintenu, /drive 1 m/s', GAIN, joy_buttons=[RB], drive=1.0)
    case('aucun bouton, /drive 1 m/s', 0.0, joy_buttons=[], drive=1.0)
    case('bouton A (pas RB), /drive 1 m/s', 0.0, joy_buttons=[A], drive=1.0)
    case('LB + stick 0,5, /drive 1 m/s', GAIN * 0.5, joy_buttons=[LB],
         joy_axes=[0.0, 0.5, 0.0, 0.0, 0.0, 0.0], drive=1.0)
    case('LB + RB + stick 0,5, /drive 1 m/s', GAIN * 0.5, joy_buttons=[LB, RB],
         joy_axes=[0.0, 0.5, 0.0, 0.0, 0.0, 0.0], drive=1.0)
    stop_case('RB relâché', dict(joy_buttons=[RB], drive=1.0), dict(joy_buttons=[], drive=1.0))
    stop_case('manette morte (plus de /joy)', dict(joy_buttons=[RB], drive=1.0), dict(drive=1.0))
    stop_case('/drive coupé', dict(joy_buttons=[RB], drive=1.0), dict(joy_buttons=[RB]))

    if '--kill-mux' in sys.argv:
        def kill_mux():
            subprocess.run(['pkill', '-9', '-f', 'ackermann_mux/ackermann_mux'])
        stop_case('mux tué', dict(joy_buttons=[RB], drive=1.0), dict(joy_buttons=[RB], drive=1.0,
                                                                     on_start=kill_mux))

    print(f'{sum(results)}/{len(results)} OK')
    rclpy.shutdown()


if __name__ == '__main__':
    main()
