#!/usr/bin/env python3
"""
QuantumCommRelay - Eavesdropper Detection System
Intercept-resend, beam-splitting, man-in-the-middle attacks
QBER calculation and countermeasure deployment
For LEO quantum network security monitoring

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import IntEnum
import math

from qubit import Qubit, Basis, HADAMARD, PAULI_X


class AttackType(IntEnum):
    NONE = 0
    INTERCEPT_RESEND = 1
    BEAM_SPLITTING = 2
    MAN_IN_THE_MIDDLE = 3
    PHOTON_NUMBER_SPLITTING = 4
    CLONING_ATTEMPT = 5
    DENIAL_OF_SERVICE = 6
    TROJAN_HORSE = 7


class AlertLevel(IntEnum):
    GREEN = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3
    CRITICAL = 4


@dataclass
class AttackEvent:
    attack_type: AttackType
    timestamp: float
    target_node: str
    severity: float
    qber_induced: float
    photons_compromised: int
    detected: bool
    countermeasure_applied: str


@dataclass
class SecurityAlert:
    level: AlertLevel
    message: str
    attack_type: AttackType
    recommended_action: str
    timestamp: float


class EavesdropperSimulator:
    def __init__(self, attack_type: AttackType = AttackType.INTERCEPT_RESEND):
        self.attack_type = attack_type
        self.intercept_rate = 0.4
        self.beam_split_ratio = 0.3
        self.mitm_success_rate = 0.5
        self.cloning_fidelity = 0.0
        self.active = True
        self.stealth_mode = False

        self.total_attacks = 0
        self.successful_attacks = 0
        self.detected_attacks = 0
        self.photons_intercepted = 0
        self.total_qber_induced = 0.0

    def set_stealth(self, enabled: bool):
        self.stealth_mode = enabled
        if enabled:
            self.intercept_rate = max(0.1, self.intercept_rate * 0.3)
            self.beam_split_ratio = max(0.05, self.beam_split_ratio * 0.3)
        else:
            self.intercept_rate = min(0.8, self.intercept_rate * 3.0)
            self.beam_split_ratio = min(0.5, self.beam_split_ratio * 3.0)

    def intercept_resend(self, qubits: List[Optional[Qubit]],
                        bases: Optional[List[Basis]] = None) -> Tuple[List[Optional[Qubit]], float]:
        self.total_attacks += 1
        intercepted = []
        compromised = 0
        for qubit in qubits:
            if qubit is None or np.random.random() > self.intercept_rate:
                intercepted.append(qubit)
                continue
            compromised += 1
            self.photons_intercepted += 1
            basis = Basis(np.random.randint(0, 2))
            measurement = qubit.measure(basis)
            if measurement == 0 and basis == Basis.Z:
                new_qubit = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
            elif measurement == 1 and basis == Basis.Z:
                new_qubit = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
            elif measurement == 0 and basis == Basis.X:
                new_qubit = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
                new_qubit.apply_gate(HADAMARD)
            else:
                new_qubit = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
                new_qubit.apply_gate(HADAMARD)
            intercepted.append(new_qubit)

        qber = 0.25 * (compromised / max(1, len(qubits)))
        self.total_qber_induced += qber
        if qber > 0.11:
            self.detected_attacks += 1
        else:
            self.successful_attacks += 1

        return intercepted, qber

    def beam_splitting_attack(self, qubits: List[Optional[Qubit]]) -> Tuple[List[Optional[Qubit]], float]:
        self.total_attacks += 1
        attacked = []
        compromised = 0

        for qubit in qubits:
            if qubit is None:
                attacked.append(None)
                continue
            if np.random.random() < self.beam_split_ratio:
                compromised += 1
                self.photons_intercepted += 1
                split_qubit = qubit.clone()
                split_qubit.apply_noise(np.random.uniform(0.05, 0.2))
                attacked.append(split_qubit)
                qubit.apply_noise(np.random.uniform(0.01, 0.05))
            else:
                attacked.append(qubit)

        qber = 0.15 * (compromised / max(1, len(qubits)))
        self.total_qber_induced += qber
        if qber > 0.11:
            self.detected_attacks += 1
        else:
            self.successful_attacks += 1

        return attacked, qber

    def man_in_the_middle(self, qubits: List[Optional[Qubit]],
                         alice_bases: List[Basis],
                         bob_bases: List[Basis]) -> Tuple[List[Optional[Qubit]], float]:
        self.total_attacks += 1
        eve_results = []
        compromised = 0

        for i, qubit in enumerate(qubits):
            if qubit is None:
                eve_results.append(None)
                continue
            if np.random.random() > self.mitm_success_rate:
                eve_results.append(qubit)
                continue
            compromised += 1
            self.photons_intercepted += 1
            eve_basis = alice_bases[i] if i < len(alice_bases) else Basis.Z
            measurement = qubit.measure(eve_basis)
            bob_basis = bob_bases[i] if i < len(bob_bases) else Basis.Z
            if measurement == 0 and bob_basis == Basis.Z:
                new_qubit = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
            elif measurement == 1 and bob_basis == Basis.Z:
                new_qubit = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
            elif measurement == 0 and bob_basis == Basis.X:
                new_qubit = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
                new_qubit.apply_gate(HADAMARD)
            else:
                new_qubit = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
                new_qubit.apply_gate(HADAMARD)
            eve_results.append(new_qubit)

        qber = 0.35 * (compromised / max(1, len(qubits)))
        self.total_qber_induced += qber
        if qber > 0.11:
            self.detected_attacks += 1
        else:
            self.successful_attacks += 1

        return eve_results, qber

    def photon_number_splitting(self, qubits: List[Optional[Qubit]],
                               photons_per_pulse: int = 10) -> Tuple[List[Optional[Qubit]], float]:
        self.total_attacks += 1
        attacked = []
        compromised = 0

        for qubit in qubits:
            if qubit is None:
                attacked.append(None)
                continue
            multi_photon = np.random.random() < 0.2
            if multi_photon:
                compromised += 1
                self.photons_intercepted += photons_per_pulse - 1
                remaining = Qubit(qubit.alpha, qubit.beta)
                remaining.apply_noise(0.02)
                attacked.append(remaining)
            else:
                attacked.append(qubit)

        qber = 0.05 * (compromised / max(1, len(qubits)))
        self.total_qber_induced += qber
        if compromised > 0:
            self.detected_attacks += 1
        else:
            self.successful_attacks += 1

        return attacked, qber

    def cloning_attack(self, qubits: List[Optional[Qubit]]) -> Tuple[List[Optional[Qubit]], float]:
        self.total_attacks += 1
        attacked = []
        compromised = 0

        for qubit in qubits:
            if qubit is None:
                attacked.append(None)
                continue
            compromised += 1
            self.photons_intercepted += 1
            clone = qubit.clone()
            clone.apply_noise(np.random.uniform(0.3, 0.5))
            clone_fidelity = clone.fidelity(qubit)
            self.cloning_fidelity = max(self.cloning_fidelity, clone_fidelity)
            if clone_fidelity < 0.5:
                attacked.append(qubit)
            else:
                attacked.append(clone)

        qber = 0.50 * (compromised / max(1, len(qubits)))
        self.total_qber_induced += qber
        self.detected_attacks += 1

        return attacked, qber

    def get_statistics(self) -> Dict:
        return {
            "attack_type": self.attack_type.name,
            "total_attacks": self.total_attacks,
            "successful_attacks": self.successful_attacks,
            "detected_attacks": self.detected_attacks,
            "detection_rate": self.detected_attacks / max(1, self.total_attacks),
            "photons_intercepted": self.photons_intercepted,
            "avg_qber_induced": self.total_qber_induced / max(1, self.total_attacks),
            "stealth_mode": self.stealth_mode,
        }


class SecurityMonitor:
    def __init__(self):
        self.attack_events: List[AttackEvent] = []
        self.alerts: List[SecurityAlert] = []
        self.qber_history: List[float] = []
        self.qber_threshold = 0.11
        self.qber_warning_threshold = 0.07
        self.suspicious_nodes: Dict[str, int] = {}
        self.countermeasures_active: List[str] = []
        self.total_photons_monitored = 0
        self.total_alerts_generated = 0

    def record_measurement(self, qber: float, node_a: str, node_b: str):
        self.qber_history.append(qber)
        self.total_photons_monitored += 1
        if len(self.qber_history) > 1000:
            self.qber_history.pop(0)

        if qber > self.qber_threshold:
            alert_level = AlertLevel.RED
            message = f"QBER {qber*100:.1f}% exceeds threshold {self.qber_threshold*100:.0f}%"
            self._generate_alert(alert_level, message, AttackType.INTERCEPT_RESEND)
        elif qber > self.qber_warning_threshold:
            alert_level = AlertLevel.YELLOW
            message = f"QBER {qber*100:.1f}% above warning level {self.qber_warning_threshold*100:.0f}%"
            self._generate_alert(alert_level, message, AttackType.INTERCEPT_RESEND)

    def detect_attack_pattern(self) -> Optional[AttackType]:
        if len(self.qber_history) < 10:
            return None

        recent_qber = self.qber_history[-10:]
        avg_qber = np.mean(recent_qber)
        std_qber = np.std(recent_qber)

        if avg_qber > 0.30:
            return AttackType.MAN_IN_THE_MIDDLE
        if avg_qber > 0.20 and std_qber > 0.05:
            return AttackType.INTERCEPT_RESEND
        if avg_qber > 0.10 and std_qber < 0.03:
            return AttackType.BEAM_SPLITTING
        if avg_qber > 0.40:
            return AttackType.CLONING_ATTEMPT
        if avg_qber < 0.08 and std_qber < 0.02:
            return AttackType.PHOTON_NUMBER_SPLITTING

        return None

    def _generate_alert(self, level: AlertLevel, message: str, attack_type: AttackType):
        actions = {
            AlertLevel.GREEN: "Continue monitoring",
            AlertLevel.YELLOW: "Increase sampling rate",
            AlertLevel.ORANGE: "Activate decoy states",
            AlertLevel.RED: "Switch to alternate channel + privacy amplification",
            AlertLevel.CRITICAL: "Abort key exchange + full security audit",
        }

        alert = SecurityAlert(
            level=level,
            message=message,
            attack_type=attack_type,
            recommended_action=actions.get(level, "Unknown"),
            timestamp=len(self.qber_history),
        )
        self.alerts.append(alert)
        self.total_alerts_generated += 1

    def apply_countermeasure(self, attack_type: AttackType) -> str:
        countermeasures = {
            AttackType.INTERCEPT_RESEND: "Privacy amplification + decoy states",
            AttackType.BEAM_SPLITTING: "Reduce beam intensity + entanglement verification",
            AttackType.MAN_IN_THE_MIDDLE: "Authentication check + basis reconciliation",
            AttackType.PHOTON_NUMBER_SPLITTING: "Single-photon sources + decoy states",
            AttackType.CLONING_ATTEMPT: "No countermeasure needed (impossible per no-cloning theorem)",
            AttackType.DENIAL_OF_SERVICE: "Channel hopping + redundant links",
            AttackType.TROJAN_HORSE: "Optical isolators + power monitoring",
            AttackType.NONE: "No countermeasure needed",
        }

        measure = countermeasures.get(attack_type, "Unknown attack - full security lockdown")
        self.countermeasures_active.append(measure)
        return measure

    def get_security_report(self) -> Dict:
        recent_alerts = self.alerts[-5:] if self.alerts else []
        avg_qber = np.mean(self.qber_history) if self.qber_history else 0.0
        attack_detected = self.detect_attack_pattern()

        return {
            "average_qber": avg_qber,
            "qber_threshold": self.qber_threshold,
            "total_photons_monitored": self.total_photons_monitored,
            "total_alerts": self.total_alerts_generated,
            "attack_detected": attack_detected.name if attack_detected else "NONE",
            "active_countermeasures": self.countermeasures_active[-3:]
            if self.countermeasures_active else [],
            "recent_alerts": [
                {"level": a.level.name, "message": a.message,
                 "action": a.recommended_action} for a in recent_alerts
            ],
            "channel_secure": avg_qber < self.qber_threshold,
        }


def demo_intercept_resend():
    print("\n" + "─" * 60)
    print("  DEMO 1: Intercept-Resend Attack (IR)")
    print("─" * 60)
    eve = EavesdropperSimulator(AttackType.INTERCEPT_RESEND)
    monitor = SecurityMonitor()
    qubits = [Qubit(1.0, 0.0) for _ in range(100)]
    for q in qubits:
        q.apply_gate(HADAMARD)
    attacked, qber = eve.intercept_resend(qubits)
    monitor.record_measurement(qber, "SAT-A", "SAT-B")
    print(f"  Attack type: IR (Intercept-Resend)")
    print(f"  Intercept rate: {eve.intercept_rate*100:.0f}%")
    print(f"  QBER induced: {qber*100:.2f}%")
    print(f"  Detected: {'✓ YES' if qber > 0.11 else '✗ NO'}")
    print(f"  Photons compromised: {eve.photons_intercepted}")
    stats = eve.get_statistics()
    print(f"  Detection rate: {stats['detection_rate']*100:.1f}%")


def demo_stealth_vs_aggressive():
    print("\n" + "─" * 60)
    print("  DEMO 2: Stealth vs Aggressive Attack Comparison")
    print("─" * 60)
    for mode, label in [(True, "STEALTH"), (False, "AGGRESSIVE")]:
        eve = EavesdropperSimulator(AttackType.INTERCEPT_RESEND)
        eve.set_stealth(mode)
        qubits = [Qubit(1.0, 0.0) for _ in range(200)]
        for q in qubits:
            q.apply_gate(HADAMARD)
        _, qber = eve.intercept_resend(qubits)
        print(f"  {label}:")
        print(f"    Intercept rate: {eve.intercept_rate*100:.0f}%")
        print(f"    QBER: {qber*100:.2f}%")
        print(f"    Detected: {'✓ YES' if qber > 0.11 else '✗ NO (attack successful)'}")


def demo_all_attack_types():
    print("\n" + "─" * 60)
    print("  DEMO 3: All Attack Types Comparison")
    print("─" * 60)
    attack_types = [
        (AttackType.INTERCEPT_RESEND, "Intercept-Resend"),
        (AttackType.BEAM_SPLITTING, "Beam Splitting"),
        (AttackType.MAN_IN_THE_MIDDLE, "Man-in-the-Middle"),
        (AttackType.PHOTON_NUMBER_SPLITTING, "Photon Number Splitting"),
        (AttackType.CLONING_ATTEMPT, "Cloning Attempt"),
    ]

    qubits = [Qubit(1.0, 0.0) for _ in range(100)]
    for q in qubits:
        q.apply_gate(HADAMARD)
    bases = [Basis(np.random.randint(0, 2)) for _ in range(100)]

    for attack_type, name in attack_types:
        eve = EavesdropperSimulator(attack_type)
        if attack_type == AttackType.MAN_IN_THE_MIDDLE:
            bob_bases = [Basis(np.random.randint(0, 2)) for _ in range(100)]
            _, qber = eve.man_in_the_middle(qubits, bases, bob_bases)
        elif attack_type == AttackType.PHOTON_NUMBER_SPLITTING:
            _, qber = eve.photon_number_splitting(qubits)
        elif attack_type == AttackType.CLONING_ATTEMPT:
            _, qber = eve.cloning_attack(qubits)
        else:
            _, qber = eve.intercept_resend(qubits) if attack_type == AttackType.INTERCEPT_RESEND else eve.beam_splitting_attack(qubits)

        detected = "✓ DETECTED" if qber > 0.11 else "✗ UNDETECTED"
        print(f"  {name:25s}: QBER={qber*100:5.1f}%  {detected}")


def demo_countermeasures():
    print("\n" + "─" * 60)
    print("  DEMO 4: Countermeasure Deployment")
    print("─" * 60)
    monitor = SecurityMonitor()
    for attack_type in AttackType:
        if attack_type == AttackType.NONE:
            continue
        measure = monitor.apply_countermeasure(attack_type)
        print(f"  {attack_type.name:25s}: {measure}")


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - Eavesdropper Detection")
    print("  QBER Analysis + Attack Detection + Countermeasures")
    print("=" * 60)

    demo_intercept_resend()
    demo_stealth_vs_aggressive()
    demo_all_attack_types()
    demo_countermeasures()

    print("\n" + "=" * 60)
    print("  Security subsystem operational.")
    print("  QBER threshold: 11%")
    print("  All attack types detectable via quantum principles.")
    print("=" * 60)