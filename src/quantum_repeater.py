#!/usr/bin/env python3
"""
QuantumCommRelay - Quantum Repeater
Entanglement swapping chain, error correction, and purification
Extends quantum communication range beyond direct-link limits
For LEO satellite constellation relay networks

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from collections import deque
import math
import time

from qubit import Qubit, EntangledPair, Basis, HADAMARD, CNOT, PAULI_X, PAULI_Z
from entanglement import EntanglementLink, BellState, EntanglementGenerator


@dataclass
class RepeaterNode:
    node_id: str
    position_km: Tuple[float, float, float] = (0.0, 0.0, 500.0)
    left_buffer: deque = field(default_factory=lambda: deque(maxlen=20))
    right_buffer: deque = field(default_factory=lambda: deque(maxlen=20))
    left_link: Optional[EntanglementLink] = None
    right_link: Optional[EntanglementLink] = None
    swap_success_count: int = 0
    swap_attempt_count: int = 0
    purification_count: int = 0
    is_active: bool = True
    uptime_hours: float = 0.0
    last_maintenance: float = 0.0

    def buffer_fill_level(self) -> float:
        total = len(self.left_buffer) + len(self.right_buffer)
        return total / (self.left_buffer.maxlen + self.right_buffer.maxlen)


@dataclass
class PurificationRound:
    input_fidelity: float = 0.0
    output_fidelity: float = 0.0
    consumed_pairs: int = 0
    success: bool = False


@dataclass
class RepeaterChain:
    nodes: List[RepeaterNode]
    links: List[EntanglementLink]
    end_to_end_fidelity: float = 0.0
    total_distance_km: float = 0.0
    hop_count: int = 0
    chain_active: bool = False
    created_at: float = 0.0

    def __post_init__(self):
        self.created_at = time.time()
        self.hop_count = len(self.links)
        self.total_distance_km = sum(link.distance_km for link in self.links)
        if self.links:
            self.end_to_end_fidelity = math.prod(link.fidelity for link in self.links)


class PurificationEngine:
    def __init__(self):
        self.rounds: List[PurificationRound] = []
        self.total_pairs_consumed = 0

    def purify(self, pair1: EntangledPair, pair2: EntangledPair) -> Optional[EntangledPair]:
        if not pair1 or not pair2:
            return None
        fidelity1 = self._estimate_fidelity(pair1)
        fidelity2 = self._estimate_fidelity(pair2)
        input_avg = (fidelity1 + fidelity2) / 2.0
        success_prob = 0.5 + (input_avg - 0.5) * 0.8
        success_prob = max(0.1, min(0.99, success_prob))
        self.total_pairs_consumed += 2
        if np.random.random() > success_prob:
            self.rounds.append(PurificationRound(
                input_fidelity=input_avg,
                output_fidelity=0.0,
                consumed_pairs=2,
                success=False,
            ))
            return None
        qubit_a1 = pair1.qubit_a
        qubit_a2 = pair2.qubit_a
        qubit_b1 = pair1.qubit_b
        qubit_b2 = pair2.qubit_b

        cnot_ab1 = np.kron(CNOT, np.eye(2, dtype=np.complex128))
        state_1a_2a = np.kron(qubit_a1.state, qubit_a2.state)
        state_1a_2a = np.dot(cnot_ab1[:4, :4], state_1a_2a[:4])

        output_fidelity = min(0.999, input_avg + (1.0 - input_avg) * 0.6)
        purified = EntangledPair.create_phi_plus()
        purified.qubit_a.apply_noise((1.0 - output_fidelity) * 0.1)

        self.rounds.append(PurificationRound(
            input_fidelity=input_avg,
            output_fidelity=output_fidelity,
            consumed_pairs=2,
            success=True,
        ))
        return purified

    def _estimate_fidelity(self, pair: EntangledPair) -> float:
        target = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
        target.apply_gate(HADAMARD)
        return max(0.5, pair.qubit_a.fidelity(target))

    def get_average_improvement(self) -> float:
        if not self.rounds:
            return 0.0
        improvements = []
        for r in self.rounds:
            if r.success:
                improvements.append(r.output_fidelity - r.input_fidelity)
        return np.mean(improvements) if improvements else 0.0


class ErrorCorrector:
    def __init__(self):
        self.corrections_applied = 0
        self.successful_corrections = 0
        self.syndrome_table = self._build_syndrome_table()

    def _build_syndrome_table(self) -> Dict[int, np.ndarray]:
        return {
            0: np.eye(2, dtype=np.complex128),
            1: PAULI_X,
            2: PAULI_Z,
            3: PAULI_X @ PAULI_Z,
        }

    def measure_syndrome(self, logical_qubit: np.ndarray) -> int:
        if logical_qubit.shape[0] < 3:
            return 0
        stabilizer_z = np.array([[1, 0, 0, 0], [0, -1, 0, 0],
                                 [0, 0, 1, 0], [0, 0, 0, -1]], dtype=np.complex128)
        syndrome = abs(np.dot(np.conjugate(logical_qubit[:4]),
                     np.dot(stabilizer_z, logical_qubit[:4])))
        if syndrome < 0.01:
            return 0
        elif syndrome > 0.99:
            return 1
        else:
            return 0

    def correct(self, qubit: Qubit, syndrome: int) -> Qubit:
        self.corrections_applied += 1
        if syndrome == 0:
            self.successful_corrections += 1
            return qubit.clone()
        correction = self.syndrome_table.get(syndrome, np.eye(2, dtype=np.complex128))
        corrected = qubit.clone()
        corrected.apply_gate(correction)
        self.successful_corrections += 1
        return corrected

    def get_success_rate(self) -> float:
        if self.corrections_applied == 0:
            return 1.0
        return self.successful_corrections / self.corrections_applied


class QuantumRepeater:
    def __init__(self, node_id: str, position: Tuple[float, float, float] = (0, 0, 500)):
        self.node = RepeaterNode(node_id=node_id, position_km=position)
        self.purifier = PurificationEngine()
        self.corrector = ErrorCorrector()
        self.generator = EntanglementGenerator()
        self.total_swaps = 0
        self.successful_swaps = 0

    def receive_link(self, link: EntanglementLink, side: str = "left"):
        if side == "left":
            if self.node.left_buffer:
                self.node.left_buffer.append(link)
            self.node.left_link = link
        else:
            if self.node.right_buffer:
                self.node.right_buffer.append(link)
            self.node.right_link = link

    def perform_swap(self) -> Optional[EntanglementLink]:
        if not self.node.left_link or not self.node.right_link:
            return None
        self.total_swaps += 1
        left_pair = self.node.left_link.pair
        right_pair = self.node.right_link.pair
        bell_measurement = np.random.randint(0, 4)
        corrections = {
            0: (np.eye(2), np.eye(2)),
            1: (PAULI_X, np.eye(2)),
            2: (PAULI_Z, np.eye(2)),
            3: (PAULI_X @ PAULI_Z, np.eye(2)),
        }
        corr_a, corr_b = corrections[bell_measurement]
        new_a = Qubit(left_pair.qubit_a.alpha, left_pair.qubit_a.beta)
        new_b = Qubit(right_pair.qubit_b.alpha, right_pair.qubit_b.beta)
        new_a.apply_gate(corr_a)
        new_b.apply_gate(corr_b)
        new_pair = EntangledPair()
        new_pair.qubit_a = new_a
        new_pair.qubit_b = new_b
        fidelity = (self.node.left_link.fidelity + self.node.right_link.fidelity) / 2.0
        fidelity *= 0.85
        distance = self.node.left_link.distance_km + self.node.right_link.distance_km
        new_link = EntanglementLink(
            pair=new_pair,
            node_a=self.node.left_link.node_a,
            node_b=self.node.right_link.node_b,
            fidelity=fidelity,
            distance_km=distance,
        )
        self.successful_swaps += 1
        self.node.swap_success_count += 1
        self.node.swap_attempt_count += 1
        self.node.left_link.active = False
        self.node.right_link.active = False
        self.node.left_link = None
        self.node.right_link = None
        return new_link

    def purify_stored_pairs(self) -> Optional[EntanglementLink]:
        left_pairs = list(self.node.left_buffer)
        if len(left_pairs) < 2:
            return None
        pair_a = left_pairs[0].pair
        pair_b = left_pairs[1].pair
        self.node.left_buffer.popleft()
        self.node.left_buffer.popleft()
        purified_pair = self.purifier.purify(pair_a, pair_b)
        if purified_pair is None:
            return None
        self.node.purification_count += 1
        fidelity = (pair_a.qubit_a.fidelity(Qubit(1, 0)) + pair_b.qubit_a.fidelity(Qubit(1, 0))) / 2.0
        fidelity = min(0.999, fidelity + 0.1)
        return EntanglementLink(
            pair=purified_pair,
            node_a=self.node.node_id,
            node_b=self.node.node_id + "-purified",
            fidelity=fidelity,
            distance_km=0,
        )

    def get_swap_success_rate(self) -> float:
        if self.total_swaps == 0:
            return 1.0
        return self.successful_swaps / self.total_swaps


class RepeaterNetwork:
    def __init__(self, num_nodes: int = 5,
                 orbit_radius_km: float = 6871.0,
                 orbit_inclination_deg: float = 97.0):
        self.nodes: List[QuantumRepeater] = []
        self.chains: List[RepeaterChain] = []
        self._init_nodes(num_nodes, orbit_radius_km, orbit_inclination_deg)

    def _init_nodes(self, num_nodes: int, radius: float, inclination: float):
        inc_rad = math.radians(inclination)
        for i in range(num_nodes):
            angle = 2.0 * math.pi * i / num_nodes
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) * math.cos(inc_rad)
            z = radius * math.sin(angle) * math.sin(inc_rad) + 500.0
            node_id = f"SAT-{i+1:02d}"
            self.nodes.append(QuantumRepeater(node_id, (x, y, z)))

    def get_node(self, index: int) -> Optional[QuantumRepeater]:
        if 0 <= index < len(self.nodes):
            return self.nodes[index]
        return None

    def build_chain(self, start_idx: int, end_idx: int) -> Optional[RepeaterChain]:
        if start_idx == end_idx:
            return None
        step = 1 if end_idx > start_idx else -1
        chain_nodes = []
        chain_links = []
        current = start_idx
        while current != end_idx:
            next_idx = current + step
            if next_idx < 0 or next_idx >= len(self.nodes):
                return None
            node_a = self.nodes[current]
            node_b = self.nodes[next_idx]
            link = self._create_link_between(node_a, node_b)
            if link is None:
                return None
            chain_nodes.append(node_a)
            chain_links.append(link)
            current = next_idx
        chain_nodes.append(self.nodes[end_idx])
        chain = RepeaterChain(
            nodes=[n.node for n in chain_nodes],
            links=chain_links,
            chain_active=True,
        )
        self.chains.append(chain)
        return chain

    def _create_link_between(self, node_a: QuantumRepeater,
                            node_b: QuantumRepeater) -> Optional[EntanglementLink]:
        dx = node_b.node.position_km[0] - node_a.node.position_km[0]
        dy = node_b.node.position_km[1] - node_a.node.position_km[1]
        dz = node_b.node.position_km[2] - node_a.node.position_km[2]
        distance = math.sqrt(dx**2 + dy**2 + dz**2)
        pair = node_a.generator.create_bell_pair(BellState.PHI_PLUS)
        link = EntanglementLink(
            pair=pair,
            node_a=node_a.node.node_id,
            node_b=node_b.node.node_id,
            fidelity=0.95 - distance * 0.00005,
            distance_km=distance,
        )
        return link

    def route_quantum_message(self, start_idx: int, end_idx: int) -> float:
        chain = self.build_chain(start_idx, end_idx)
        if chain is None:
            return 0.0
        for i in range(len(chain.nodes) - 2):
            repeater = self._find_repeater_for_node(chain.nodes[i+1].node_id)
            if repeater:
                repeater.perform_swap()
        return chain.end_to_end_fidelity

    def _find_repeater_for_node(self, node_id: str) -> Optional[QuantumRepeater]:
        for node in self.nodes:
            if node.node.node_id == node_id:
                return node
        return None

    def get_network_statistics(self) -> Dict:
        total_swaps = sum(n.total_swaps for n in self.nodes)
        successful_swaps = sum(n.successful_swaps for n in self.nodes)
        total_purifications = sum(n.node.purification_count for n in self.nodes)
        return {
            "num_nodes": len(self.nodes),
            "active_chains": len([c for c in self.chains if c.chain_active]),
            "total_swaps": total_swaps,
            "swap_success_rate": successful_swaps / max(1, total_swaps),
            "total_purifications": total_purifications,
            "avg_fidelity": np.mean([c.end_to_end_fidelity for c in self.chains])
            if self.chains else 0.0,
            "avg_distance_km": np.mean([c.total_distance_km for c in self.chains])
            if self.chains else 0.0,
        }


def demo_purification():
    print("\n" + "─" * 60)
    print("  DEMO 1: Entanglement Purification")
    print("─" * 60)
    engine = PurificationEngine()
    gen = EntanglementGenerator()
    for i in range(5):
        p1 = gen.create_bell_pair()
        p2 = gen.create_bell_pair()
        p1.qubit_a.apply_noise(0.05 * (i + 1))
        p2.qubit_a.apply_noise(0.05 * (i + 1))
        f1 = p1.qubit_a.fidelity(Qubit(1, 0))
        f2 = p2.qubit_a.fidelity(Qubit(1, 0))
        print(f"  Round {i+1}: Input fidelities: {f1:.4f}, {f2:.4f}")
        result = engine.purify(p1, p2)
        if result:
            print(f"    ✓ Purified, improvement: {engine.get_average_improvement():.4f}")
        else:
            print(f"    ✗ Purification failed")
    print(f"  Average fidelity improvement: {engine.get_average_improvement():.4f}")


def demo_repeater_swap():
    print("\n" + "─" * 60)
    print("  DEMO 2: Repeater Entanglement Swapping")
    print("─" * 60)
    repeater = QuantumRepeater("SAT-R1", (1000, 0, 500))
    gen = EntanglementGenerator()
    left_pair = gen.create_bell_pair()
    right_pair = gen.create_bell_pair()
    left_link = EntanglementLink(left_pair, "SAT-A", "SAT-R1", fidelity=0.95, distance_km=800)
    right_link = EntanglementLink(right_pair, "SAT-R1", "SAT-B", fidelity=0.95, distance_km=800)
    repeater.receive_link(left_link, "left")
    repeater.receive_link(right_link, "right")
    print(f"  Left link:  {left_link.node_a} ↔ {left_link.node_b}")
    print(f"  Right link: {right_link.node_a} ↔ {right_link.node_b}")
    result = repeater.perform_swap()
    if result:
        print(f"  After swap: {result.node_a} ↔ {result.node_b}")
        print(f"  End-to-end fidelity: {result.fidelity:.4f}")
        print(f"  Total distance: {result.distance_km:.0f} km")
    print(f"  Swap success rate: {repeater.get_swap_success_rate()*100:.1f}%")


def demo_network_routing():
    print("\n" + "─" * 60)
    print("  DEMO 3: Multi-hop Quantum Network Routing")
    print("─" * 60)
    network = RepeaterNetwork(num_nodes=8)
    print(f"  Network: {len(network.nodes)} satellites in LEO")
    for i in range(len(network.nodes)):
        node = network.nodes[i]
        print(f"    {node.node.node_id}: pos=({node.node.position_km[0]:.0f}, "
              f"{node.node.position_km[1]:.0f}, {node.node.position_km[2]:.0f}) km")
    fidelity = network.route_quantum_message(0, 4)
    print(f"\n  Route SAT-01 → SAT-05: Fidelity={fidelity:.4f}")
    fidelity = network.route_quantum_message(0, 7)
    print(f"  Route SAT-01 → SAT-08: Fidelity={fidelity:.4f}")
    stats = network.get_network_statistics()
    print(f"\n  Network Statistics:")
    print(f"    Active chains: {stats['active_chains']}")
    print(f"    Avg fidelity: {stats['avg_fidelity']:.4f}")
    print(f"    Avg distance: {stats['avg_distance_km']:.0f} km")


def demo_error_correction():
    print("\n" + "─" * 60)
    print("  DEMO 4: Quantum Error Correction")
    print("─" * 60)
    corrector = ErrorCorrector()
    q = Qubit(1.0, 0.0)
    q.apply_gate(HADAMARD)
    print(f"  Original state: {q}")
    q.apply_noise(0.1)
    print(f"  After noise:    {q}")
    syndrome = corrector.measure_syndrome(np.kron(q.state, np.array([1, 0])))
    print(f"  Syndrome: {syndrome}")
    q = corrector.correct(q, syndrome)
    print(f"  After correction: {q}")
    print(f"  Correction success rate: {corrector.get_success_rate()*100:.1f}%")


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - Quantum Repeater Network")
    print("  Entanglement Swapping + Purification + Error Correction")
    print("=" * 60)

    demo_purification()
    demo_repeater_swap()
    demo_network_routing()
    demo_error_correction()

    print("\n" + "=" * 60)
    print("  Quantum repeater subsystem operational.")
    print("  Multi-hop entanglement-based routing active.")
    print("=" * 60)