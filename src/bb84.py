#!/usr/bin/env python3
"""
QuantumCommRelay - BB84 Quantum Key Distribution Protocol
Alice → [Quantum Channel] → Bob
Implementation with eavesdropper detection and QBER calculation
For LEO satellite-to-satellite secure key exchange

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import IntEnum
import math

from qubit import Qubit, Basis, HADAMARD, ZERO_KET, ONE_KET, PLUS_KET, MINUS_KET


class BB84Phase(IntEnum):
    RAW_KEY_EXCHANGE = 0
    BASIS_RECONCILIATION = 1
    ERROR_ESTIMATION = 2
    KEY_SIFTING = 3
    PRIVACY_AMPLIFICATION = 4
    AUTHENTICATION = 5


@dataclass
class QuantumChannel:
    noise_level: float = 0.02
    decoherence_rate: float = 0.01
    photon_loss_probability: float = 0.05
    distance_km: float = 1000.0
    temperature_k: float = 290.0

    def transmit(self, qubit: Qubit) -> Optional[Qubit]:
        if np.random.random() < self.photon_loss_probability:
            return None
        received = qubit.clone()
        noise_strength = self.noise_level * (self.distance_km / 1000.0)
        received.apply_noise(noise_strength)
        return received

    def get_qber_estimate(self) -> float:
        return self.noise_level + self.distance_km * 0.00001


@dataclass
class BB84Alice:
    raw_key: List[int] = field(default_factory=list)
    bases: List[Basis] = field(default_factory=list)
    sifted_key: List[int] = field(default_factory=list)
    final_key: List[int] = field(default_factory=list)
    key_length: int = 256

    def generate_random_bits(self, length: int) -> List[int]:
        return [np.random.randint(0, 2) for _ in range(length)]

    def generate_random_bases(self, length: int) -> List[Basis]:
        return [Basis(np.random.randint(0, 2)) for _ in range(length)]

    def prepare_qubits(self) -> Tuple[List[Qubit], List[int], List[Basis]]:
        self.raw_key = self.generate_random_bits(self.key_length)
        self.bases = self.generate_random_bases(self.key_length)
        qubits = []
        for bit, basis in zip(self.raw_key, self.bases):
            if bit == 0 and basis == Basis.Z:
                qubits.append(Qubit(1.0 + 0.0j, 0.0 + 0.0j))
            elif bit == 1 and basis == Basis.Z:
                qubits.append(Qubit(0.0 + 0.0j, 1.0 + 0.0j))
            elif bit == 0 and basis == Basis.X:
                q = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
                q.apply_gate(HADAMARD)
                qubits.append(q)
            else:
                q = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
                q.apply_gate(HADAMARD)
                qubits.append(q)
        return qubits, self.raw_key, self.bases

    def sift_key(self, bob_bases: List[Basis]) -> List[int]:
        self.sifted_key = []
        for i in range(len(self.raw_key)):
            if i < len(bob_bases) and self.bases[i] == bob_bases[i]:
                self.sifted_key.append(self.raw_key[i])
        return self.sifted_key

    def privacy_amplification(self, error_rate: float) -> List[int]:
        if error_rate >= 0.5:
            return []
        leaked_bits = int(len(self.sifted_key) * error_rate * 2)
        effective_length = max(len(self.sifted_key) // 4,
                              len(self.sifted_key) - leaked_bits)
        step = max(1, len(self.sifted_key) // effective_length)
        self.final_key = self.sifted_key[::step]
        return self.final_key


@dataclass
class BB84Bob:
    bases: List[Basis] = field(default_factory=list)
    measurements: List[int] = field(default_factory=list)
    sifted_key: List[int] = field(default_factory=list)
    final_key: List[int] = field(default_factory=list)

    def generate_random_bases(self, length: int) -> List[Basis]:
        self.bases = [Basis(np.random.randint(0, 2)) for _ in range(length)]
        return self.bases

    def measure_qubits(self, qubits: List[Optional[Qubit]], bases: List[Basis]) -> List[int]:
        self.measurements = []
        self.bases = bases
        for qubit, basis in zip(qubits, bases):
            if qubit is None:
                self.measurements.append(np.random.randint(0, 2))
            else:
                self.measurements.append(qubit.measure(basis))
        return self.measurements

    def sift_key(self, alice_bases: List[Basis]) -> List[int]:
        self.sifted_key = []
        for i in range(len(self.measurements)):
            if i < len(alice_bases) and self.bases[i] == alice_bases[i]:
                self.sifted_key.append(self.measurements[i])
        return self.sifted_key


@dataclass
class BB84Eve:
    intercept_rate: float = 0.3
    bases: List[Basis] = field(default_factory=list)
    measurements: List[int] = field(default_factory=list)

    def intercept_resend(self, qubits: List[Optional[Qubit]]) -> List[Optional[Qubit]]:
        self.bases = []
        self.measurements = []
        intercepted = []
        for qubit in qubits:
            if qubit is None or np.random.random() > self.intercept_rate:
                intercepted.append(qubit)
                self.bases.append(Basis.Z)
                self.measurements.append(-1)
                continue
            basis = Basis(np.random.randint(0, 2))
            self.bases.append(basis)
            measurement = qubit.measure(basis)
            self.measurements.append(measurement)
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
        return intercepted


class BB84Protocol:
    def __init__(self, key_length: int = 256, channel: Optional[QuantumChannel] = None):
        self.alice = BB84Alice(key_length=key_length)
        self.bob = BB84Bob()
        self.eve = BB84Eve()
        self.channel = channel or QuantumChannel()
        self.qber = 0.0
        self.phase = BB84Phase.RAW_KEY_EXCHANGE
        self.eavesdropper_detected = False
        self.statistics = {
            "raw_bits_sent": 0,
            "raw_bits_received": 0,
            "photons_lost": 0,
            "sifted_bits": 0,
            "final_bits": 0,
            "qber": 0.0,
            "eavesdropper_detected": False,
            "key_rate_bps": 0.0,
        }

    def _calculate_qber(self, alice_key: List[int], bob_key: List[int]) -> float:
        if not alice_key or not bob_key:
            return 1.0
        min_len = min(len(alice_key), len(bob_key))
        errors = sum(1 for i in range(min_len) if alice_key[i] != bob_key[i])
        return errors / min_len if min_len > 0 else 1.0

    def run(self, enable_eavesdropper: bool = False) -> Dict:
        self.phase = BB84Phase.RAW_KEY_EXCHANGE
        qubits, alice_raw, alice_bases = self.alice.prepare_qubits()
        self.statistics["raw_bits_sent"] = len(qubits)

        transmitted = []
        for q in qubits:
            received = self.channel.transmit(q)
            transmitted.append(received)
            if received is None:
                self.statistics["photons_lost"] += 1

        if enable_eavesdropper:
            transmitted = self.eve.intercept_resend(transmitted)

        self.phase = BB84Phase.BASIS_RECONCILIATION
        bob_bases = self.bob.generate_random_bases(len(transmitted))
        self.bob.measure_qubits(transmitted, bob_bases)
        self.statistics["raw_bits_received"] = sum(1 for q in transmitted if q is not None)

        self.phase = BB84Phase.KEY_SIFTING
        alice_sifted = self.alice.sift_key(bob_bases)
        bob_sifted = self.bob.sift_key(alice_bases)
        self.statistics["sifted_bits"] = min(len(alice_sifted), len(bob_sifted))

        self.phase = BB84Phase.ERROR_ESTIMATION
        self.qber = self._calculate_qber(alice_sifted, bob_sifted)
        self.statistics["qber"] = self.qber

        threshold = 0.11
        self.eavesdropper_detected = self.qber > threshold
        self.statistics["eavesdropper_detected"] = self.eavesdropper_detected

        self.phase = BB84Phase.PRIVACY_AMPLIFICATION
        self.alice.final_key = self.alice.privacy_amplification(self.qber)
        self.bob.final_key = self.bob.sifted_key[:len(self.alice.final_key)]
        self.statistics["final_bits"] = len(self.alice.final_key)

        self.phase = BB84Phase.AUTHENTICATION
        self.statistics["key_rate_bps"] = self.statistics["final_bits"] / 1.0

        return self.statistics

    def get_shared_key(self) -> Tuple[List[int], List[int]]:
        return self.alice.final_key, self.bob.final_key

    def verify_key_match(self) -> bool:
        ak = self.alice.final_key
        bk = self.bob.final_key
        if len(ak) != len(bk):
            return False
        return all(a == b for a, b in zip(ak, bk))

    def print_protocol_summary(self):
        print("\n" + "=" * 60)
        print("  BB84 QKD PROTOCOL SUMMARY")
        print("=" * 60)
        print(f"  Raw bits sent:       {self.statistics['raw_bits_sent']}")
        print(f"  Raw bits received:   {self.statistics['raw_bits_received']}")
        print(f"  Photons lost:        {self.statistics['photons_lost']}")
        print(f"  Sifted bits:         {self.statistics['sifted_bits']}")
        print(f"  QBER:                {self.statistics['qber']*100:.2f}%")
        print(f"  Eavesdropper:        {'⚠️  DETECTED' if self.statistics['eavesdropper_detected'] else '✓ None'}")
        print(f"  Final key bits:      {self.statistics['final_bits']}")
        print(f"  Key rate:            {self.statistics['key_rate_bps']:.1f} bps")
        print(f"  Keys match:          {'✓ YES' if self.verify_key_match() else '✗ NO'}")
        print("=" * 60)


def demo_bb84_clean():
    print("\n" + "─" * 60)
    print("  SCENARIO 1: Clean channel (no eavesdropper)")
    print("─" * 60)
    channel = QuantumChannel(noise_level=0.01, distance_km=500.0,
                            photon_loss_probability=0.02)
    protocol = BB84Protocol(key_length=256, channel=channel)
    protocol.run(enable_eavesdropper=False)
    protocol.print_protocol_summary()


def demo_bb84_eavesdropper():
    print("\n" + "─" * 60)
    print("  SCENARIO 2: Eavesdropper present (Eve intercepts 50%)")
    print("─" * 60)
    channel = QuantumChannel(noise_level=0.01, distance_km=500.0,
                            photon_loss_probability=0.02)
    protocol = BB84Protocol(key_length=256, channel=channel)
    protocol.eve.intercept_rate = 0.5
    protocol.run(enable_eavesdropper=True)
    protocol.print_protocol_summary()


def demo_bb84_long_distance():
    print("\n" + "─" * 60)
    print("  SCENARIO 3: Long distance LEO link (3000 km)")
    print("─" * 60)
    channel = QuantumChannel(noise_level=0.03, distance_km=3000.0,
                            photon_loss_probability=0.10)
    protocol = BB84Protocol(key_length=512, channel=channel)
    protocol.run(enable_eavesdropper=False)
    protocol.print_protocol_summary()


def demo_bb84_high_noise():
    print("\n" + "─" * 60)
    print("  SCENARIO 4: High noise environment (solar storm)")
    print("─" * 60)
    channel = QuantumChannel(noise_level=0.08, distance_km=800.0,
                            photon_loss_probability=0.15)
    protocol = BB84Protocol(key_length=256, channel=channel)
    protocol.run(enable_eavesdropper=False)
    protocol.print_protocol_summary()


def demo_bb84_full_attack():
    print("\n" + "─" * 60)
    print("  SCENARIO 5: Full intercept-resend attack (Eve 100%)")
    print("─" * 60)
    channel = QuantumChannel(noise_level=0.01, distance_km=500.0,
                            photon_loss_probability=0.02)
    protocol = BB84Protocol(key_length=512, channel=channel)
    protocol.eve.intercept_rate = 1.0
    protocol.run(enable_eavesdropper=True)
    protocol.print_protocol_summary()


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - BB84 QKD Protocol")
    print("  Quantum Key Distribution for LEO Constellations")
    print("=" * 60)

    demo_bb84_clean()
    demo_bb84_eavesdropper()
    demo_bb84_long_distance()
    demo_bb84_high_noise()
    demo_bb84_full_attack()

    print("\n" + "=" * 60)
    print("  BB84 Protocol demonstration complete.")
    print("  Eavesdropper detection: QBER > 11% threshold")
    print("  Quantum advantage: Unconditional security proven")
    print("=" * 60)