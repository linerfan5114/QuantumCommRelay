#!/usr/bin/env python3
"""
QuantumCommRelay - Entanglement Management
EPR pair generation, distribution, and entanglement swapping
Enables quantum repeaters for LEO satellite constellations

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import IntEnum
import math
import time

from qubit import Qubit, Basis, EntangledPair, HADAMARD, CNOT, PAULI_X, PAULI_Z, ZERO_KET, ONE_KET


class BellState(IntEnum):
    PHI_PLUS = 0
    PHI_MINUS = 1
    PSI_PLUS = 2
    PSI_MINUS = 3


@dataclass
class EntanglementLink:
    pair: EntangledPair
    node_a: str = "Alice"
    node_b: str = "Bob"
    created_at: float = 0.0
    fidelity: float = 1.0
    distance_km: float = 0.0
    active: bool = True
    measurements_done: int = 0
    correlation_quality: float = 1.0

    def __post_init__(self):
        self.created_at = time.time()


@dataclass
class QuantumMemory:
    stored_qubits: List[Qubit] = field(default_factory=list)
    max_capacity: int = 10
    decoherence_rate: float = 0.001
    storage_time: float = 0.0

    def store(self, qubit: Qubit) -> bool:
        if len(self.stored_qubits) >= self.max_capacity:
            return False
        self.stored_qubits.append(qubit.clone())
        return True

    def retrieve(self, index: int = 0) -> Optional[Qubit]:
        if not self.stored_qubits:
            return None
        if index >= len(self.stored_qubits):
            index = len(self.stored_qubits) - 1
        qubit = self.stored_qubits.pop(index)
        noise = self.decoherence_rate * self.storage_time
        qubit.apply_noise(noise)
        return qubit

    def age(self, dt: float):
        self.storage_time += dt
        for qubit in self.stored_qubits:
            qubit.apply_noise(self.decoherence_rate * dt)


class EntanglementGenerator:
    def __init__(self):
        self.pairs_created = 0
        self.success_rate = 0.98

    def create_bell_pair(self, state: BellState = BellState.PHI_PLUS) -> EntangledPair:
        self.pairs_created += 1
        if np.random.random() > self.success_rate:
            return self._create_degraded_pair(state)
        return self._create_perfect_pair(state)

    def _create_perfect_pair(self, state: BellState) -> EntangledPair:
        if state == BellState.PHI_PLUS:
            return EntangledPair.create_phi_plus()
        elif state == BellState.PHI_MINUS:
            return EntangledPair.create_phi_minus()
        elif state == BellState.PSI_PLUS:
            return EntangledPair.create_psi_plus()
        else:
            return EntangledPair.create_psi_minus()

    def _create_degraded_pair(self, state: BellState) -> EntangledPair:
        pair = self._create_perfect_pair(state)
        pair.qubit_a.apply_noise(np.random.uniform(0.05, 0.15))
        return pair

    def create_multiple_pairs(self, count: int,
                             state: BellState = BellState.PHI_PLUS) -> List[EntangledPair]:
        return [self.create_bell_pair(state) for _ in range(count)]


class EntanglementDistributor:
    def __init__(self):
        self.distributed_pairs = 0
        self.lost_photons = 0
        self.active_links: List[EntanglementLink] = []

    def distribute(self, pair: EntangledPair, node_a: str, node_b: str,
                   distance_km: float = 0.0) -> Optional[EntanglementLink]:
        loss_probability = min(0.5, distance_km * 0.0002)
        if np.random.random() < loss_probability:
            self.lost_photons += 1
            return None
        decoherence = distance_km * 0.00001
        pair.qubit_a.apply_noise(decoherence)
        pair.qubit_b.apply_noise(decoherence)
        fidelity = 1.0 - decoherence * 5
        fidelity = max(0.0, min(1.0, fidelity))
        link = EntanglementLink(
            pair=pair,
            node_a=node_a,
            node_b=node_b,
            fidelity=fidelity,
            distance_km=distance_km,
        )
        self.active_links.append(link)
        self.distributed_pairs += 1
        return link

    def get_link_quality(self, link: EntanglementLink) -> float:
        if not link.active:
            return 0.0
        age_factor = math.exp(-0.01 * (time.time() - link.created_at))
        return link.fidelity * age_factor * link.correlation_quality


class EntanglementSwapper:
    def __init__(self):
        self.swaps_performed = 0
        self.successful_swaps = 0

    def swap(self, link_ab: EntanglementLink,
             link_bc: EntanglementLink) -> Optional[EntanglementLink]:
        if link_ab.node_b != link_bc.node_a:
            return None
        self.swaps_performed += 1
        success_probability = link_ab.fidelity * link_bc.fidelity * 0.75
        if np.random.random() > success_probability:
            return None
        self.successful_swaps += 1
        new_pair = EntangledPair()
        combined_fidelity = link_ab.fidelity * link_bc.fidelity
        total_distance = link_ab.distance_km + link_bc.distance_km
        new_link = EntanglementLink(
            pair=new_pair,
            node_a=link_ab.node_a,
            node_b=link_bc.node_b,
            fidelity=combined_fidelity,
            distance_km=total_distance,
        )
        link_ab.active = False
        link_bc.active = False
        return new_link

    def create_repeater_chain(self, pairs: List[EntanglementLink]) -> Optional[EntanglementLink]:
        if not pairs or len(pairs) < 2:
            return pairs[0] if pairs else None
        current = pairs[0]
        for i in range(1, len(pairs)):
            result = self.swap(current, pairs[i])
            if result is None:
                return None
            current = result
        return current

    def get_success_rate(self) -> float:
        if self.swaps_performed == 0:
            return 1.0
        return self.successful_swaps / self.swaps_performed


class QuantumTeleporter:
    def __init__(self):
        self.teleportations = 0
        self.successful = 0
        self.average_fidelity = 0.0
        self._fidelities: List[float] = []

    def teleport(self, qubit: Qubit,
                 entangled_pair: EntangledPair) -> Optional[Qubit]:
        self.teleportations += 1
        if np.random.random() > entangled_pair.check_correlation(100):
            return None
        combined = np.kron(qubit.state, entangled_pair.combined)
        bell_measurement = np.random.randint(0, 4)
        corrections = {
            0: np.eye(2, dtype=np.complex128),
            1: PAULI_X,
            2: PAULI_Z,
            3: PAULI_X @ PAULI_Z,
        }
        correction = corrections[bell_measurement]
        teleported_state = np.dot(correction, entangled_pair.qubit_b.state)
        teleported_state = teleported_state / np.linalg.norm(teleported_state)
        result = Qubit(teleported_state[0], teleported_state[1])
        fidelity = qubit.fidelity(result)
        self._fidelities.append(fidelity)
        self.average_fidelity = np.mean(self._fidelities)
        if fidelity > 0.9:
            self.successful += 1
        return result

    def get_statistics(self) -> Dict:
        return {
            "teleportations": self.teleportations,
            "successful": self.successful,
            "success_rate": self.successful / max(1, self.teleportations),
            "average_fidelity": self.average_fidelity,
        }


class EntanglementManager:
    def __init__(self):
        self.generator = EntanglementGenerator()
        self.distributor = EntanglementDistributor()
        self.swapper = EntanglementSwapper()
        self.teleporter = QuantumTeleporter()
        self.memory_a = QuantumMemory(max_capacity=10)
        self.memory_b = QuantumMemory(max_capacity=10)
        self.stats = {
            "pairs_created": 0,
            "pairs_distributed": 0,
            "pairs_lost": 0,
            "swaps_performed": 0,
            "teleportations": 0,
            "active_links": 0,
        }

    def create_and_distribute(self, node_a: str, node_b: str,
                              distance_km: float = 1000.0,
                              state: BellState = BellState.PHI_PLUS) -> Optional[EntanglementLink]:
        pair = self.generator.create_bell_pair(state)
        self.stats["pairs_created"] += 1
        link = self.distributor.distribute(pair, node_a, node_b, distance_km)
        if link:
            self.stats["pairs_distributed"] += 1
            self.memory_a.store(pair.qubit_a)
            self.memory_b.store(pair.qubit_b)
        else:
            self.stats["pairs_lost"] += 1
        self.stats["active_links"] = len(self.distributor.active_links)
        return link

    def extend_link_via_swapping(self, link1: EntanglementLink,
                                 link2: EntanglementLink) -> Optional[EntanglementLink]:
        new_link = self.swapper.swap(link1, link2)
        if new_link:
            self.stats["swaps_performed"] += 1
            self.stats["active_links"] = len(self.distributor.active_links)
        return new_link

    def teleport_qubit(self, qubit: Qubit,
                       link: EntanglementLink) -> Optional[Qubit]:
        result = self.teleporter.teleport(qubit, link.pair)
        if result:
            self.stats["teleportations"] += 1
        return result

    def refresh_stored_qubits(self, dt: float = 1.0):
        self.memory_a.age(dt)
        self.memory_b.age(dt)

    def get_network_status(self) -> Dict:
        return {
            **self.stats,
            "generator_success_rate": self.generator.success_rate,
            "swapper_success_rate": self.swapper.get_success_rate(),
            "teleporter_stats": self.teleporter.get_statistics(),
            "memory_a_usage": len(self.memory_a.stored_qubits),
            "memory_b_usage": len(self.memory_b.stored_qubits),
        }


def demo_bell_pairs():
    print("\n" + "─" * 60)
    print("  DEMO 1: Bell State Generation")
    print("─" * 60)
    gen = EntanglementGenerator()
    for state in BellState:
        pair = gen.create_bell_pair(state)
        a = pair.measure_a()
        b = pair.measure_b()
        correlation = pair.check_correlation(500)
        print(f"  {state.name:12s}: A={a} B={b} Anti-correlated={a!=b} "
              f"Corr={correlation:.3f}")


def demo_distribution():
    print("\n" + "─" * 60)
    print("  DEMO 2: Entanglement Distribution over Distance")
    print("─" * 60)
    manager = EntanglementManager()
    distances = [100, 500, 1000, 2000, 3000]
    for d in distances:
        link = manager.create_and_distribute("SAT-A", "SAT-B", distance_km=d)
        if link:
            quality = manager.distributor.get_link_quality(link)
            print(f"  {d:5d} km: ✓ Distributed, Fidelity={link.fidelity:.4f}, "
                  f"Quality={quality:.4f}")
        else:
            print(f"  {d:5d} km: ✗ Photon lost")


def demo_entanglement_swapping():
    print("\n" + "─" * 60)
    print("  DEMO 3: Entanglement Swapping (Quantum Repeater)")
    print("─" * 60)
    manager = EntanglementManager()
    link_ab = manager.create_and_distribute("SAT-A", "SAT-B", distance_km=800)
    link_bc = manager.create_and_distribute("SAT-B", "SAT-C", distance_km=800)
    if link_ab and link_bc:
        print(f"  AB Link: Fidelity={link_ab.fidelity:.4f}")
        print(f"  BC Link: Fidelity={link_bc.fidelity:.4f}")
        link_ac = manager.extend_link_via_swapping(link_ab, link_bc)
        if link_ac:
            print(f"  AC Link (after swap): Fidelity={link_ac.fidelity:.4f}")
            print(f"  Total distance: {link_ac.distance_km:.0f} km")
        else:
            print("  ✗ Swapping failed")


def demo_quantum_teleportation():
    print("\n" + "─" * 60)
    print("  DEMO 4: Quantum Teleportation")
    print("─" * 60)
    manager = EntanglementManager()
    link = manager.create_and_distribute("SAT-A", "SAT-B", distance_km=500)
    if link:
        original = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
        original.apply_gate(HADAMARD)
        print(f"  Original state: {original}")
        teleported = manager.teleport_qubit(original, link)
        if teleported:
            fidelity = original.fidelity(teleported)
            print(f"  Teleported state: {teleported}")
            print(f"  Fidelity: {fidelity:.6f}")
            print(f"  {'✓ Success' if fidelity > 0.9 else '✗ Failed'}")


def demo_repeater_chain():
    print("\n" + "─" * 60)
    print("  DEMO 5: Multi-hop Quantum Repeater Chain")
    print("─" * 60)
    manager = EntanglementManager()
    nodes = ["SAT-1", "SAT-2", "SAT-3", "SAT-4", "SAT-5"]
    links = []
    for i in range(len(nodes) - 1):
        link = manager.create_and_distribute(nodes[i], nodes[i+1], distance_km=600)
        if link:
            links.append(link)
            print(f"  {nodes[i]} ↔ {nodes[i+1]}: ✓ Fidelity={link.fidelity:.4f}")
        else:
            print(f"  {nodes[i]} ↔ {nodes[i+1]}: ✗ Lost")
    if len(links) >= 2:
        chain = manager.swapper.create_repeater_chain(links)
        if chain:
            print(f"\n  Repeater chain: {chain.node_a} ↔ {chain.node_b}")
            print(f"  End-to-end fidelity: {chain.fidelity:.4f}")
            print(f"  Total distance: {chain.distance_km:.0f} km")
    print(f"\n  Swapper success rate: {manager.swapper.get_success_rate()*100:.1f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - Entanglement Management")
    print("  EPR Pairs, Distribution, Swapping, Teleportation")
    print("=" * 60)

    demo_bell_pairs()
    demo_distribution()
    demo_entanglement_swapping()
    demo_quantum_teleportation()
    demo_repeater_chain()

    print("\n" + "=" * 60)
    print("  Entanglement subsystem operational.")
    print("  Quantum repeaters ready for LEO deployment.")
    print("=" * 60)