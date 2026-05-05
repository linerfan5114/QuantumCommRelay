
# QuantumCommRelay – LEO Satellite Quantum Key Distribution Network

**A quantum-secured communication relay for Low Earth Orbit satellite constellations using BB84 protocol, entanglement swapping, and quantum repeaters.**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Language](https://img.shields.io/badge/language-Python%203.10%2B-yellow)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-Research%20Ready-brightgreen)
![Simulation](https://img.shields.io/badge/satellites-100-orange)
![Security](https://img.shields.io/badge/security-Quantum%20QKD-purple)

---

## Overview

**QuantumCommRelay** is a complete simulation framework for quantum-secured communication in Low Earth Orbit satellite constellations. It implements the BB84 quantum key distribution protocol, entanglement-based quantum repeaters, and eavesdropper detection — all within a realistic LEO orbital environment with atmospheric loss, Doppler shift, decoherence, and satellite eclipses.

When satellites pass behind Earth, classical communication is blocked. QuantumCommRelay uses **entanglement swapping** and **quantum repeaters** to maintain secure connectivity across the entire constellation, even when direct line-of-sight is lost.

> *"Because in space, nobody can jam a photon."*

---

## Key Capabilities

| Subsystem | Implementation |
|-----------|----------------|
| **Qubit Simulator** | Full quantum state representation with Bloch sphere, Pauli/Hadamard/CNOT gates, measurement, and decoherence |
| **BB84 Protocol** | Complete Alice-Bob QKD with basis reconciliation, key sifting, privacy amplification, and QBER calculation |
| **Entanglement Manager** | Bell state generation, distribution over distance, entanglement swapping, and quantum teleportation |
| **Quantum Repeater** | Multi-hop repeater chains with purification engine and error correction |
| **LEO Channel Model** | Atmospheric loss, Doppler shift (relative velocity up to 14 km/s), scintillation, background noise |
| **Eavesdropper Detection** | Intercept-resend, beam-splitting, man-in-the-middle, photon-number-splitting attacks with QBER monitoring |
| **Satellite Network** | 100-satellite Walker constellation with quantum routing, handoff, and fault tolerance |
| **3D Visualization** | Interactive Plotly-based orbital view with entanglement links, QKD routes, and attack alerts |

---

## Project Structure

```
QuantumCommRelay/
├── src/
│   ├── qubit.py               # Quantum bit simulator (gates, measurement, Bloch sphere)
│   ├── bb84.py                # BB84 QKD protocol (Alice, Bob, Eve, key sifting)
│   ├── entanglement.py        # Bell pairs, distribution, swapping, teleportation
│   ├── quantum_repeater.py    # Repeater chains, purification, error correction
│   ├── leo_channel.py         # LEO physical channel (atmosphere, Doppler, noise)
│   ├── eavesdropper.py        # Attack simulation and security monitoring
│   ├── satellite_network.py   # 100-satellite constellation with quantum routing
│   └── main.py                # Full mission simulation orchestrator
├── sim/
│   └── quantum_viz.py         # 3D network visualization and dashboard
├── README.md
└── LICENSE
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- NumPy (`pip install numpy`)
- Plotly (`pip install plotly`)

### Installation

```bash
git clone https://github.com/linerfan5114/QuantumCommRelay.git
cd QuantumCommRelay
pip install numpy plotly
```

### Run Quick Demo (10 minutes simulated)

```bash
python src/main.py
```

### Run Full Mission (1 hour simulated)

```bash
python src/main.py full
```

### Launch 3D Visualization

```bash
python sim/quantum_viz.py
```

---

## How It Works

### BB84 Quantum Key Distribution

```
Alice                           Eve (Eavesdropper)              Bob
  |                                    |                          |
  |-- Qubits (X/Z bases) ---->---[intercepts?]--->---[measures?]--|
  |                                    |                          |
  |<-------- Basis comparison (classical channel) ---------------->|
  |                                    |                          |
  |<-------- QBER calculation ----------------------------------->|
  |                                    |                          |
  |-------- Privacy amplification ---->|------->|--------->|------|
```

1. **Alice** generates random bits and encodes them in randomly chosen X or Z bases
2. **Bob** measures each qubit in a randomly chosen basis
3. Alice and Bob publicly compare their bases and discard mismatches (key sifting)
4. They compare a subset of their keys to calculate the **Quantum Bit Error Rate (QBER)**
5. If QBER > 11%, an eavesdropper is detected and the key is discarded
6. **Privacy amplification** extracts a shorter but provably secure key

### Entanglement Swapping

```
SAT-A -----[EPR]-----> SAT-R1 -----[EPR]-----> SAT-B
                           |
                     Bell measurement
                           |
                           v
SAT-A ------------[new EPR]-------------> SAT-B
```

Two separate entangled pairs (A-R1 and R1-B) are measured at the repeater node R1, creating a new entangled pair between A and B without either ever meeting.

---

## Attack Detection

| Attack Type | QBER Induced | Detectable? | Countermeasure |
|-------------|-------------|-------------|----------------|
| Intercept-Resend | 25% | Yes (QBER > 11%) | Privacy amplification |
| Beam Splitting | 5-15% | Partial | Decoy states + entanglement verification |
| Man-in-the-Middle | 30-50% | Yes | Authentication + basis reconciliation |
| Photon Number Splitting | 3-8% | Hard | Single-photon sources + decoy states |
| Cloning Attempt | 50%+ | Yes (impossible per no-cloning theorem) | None needed |

---

## Simulation Fidelity

| Parameter | Model |
|-----------|-------|
| **Orbit** | Walker Delta constellation, 500 km altitude, 97.4° inclination |
| **Atmosphere** | Standard atmosphere model with density/temperature profiles |
| **Doppler** | Relative velocity calculation from orbital mechanics |
| **Decoherence** | Radiation dose at altitude + atmospheric scattering |
| **Photon Loss** | Geometric spreading + atmospheric extinction + detector efficiency |
| **Background** | Sun, Moon, Earth albedo, star background with solid angle |
| **Eclipse** | Earth shadow model with realistic durations |

---

## Sample Output

```
╔══════════════════════════════════════════════════════════════╗
║              QUANTUMCOMMRELAY - MISSION COMPLETE              ║
╠══════════════════════════════════════════════════════════════╣
║ Simulation time: 1.0 hours (3600 seconds)
║ Satellites: 100
║ Orbital altitude: 500 km | Inclination: 97.4°
╠══════════════════════════════════════════════════════════════╣
║ QKD Sessions: 180
║ Successful: 165 (91.7%)
║ Total keys generated: 42,240 bits
║ Average QBER: 2.30%
╠══════════════════════════════════════════════════════════════╣
║ Entangled pairs created: 1080
║ Entangled pairs lost: 42
║ Routes found: 165
║ Routes failed: 15
╠══════════════════════════════════════════════════════════════╣
║ Attacks detected: 12
║ Attacks blocked: 12
║ Security status: ✓ SECURE
╠══════════════════════════════════════════════════════════════╣
║ Protocol: BB84 + E91 | Topology: LEO Walker Constellation  ║
║ Status: OPERATIONAL - Quantum-secured communication active ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Applications

- **Military Satellite Communications**: Unconditional security guaranteed by laws of physics
- **Financial Networks**: Quantum-secured transactions between ground stations via satellite relay
- **Deep Space Communication**: Entanglement-based links for Mars-Earth secure channels
- **Quantum Internet Backbone**: LEO constellation as the physical layer of the future quantum internet
- **Disaster Response**: Secure communication when terrestrial infrastructure is compromised

---

## Scientific References

- Bennett, C.H. & Brassard, G. (1984). *Quantum Cryptography: Public Key Distribution and Coin Tossing*. IEEE
- Ekert, A.K. (1991). *Quantum Cryptography Based on Bell's Theorem*. Physical Review Letters
- Briegel, H.J. et al. (1998). *Quantum Repeaters: The Role of Imperfect Local Operations*. Physical Review Letters
- Yin, J. et al. (2017). *Satellite-based entanglement distribution over 1200 km*. Science
- Liao, S.K. et al. (2017). *Satellite-to-ground quantum key distribution*. Nature
- Ren, J.G. et al. (2017). *Ground-to-satellite quantum teleportation*. Nature

---

## Why This Matters

Classical encryption (RSA, ECC) will be broken by sufficiently powerful quantum computers. **Quantum Key Distribution** is the only provably secure method that detects eavesdropping through fundamental physics — not computational complexity assumptions.

By deploying QKD on LEO satellite constellations, we can achieve **global quantum-secured communication** decades before a fiber-based quantum internet reaches the same coverage.

---
