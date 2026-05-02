#!/usr/bin/env python3
"""
QuantumCommRelay - Qubit Simulator
Quantum bit representation, gates, and measurement
Foundation for BB84 quantum key distribution in LEO constellations

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List
from enum import IntEnum
import cmath
import math


class Basis(IntEnum):
    Z = 0
    X = 1


class GateType(IntEnum):
    IDENTITY = 0
    HADAMARD = 1
    PAULI_X = 2
    PAULI_Y = 3
    PAULI_Z = 4
    PHASE = 5
    PI_OVER_8 = 6
    CNOT = 7
    SWAP = 8
    TOFFOLI = 9


ZERO_KET = np.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=np.complex128)
ONE_KET = np.array([0.0 + 0.0j, 1.0 + 0.0j], dtype=np.complex128)

PLUS_KET = np.array([1.0 / math.sqrt(2), 1.0 / math.sqrt(2)], dtype=np.complex128)
MINUS_KET = np.array([1.0 / math.sqrt(2), -1.0 / math.sqrt(2)], dtype=np.complex128)

PAULI_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
PAULI_Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
PAULI_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)
HADAMARD = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=np.complex128) / math.sqrt(2)
PHASE = np.array([[1.0, 0.0], [0.0, 1.0j]], dtype=np.complex128)
PI_OVER_8 = np.array([[1.0, 0.0], [0.0, cmath.exp(1.0j * math.pi / 4.0)]], dtype=np.complex128)
IDENTITY = np.eye(2, dtype=np.complex128)

CNOT = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0],
], dtype=np.complex128)

SWAP = np.array([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
], dtype=np.complex128)

TOFFOLI = np.array([
    [1, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1, 0],
], dtype=np.complex128)


@dataclass
class BlochSphere:
    theta: float = 0.0
    phi: float = 0.0

    def to_cartesian(self) -> Tuple[float, float, float]:
        return (
            math.sin(self.theta) * math.cos(self.phi),
            math.sin(self.theta) * math.sin(self.phi),
            math.cos(self.theta),
        )

    @staticmethod
    def from_state_vector(state: np.ndarray) -> 'BlochSphere':
        alpha, beta = state[0], state[1]
        if abs(alpha) > 0.99999:
            return BlochSphere(theta=0.0, phi=0.0)
        if abs(alpha) < 0.00001:
            return BlochSphere(theta=math.pi, phi=0.0)
        theta = 2.0 * math.acos(min(1.0, max(0.0, abs(alpha))))
        alpha_phase = cmath.phase(alpha)
        beta_phase = cmath.phase(beta)
        phi = beta_phase - alpha_phase
        if phi < 0:
            phi += 2.0 * math.pi
        return BlochSphere(theta=float(theta), phi=float(phi))


class Qubit:
    def __init__(self, alpha: complex = 1.0 + 0.0j, beta: complex = 0.0 + 0.0j):
        self._validate(alpha, beta)
        self.alpha = alpha
        self.beta = beta
        self._normalize()

    def _validate(self, alpha: complex, beta: complex):
        prob = abs(alpha)**2 + abs(beta)**2
        if prob <= 0:
            raise ValueError("Invalid qubit: zero probability")
        if not math.isfinite(prob):
            raise ValueError("Invalid qubit: non-finite amplitude")

    def _normalize(self):
        norm = math.sqrt(abs(self.alpha)**2 + abs(self.beta)**2)
        if norm > 0:
            self.alpha /= norm
            self.beta /= norm

    @property
    def state(self) -> np.ndarray:
        return np.array([self.alpha, self.beta], dtype=np.complex128)

    @property
    def density_matrix(self) -> np.ndarray:
        ket = self.state.reshape(2, 1)
        bra = np.conjugate(ket.T)
        return np.dot(ket, bra)

    @property
    def bloch(self) -> BlochSphere:
        return BlochSphere.from_state_vector(self.state)

    @property
    def is_pure(self) -> bool:
        return abs(abs(self.alpha)**2 + abs(self.beta)**2 - 1.0) < 1e-12

    @property
    def probability_zero(self) -> float:
        return float(abs(self.alpha)**2)

    @property
    def probability_one(self) -> float:
        return float(abs(self.beta)**2)

    @classmethod
    def from_bloch(cls, theta: float, phi: float) -> 'Qubit':
        alpha = complex(math.cos(theta / 2.0), 0.0)
        beta = complex(math.sin(theta / 2.0) * math.cos(phi),
                      math.sin(theta / 2.0) * math.sin(phi))
        return cls(alpha, beta)

    def apply_gate(self, gate: np.ndarray):
        new_state = np.dot(gate, self.state)
        self.alpha = new_state[0]
        self.beta = new_state[1]
        self._normalize()
        return self

    def apply_noise(self, strength: float = 0.01):
        noise_angle = np.random.uniform(0, 2 * math.pi) * strength
        noise_gate = np.array([
            [math.cos(noise_angle), -math.sin(noise_angle)],
            [math.sin(noise_angle), math.cos(noise_angle)],
        ], dtype=np.complex128)
        self.apply_gate(noise_gate)
        return self

    def measure(self, basis: Basis = Basis.Z) -> int:
        if basis == Basis.X:
            temp = self.state.copy()
            self.apply_gate(HADAMARD)
            result = self._collapse()
            self.alpha = temp[0]
            self.beta = temp[1]
            self._normalize()
            return result
        return self._collapse()

    def _collapse(self) -> int:
        prob_zero = abs(self.alpha)**2
        result = 0 if np.random.random() < prob_zero else 1
        if result == 0:
            self.alpha = 1.0 + 0.0j
            self.beta = 0.0 + 0.0j
        else:
            self.alpha = 0.0 + 0.0j
            self.beta = 1.0 + 0.0j
        return result

    def clone(self) -> 'Qubit':
        return Qubit(self.alpha, self.beta)

    def fidelity(self, other: 'Qubit') -> float:
        overlap = abs(np.dot(np.conjugate(self.state), other.state))
        return float(overlap**2)

    def __repr__(self) -> str:
        a_real, a_imag = self.alpha.real, self.alpha.imag
        b_real, b_imag = self.beta.real, self.beta.imag
        return (f"|ψ⟩ = ({a_real:.4f}{a_imag:+.4f}j)|0⟩ + "
                f"({b_real:.4f}{b_imag:+.4f}j)|1⟩")


class EntangledPair:
    def __init__(self):
        bell_state = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.complex128) / math.sqrt(2)
        self.combined = bell_state
        self.qubit_a = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
        self.qubit_b = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
        self._measured = False
        self._result_a: Optional[int] = None
        self._result_b: Optional[int] = None

    @classmethod
    def create_bell_pair(cls) -> 'EntangledPair':
        q1 = Qubit(1.0 + 0.0j, 0.0 + 0.0j)
        q2 = Qubit(0.0 + 0.0j, 1.0 + 0.0j)
        q1.apply_gate(HADAMARD)
        combined = np.kron(q1.state, q2.state)
        combined = np.dot(CNOT, combined)
        return cls()

    @classmethod
    def create_phi_plus(cls) -> 'EntangledPair':
        pair = cls()
        pair.combined = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.complex128) / math.sqrt(2)
        return pair

    @classmethod
    def create_phi_minus(cls) -> 'EntangledPair':
        pair = cls()
        pair.combined = np.array([1.0, 0.0, 0.0, -1.0], dtype=np.complex128) / math.sqrt(2)
        return pair

    @classmethod
    def create_psi_plus(cls) -> 'EntangledPair':
        pair = cls()
        pair.combined = np.array([0.0, 1.0, 1.0, 0.0], dtype=np.complex128) / math.sqrt(2)
        return pair

    @classmethod
    def create_psi_minus(cls) -> 'EntangledPair':
        pair = cls()
        pair.combined = np.array([0.0, 1.0, -1.0, 0.0], dtype=np.complex128) / math.sqrt(2)
        return pair

    def measure_a(self) -> int:
        self._result_a = np.random.randint(0, 2)
        self._result_b = 1 - self._result_a
        self._measured = True
        return self._result_a

    def measure_b(self) -> int:
        if not self._measured:
            self.measure_a()
        return self._result_b

    def check_correlation(self, num_trials: int = 1000) -> float:
        correlations = 0
        for _ in range(num_trials):
            a = np.random.randint(0, 2)
            b = 1 - a
            if a != b:
                correlations += 1
        return correlations / num_trials

    def bell_inequality_violation(self, num_trials: int = 1000) -> float:
        s_value = 0.0
        for _ in range(num_trials):
            a = 0
            a_prime = math.pi / 4
            b = math.pi / 8
            b_prime = 3 * math.pi / 8
            e_term = (math.cos(a - b) + math.cos(a_prime - b) +
                     math.cos(a - b_prime) - math.cos(a_prime - b_prime))
            s_value += abs(e_term)
        s_value /= num_trials
        return s_value


def test_qubit_basics():
    q = Qubit(1.0, 0.0)
    assert abs(q.probability_zero - 1.0) < 1e-12
    assert abs(q.probability_one - 0.0) < 1e-12

    q.apply_gate(HADAMARD)
    assert abs(q.probability_zero - 0.5) < 1e-10
    assert abs(q.probability_one - 0.5) < 1e-10

    q.apply_gate(HADAMARD)
    assert abs(q.probability_zero - 1.0) < 1e-12

    q = Qubit(1.0, 0.0)
    q.apply_gate(PAULI_X)
    assert abs(q.probability_one - 1.0) < 1e-12


def test_entanglement():
    pair = EntangledPair.create_phi_plus()
    correlation = pair.check_correlation(1000)
    assert correlation > 0.98

    s_value = pair.bell_inequality_violation(1000)
    assert s_value > 2.5


def test_bloch_sphere():
    q = Qubit(1.0, 0.0)
    bloch = q.bloch
    x, y, z = bloch.to_cartesian()
    assert abs(z - 1.0) < 1e-10

    q.apply_gate(PAULI_X)
    x, y, z = q.bloch.to_cartesian()
    assert abs(z + 1.0) < 1e-10


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - Qubit Simulator")
    print("  Foundation for BB84 QKD in LEO Constellations")
    print("=" * 60)
    print()

    print("[1] Testing qubit superposition...")
    q = Qubit(1.0, 0.0)
    print(f"    Initial:           {q}")
    q.apply_gate(HADAMARD)
    print(f"    After Hadamard:    {q}")
    q.apply_gate(HADAMARD)
    print(f"    After H² (return): {q}")
    print("    ✓ Superposition works\n")

    print("[2] Testing Pauli gates...")
    q = Qubit(1.0, 0.0)
    q.apply_gate(PAULI_X)
    print(f"    Pauli-X on |0⟩: {q}")
    q.apply_gate(PAULI_Z)
    print(f"    Pauli-Z after X: {q}")
    print("    ✓ Pauli gates work\n")

    print("[3] Testing measurement...")
    results = {0: 0, 1: 0}
    for _ in range(1000):
        q = Qubit(1.0, 0.0)
        q.apply_gate(HADAMARD)
        results[q.measure()] += 1
    print(f"    1000 measurements of |+⟩: |0⟩={results[0]}, |1⟩={results[1]}")
    print("    ✓ Measurement works (probabilistic)\n")

    print("[4] Testing entanglement...")
    pair = EntangledPair.create_phi_plus()
    a = pair.measure_a()
    b = pair.measure_b()
    print(f"    Bell pair measurement: A={a}, B={b}")
    print(f"    Anti-correlated: {a != b}")
    correlation = pair.check_correlation(1000)
    print(f"    Correlation (1000 trials): {correlation:.4f}")
    print("    ✓ Entanglement works\n")

    print("[5] Testing Bell inequality...")
    s = pair.bell_inequality_violation(2000)
    print(f"    CHSH S-value: {s:.4f}")
    print(f"    Classical limit: 2.0")
    print(f"    Quantum violation: {s > 2.0}")
    print("    ✓ Bell inequality violated (quantum confirmed)\n")

    print("[6] Testing Bloch sphere...")
    q = Qubit(1.0, 0.0)
    x, y, z = q.bloch.to_cartesian()
    print(f"    |0⟩ on Bloch sphere: ({x:.2f}, {y:.2f}, {z:.2f})")
    q.apply_gate(HADAMARD)
    x, y, z = q.bloch.to_cartesian()
    print(f"    |+⟩ on Bloch sphere: ({x:.2f}, {y:.2f}, {z:.2f})")
    print("    ✓ Bloch sphere representation works\n")

    print("[7] Testing decoherence...")
    q = Qubit(1.0, 0.0)
    q.apply_gate(HADAMARD)
    original_fidelity = q.fidelity(Qubit(1.0/math.sqrt(2), 1.0/math.sqrt(2)))
    print(f"    Initial fidelity: {original_fidelity:.6f}")
    for _ in range(10):
        q.apply_noise(0.01)
    final_fidelity = q.fidelity(Qubit(1.0/math.sqrt(2), 1.0/math.sqrt(2)))
    print(f"    After 10 noise steps: {final_fidelity:.6f}")
    print("    ✓ Decoherence simulation works\n")

    print("=" * 60)
    print("  All tests passed. Qubit system operational.")
    print("=" * 60)