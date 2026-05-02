#!/usr/bin/env python3
"""
QuantumCommRelay - Main Simulation
100-satellite LEO quantum network with BB84 QKD
Entanglement distribution, repeater chains, and security monitoring
Full mission simulation for quantum-secured space communication

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from qubit import Qubit, Basis, HADAMARD, EntangledPair, BellState
from bb84 import BB84Protocol, QuantumChannel as BB84Channel, BB84Alice, BB84Bob
from entanglement import EntanglementManager, EntanglementLink, EntanglementGenerator
from quantum_repeater import QuantumRepeater, RepeaterNetwork
from leo_channel import LEOQuantumChannel, LinkType, OrbitalState
from eavesdropper import (EavesdropperSimulator, SecurityMonitor,
                          AttackType, AlertLevel)
from satellite_network import SatelliteQuantumNetwork


class QuantumCommRelaySimulator:
    def __init__(self, num_satellites: int = 100,
                 simulation_time_s: float = 3600.0,
                 time_step_s: float = 10.0):
        self.num_satellites = num_satellites
        self.simulation_time_s = simulation_time_s
        self.time_step_s = time_step_s
        self.elapsed_time_s = 0.0

        self.satellite_network = SatelliteQuantumNetwork(
            num_satellites=num_satellites,
            num_planes=10,
            altitude_km=500.0,
        )
        self.entanglement_manager = EntanglementManager()
        self.repeater_network = RepeaterNetwork(num_nodes=10)
        self.security_monitor = SecurityMonitor()
        self.leo_channel = LEOQuantumChannel(LinkType.SATELLITE_TO_SATELLITE)

        self.qkd_sessions: List[Dict] = []
        self.attack_events: List[Dict] = []
        self.routes_established: List[Dict] = []

        self.simulation_stats = {
            "total_qkd_sessions": 0,
            "successful_sessions": 0,
            "total_keys_bits": 0,
            "average_qber": 0.0,
            "attacks_detected": 0,
            "attacks_blocked": 0,
            "entangled_pairs_created": 0,
            "entangled_pairs_lost": 0,
            "repeater_swaps": 0,
            "routes_found": 0,
            "routes_failed": 0,
            "satellites_eclipsed": 0,
        }

    def run_simulation(self):
        print("=" * 70)
        print("  QuantumCommRelay - Full Mission Simulation")
        print(f"  {self.num_satellites} satellites | "
              f"{self.simulation_time_s/3600:.1f} hours | "
              f"{self.time_step_s}s time step")
        print("=" * 70)
        print()

        step = 0
        while self.elapsed_time_s < self.simulation_time_s:
            self.satellite_network.update_positions(self.time_step_s)

            if step % 30 == 0:
                self._run_qkd_sessions()

            if step % 50 == 0:
                self._simulate_eavesdropper_attack()

            if step % 20 == 0:
                self._create_entangled_pairs()

            if step % 100 == 0:
                self._update_security_status()

            if step % 60 == 0:
                self._print_status()

            self.elapsed_time_s += self.time_step_s
            step += 1

        self._print_final_report()

    def _run_qkd_sessions(self):
        active_sats = [sid for sid, sat in self.satellite_network.satellites.items()
                      if not sat.is_eclipsed]
        if len(active_sats) < 2:
            return

        num_sessions = min(5, len(active_sats) // 2)
        for _ in range(num_sessions):
            src = np.random.choice(active_sats)
            dst = np.random.choice([s for s in active_sats if s != src])

            result = self.satellite_network.run_qkd_session(src, dst, key_length=256)
            self.simulation_stats["total_qkd_sessions"] += 1

            if result["success"]:
                self.simulation_stats["successful_sessions"] += 1
                self.simulation_stats["total_keys_bits"] += result.get("keys_exchanged", 0)
                self.simulation_stats["routes_found"] += 1

                self.qkd_sessions.append({
                    "time_s": self.elapsed_time_s,
                    "source": src,
                    "target": dst,
                    "hops": result["hops"],
                    "distance_km": result["distance_km"],
                    "keys_exchanged": result.get("keys_exchanged", 0),
                })
            else:
                self.simulation_stats["routes_failed"] += 1

    def _simulate_eavesdropper_attack(self):
        attack_types = [
            AttackType.INTERCEPT_RESEND,
            AttackType.BEAM_SPLITTING,
            AttackType.MAN_IN_THE_MIDDLE,
            AttackType.PHOTON_NUMBER_SPLITTING,
        ]

        attack_type = np.random.choice(attack_types)
        eve = EavesdropperSimulator(attack_type)

        if np.random.random() < 0.3:
            eve.set_stealth(True)

        test_qubits = [Qubit(1.0, 0.0) for _ in range(200)]
        for q in test_qubits:
            q.apply_gate(HADAMARD)

        if attack_type == AttackType.MAN_IN_THE_MIDDLE:
            bases_a = [Basis(np.random.randint(0, 2)) for _ in range(200)]
            bases_b = [Basis(np.random.randint(0, 2)) for _ in range(200)]
            _, qber = eve.man_in_the_middle(test_qubits, bases_a, bases_b)
        elif attack_type == AttackType.BEAM_SPLITTING:
            _, qber = eve.beam_splitting_attack(test_qubits)
        elif attack_type == AttackType.PHOTON_NUMBER_SPLITTING:
            _, qber = eve.photon_number_splitting(test_qubits)
        else:
            _, qber = eve.intercept_resend(test_qubits)

        self.security_monitor.record_measurement(qber, "SAT-A", "SAT-B")

        if self.security_monitor.detect_attack_pattern() is not None:
            self.simulation_stats["attacks_detected"] += 1
            measure = self.security_monitor.apply_countermeasure(attack_type)
            self.attack_events.append({
                "time_s": self.elapsed_time_s,
                "attack_type": attack_type.name,
                "qber_induced": qber,
                "detected": True,
                "countermeasure": measure,
            })
        else:
            self.attack_events.append({
                "time_s": self.elapsed_time_s,
                "attack_type": attack_type.name,
                "qber_induced": qber,
                "detected": False,
            })

    def _create_entangled_pairs(self):
        active_sats = [sid for sid, sat in self.satellite_network.satellites.items()
                      if not sat.is_eclipsed]
        if len(active_sats) < 2:
            return

        for _ in range(3):
            src = np.random.choice(active_sats)
            dst = np.random.choice([s for s in active_sats if s != src])
            dist = self.satellite_network.calculate_distance(src, dst)
            link = self.entanglement_manager.create_and_distribute(
                f"QSAT-{src:03d}", f"QSAT-{dst:03d}", distance_km=dist)

            if link:
                self.simulation_stats["entangled_pairs_created"] += 1
                self.satellite_network.satellites[src].entangled_links[dst] = link
            else:
                self.simulation_stats["entangled_pairs_lost"] += 1

    def _update_security_status(self):
        report = self.security_monitor.get_security_report()
        self.simulation_stats["average_qber"] = report["average_qber"]
        self.simulation_stats["attacks_blocked"] = (
            self.simulation_stats["attacks_detected"])

    def _print_status(self):
        hours = self.elapsed_time_s / 3600.0
        stats = self.satellite_network.get_network_statistics()
        print(f"[T+{hours:5.1f}h] "
              f"Sats: {stats['active_satellites']}/{stats['total_satellites']} | "
              f"QKD: {self.simulation_stats['successful_sessions']} | "
              f"Keys: {self.simulation_stats['total_keys_bits']:,}b | "
              f"Entangled: {self.simulation_stats['entangled_pairs_created']} | "
              f"Attacks: {self.simulation_stats['attacks_detected']} | "
              f"QBER: {self.simulation_stats['average_qber']*100:.2f}%")

    def _print_final_report(self):
        print("\n")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              QUANTUMCOMMRELAY - MISSION COMPLETE              ║")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║ Simulation time: {self.elapsed_time_s/3600:.1f} hours "
              f"({self.elapsed_time_s:.0f} seconds)")
        print(f"║ Satellites: {self.num_satellites}")
        print(f"║ Orbital altitude: 500 km | Inclination: 97.4°")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║ QKD Sessions: {self.simulation_stats['total_qkd_sessions']}")
        print(f"║ Successful: {self.simulation_stats['successful_sessions']} "
              f"({self.simulation_stats['successful_sessions']/max(1,self.simulation_stats['total_qkd_sessions'])*100:.1f}%)")
        print(f"║ Total keys generated: {self.simulation_stats['total_keys_bits']:,} bits")
        print(f"║ Average QBER: {self.simulation_stats['average_qber']*100:.2f}%")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║ Entangled pairs created: {self.simulation_stats['entangled_pairs_created']}")
        print(f"║ Entangled pairs lost: {self.simulation_stats['entangled_pairs_lost']}")
        print(f"║ Routes found: {self.simulation_stats['routes_found']}")
        print(f"║ Routes failed: {self.simulation_stats['routes_failed']}")
        print("╠══════════════════════════════════════════════════════════════╣")
        print(f"║ Attacks detected: {self.simulation_stats['attacks_detected']}")
        print(f"║ Attacks blocked: {self.simulation_stats['attacks_blocked']}")
        print(f"║ Security status: {'✓ SECURE' if self.simulation_stats['average_qber'] < 0.11 else '⚠ COMPROMISED'}")
        print("╠══════════════════════════════════════════════════════════════╣")
        print("║ Protocol: BB84 + E91 | Topology: LEO Walker Constellation  ║")
        print("║ Status: OPERATIONAL - Quantum-secured communication active ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    def save_report(self, filepath: str = "quantum_mission_report.json"):
        report = {
            "generated_at": datetime.now().isoformat(),
            "simulation_duration_s": self.elapsed_time_s,
            "num_satellites": self.num_satellites,
            "statistics": self.simulation_stats,
            "qkd_sessions": self.qkd_sessions[-20:],
            "attack_events": self.attack_events[-20:],
            "network_summary": self.satellite_network.get_network_statistics(),
            "security_report": self.security_monitor.get_security_report(),
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n[Report] Full mission report saved to: {filepath}")


def demo_quick():
    print("=" * 70)
    print("  QuantumCommRelay - Quick Demo (100 satellites, 600s)")
    print("=" * 70)
    sim = QuantumCommRelaySimulator(
        num_satellites=100,
        simulation_time_s=600.0,
        time_step_s=10.0,
    )
    sim.run_simulation()
    sim.save_report("quick_demo_report.json")


def demo_full():
    print("=" * 70)
    print("  QuantumCommRelay - Full Mission (100 satellites, 3600s)")
    print("=" * 70)
    sim = QuantumCommRelaySimulator(
        num_satellites=100,
        simulation_time_s=3600.0,
        time_step_s=10.0,
    )
    sim.run_simulation()
    sim.save_report("full_mission_report.json")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "full":
        demo_full()
    else:
        demo_quick()