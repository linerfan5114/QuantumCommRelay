#!/usr/bin/env python3
"""
QuantumCommRelay - LEO Satellite Quantum Network
100-satellite constellation with quantum routing and handoff
Dynamic topology, QKD throughput, and fault tolerance
For global quantum-secured communication coverage

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from collections import defaultdict, deque
import math
import time
import heapq

from qubit import Qubit, Basis, HADAMARD
from bb84 import BB84Protocol, QuantumChannel as BB84Channel
from entanglement import EntanglementLink, BellState, EntanglementManager
from quantum_repeater import QuantumRepeater, RepeaterNetwork


@dataclass
class SatelliteNode:
    id: int
    name: str
    orbital_state: 'OrbitalState'
    position: Tuple[float, float, float] = (0.0, 0.0, 500.0)
    qkd_buffer: deque = field(default_factory=lambda: deque(maxlen=100))
    entangled_links: Dict[int, EntanglementLink] = field(default_factory=dict)
    active_qkd_sessions: int = 0
    keys_generated: int = 0
    total_qber: float = 0.0
    is_eclipsed: bool = False
    eclipse_timer: float = 0.0
    quantum_memory: deque = field(default_factory=lambda: deque(maxlen=50))
    last_health_check: float = 0.0
    is_active: bool = True


@dataclass
class QuantumLink:
    source_id: int
    target_id: int
    distance_km: float
    fidelity: float = 0.95
    qber: float = 0.0
    key_rate_bps: float = 0.0
    active: bool = True
    established_at: float = 0.0
    total_keys_exchanged: int = 0


@dataclass
class NetworkRoute:
    path: List[int]
    total_distance_km: float
    total_fidelity: float
    hop_count: int
    estimated_qber: float
    estimated_key_rate_bps: float


class OrbitalState:
    def __init__(self, semi_major_axis_km: float = 6871.0,
                 inclination_deg: float = 97.4,
                 raan_deg: float = 0.0,
                 mean_anomaly_deg: float = 0.0):
        self.semi_major_axis_km = semi_major_axis_km
        self.eccentricity = 0.001
        self.inclination_deg = inclination_deg
        self.raan_deg = raan_deg
        self.arg_perigee_deg = 0.0
        self.mean_anomaly_deg = mean_anomaly_deg

    def propagate(self, delta_time_s: float) -> 'OrbitalState':
        mean_motion = math.sqrt(398600.4418 / self.semi_major_axis_km**3)
        new_anomaly = (self.mean_anomaly_deg +
                      math.degrees(mean_motion * delta_time_s)) % 360.0
        return OrbitalState(
            semi_major_axis_km=self.semi_major_axis_km,
            inclination_deg=self.inclination_deg,
            raan_deg=self.raan_deg,
            mean_anomaly_deg=new_anomaly,
        )

    def to_position(self) -> Tuple[float, float, float]:
        a = self.semi_major_axis_km
        e = self.eccentricity
        M = math.radians(self.mean_anomaly_deg)
        E = M
        for _ in range(10):
            E = E - (E - e * math.sin(E) - M) / (1.0 - e * math.cos(E))
        nu = 2.0 * math.atan2(
            math.sqrt(1.0 + e) * math.sin(E / 2.0),
            math.sqrt(1.0 - e) * math.cos(E / 2.0)
        )
        r = a * (1.0 - e * math.cos(E))
        inc = math.radians(self.inclination_deg)
        raan = math.radians(self.raan_deg)
        argp = math.radians(self.arg_perigee_deg)
        x_orb = r * math.cos(nu)
        y_orb = r * math.sin(nu)
        x = x_orb * (math.cos(raan) * math.cos(argp) -
             math.sin(raan) * math.sin(argp) * math.cos(inc))
        x -= y_orb * (math.cos(raan) * math.sin(argp) +
             math.sin(raan) * math.cos(argp) * math.cos(inc))
        y = x_orb * (math.sin(raan) * math.cos(argp) +
             math.cos(raan) * math.sin(argp) * math.cos(inc))
        y += y_orb * (math.cos(raan) * math.cos(argp) * math.cos(inc) -
             math.sin(raan) * math.sin(argp))
        z = x_orb * math.sin(argp) * math.sin(inc)
        z += y_orb * math.cos(argp) * math.sin(inc)
        return (x, y, z)


class SatelliteQuantumNetwork:
    def __init__(self, num_satellites: int = 100,
                 num_planes: int = 10,
                 altitude_km: float = 500.0):
        self.num_satellites = num_satellites
        self.num_planes = num_planes
        self.altitude_km = altitude_km
        self.semi_major_axis = 6371.0 + altitude_km

        self.satellites: Dict[int, SatelliteNode] = {}
        self.quantum_links: Dict[Tuple[int, int], QuantumLink] = {}
        self.routes: List[NetworkRoute] = []

        self.network_stats = {
            "total_keys_generated": 0,
            "total_qkd_sessions": 0,
            "failed_handoffs": 0,
            "successful_handoffs": 0,
            "average_qber": 0.0,
            "average_key_rate_bps": 0.0,
            "active_links": 0,
            "eclipsed_satellites": 0,
        }

        self.ground_stations = [
            {"name": "New Mexico", "lat": 32.9, "lon": -106.9},
            {"name": "Canary Islands", "lat": 28.3, "lon": -16.5},
            {"name": "Singapore", "lat": 1.3, "lon": 103.8},
        ]

        self._init_constellation()

    def _init_constellation(self):
        sats_per_plane = self.num_satellites // self.num_planes
        sat_id = 0

        for plane in range(self.num_planes):
            raan = plane * 360.0 / self.num_planes
            for slot in range(sats_per_plane):
                mean_anomaly = slot * 360.0 / sats_per_plane
                sat_id += 1
                orbital = OrbitalState(
                    semi_major_axis_km=self.semi_major_axis,
                    raan_deg=raan,
                    mean_anomaly_deg=mean_anomaly,
                )
                pos = orbital.to_position()
                self.satellites[sat_id] = SatelliteNode(
                    id=sat_id,
                    name=f"QSAT-{sat_id:03d}",
                    orbital_state=orbital,
                    position=pos,
                )

    def update_positions(self, time_step_s: float = 10.0):
        for sat_id, sat in self.satellites.items():
            sat.orbital_state = sat.orbital_state.propagate(time_step_s)
            sat.position = sat.orbital_state.to_position()
            self._check_eclipse(sat_id)

    def _check_eclipse(self, sat_id: int):
        sat = self.satellites[sat_id]
        x, y, z = sat.position
        earth_radius = 6371.0
        distance_from_center = math.sqrt(x**2 + y**2 + z**2)
        if distance_from_center < earth_radius + 100.0:
            sat.is_eclipsed = True
            sat.eclipse_timer = np.random.uniform(300, 1800)
        elif sat.is_eclipsed and sat.eclipse_timer > 0:
            sat.eclipse_timer -= 10.0
        else:
            sat.is_eclipsed = False
            sat.eclipse_timer = 0.0

    def calculate_distance(self, sat1_id: int, sat2_id: int) -> float:
        if sat1_id not in self.satellites or sat2_id not in self.satellites:
            return float('inf')
        p1 = np.array(self.satellites[sat1_id].position)
        p2 = np.array(self.satellites[sat2_id].position)
        return float(np.linalg.norm(p1 - p2))

    def find_visible_satellites(self, sat_id: int,
                               max_distance_km: float = 5000.0) -> List[int]:
        visible = []
        for other_id in self.satellites:
            if other_id == sat_id:
                continue
            if self.satellites[other_id].is_eclipsed:
                continue
            dist = self.calculate_distance(sat_id, other_id)
            if dist < max_distance_km:
                visible.append(other_id)
        return visible

    def establish_quantum_link(self, source_id: int, target_id: int) -> Optional[QuantumLink]:
        if source_id == target_id:
            return None
        if self.satellites[source_id].is_eclipsed or self.satellites[target_id].is_eclipsed:
            return None

        distance = self.calculate_distance(source_id, target_id)
        fidelity = max(0.5, 0.98 - distance * 0.00005)
        qber = 0.01 + distance * 0.00002
        key_rate = max(1.0, 10000.0 / (1.0 + distance / 100.0))

        link = QuantumLink(
            source_id=source_id,
            target_id=target_id,
            distance_km=distance,
            fidelity=fidelity,
            qber=qber,
            key_rate_bps=key_rate,
            established_at=time.time(),
        )

        key = (min(source_id, target_id), max(source_id, target_id))
        self.quantum_links[key] = link
        return link

    def route_quantum_request(self, source_id: int,
                             target_id: int) -> Optional[NetworkRoute]:
        if source_id == target_id:
            return NetworkRoute([source_id], 0.0, 1.0, 0, 0.0, 10000.0)

        dist = {s: float('inf') for s in self.satellites}
        prev = {s: -1 for s in self.satellites}
        fid = {s: 0.0 for s in self.satellites}
        dist[source_id] = 0.0
        fid[source_id] = 1.0
        visited = set()
        pq = [(0.0, source_id)]

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == target_id:
                break
            for v in self.find_visible_satellites(u):
                if v in visited or self.satellites[v].is_eclipsed:
                    continue
                edge_dist = self.calculate_distance(u, v)
                if edge_dist > 5000.0:
                    continue
                new_dist = d + edge_dist
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    fid[v] = fid[u] * 0.98
                    heapq.heappush(pq, (new_dist, v))

        if dist[target_id] == float('inf'):
            return None

        path = []
        current = target_id
        while current != -1:
            path.append(current)
            current = prev[current]
        path.reverse()

        total_fidelity = 1.0
        for i in range(len(path) - 1):
            total_fidelity *= 0.98

        estimated_qber = 0.01 + dist[target_id] * 0.00002
        key_rate = max(1.0, 10000.0 / (1.0 + dist[target_id] / 100.0))

        route = NetworkRoute(
            path=path,
            total_distance_km=dist[target_id],
            total_fidelity=total_fidelity,
            hop_count=len(path) - 1,
            estimated_qber=estimated_qber,
            estimated_key_rate_bps=key_rate,
        )
        self.routes.append(route)
        return route

    def run_qkd_session(self, source_id: int, target_id: int,
                        key_length: int = 256) -> Dict:
        route = self.route_quantum_request(source_id, target_id)
        if route is None:
            return {"success": False, "reason": "No route found"}

        for i in range(len(route.path) - 1):
            u, v = route.path[i], route.path[i + 1]
            key = (min(u, v), max(u, v))
            if key not in self.quantum_links:
                self.establish_quantum_link(u, v)

        total_keys = 0
        for i in range(len(route.path) - 1):
            u, v = route.path[i], route.path[i + 1]
            key = (min(u, v), max(u, v))
            if key in self.quantum_links:
                self.quantum_links[key].total_keys_exchanged += key_length
                total_keys += key_length
                self.satellites[u].keys_generated += key_length
                self.satellites[v].keys_generated += key_length

        self.network_stats["total_keys_generated"] += total_keys
        self.network_stats["total_qkd_sessions"] += 1

        return {
            "success": True,
            "route": route,
            "keys_exchanged": total_keys,
            "hops": route.hop_count,
            "distance_km": route.total_distance_km,
        }

    def get_network_statistics(self) -> Dict:
        active_sats = sum(1 for s in self.satellites.values() if not s.is_eclipsed)
        eclipsed = self.num_satellites - active_sats

        qbers = [l.qber for l in self.quantum_links.values()]
        key_rates = [l.key_rate_bps for l in self.quantum_links.values()]

        return {
            **self.network_stats,
            "total_satellites": self.num_satellites,
            "active_satellites": active_sats,
            "eclipsed_satellites": eclipsed,
            "active_quantum_links": len(self.quantum_links),
            "avg_qber": np.mean(qbers) if qbers else 0.0,
            "avg_key_rate_bps": np.mean(key_rates) if key_rates else 0.0,
            "total_routes_computed": len(self.routes),
        }

    def print_network_status(self):
        stats = self.get_network_statistics()
        print("\n" + "=" * 60)
        print("  QUANTUM NETWORK STATUS")
        print("=" * 60)
        print(f"  Satellites: {stats['active_satellites']}/{stats['total_satellites']} active "
              f"({stats['eclipsed_satellites']} eclipsed)")
        print(f"  Active links: {stats['active_quantum_links']}")
        print(f"  Total keys generated: {stats['total_keys_generated']:,}")
        print(f"  Average QBER: {stats['avg_qber']*100:.2f}%")
        print(f"  Average key rate: {stats['avg_key_rate_bps']:.1f} bps")
        print(f"  QKD sessions: {stats['total_qkd_sessions']}")
        print("=" * 60)


def demo_constellation_init():
    print("\n" + "─" * 60)
    print("  DEMO 1: Constellation Initialization")
    print("─" * 60)
    network = SatelliteQuantumNetwork(num_satellites=100, num_planes=10)
    stats = network.get_network_statistics()
    print(f"  Total satellites: {stats['total_satellites']}")
    print(f"  Orbital planes: {network.num_planes}")
    print(f"  Altitude: {network.altitude_km} km")
    for i in range(1, 4):
        sat = network.satellites[i]
        print(f"  {sat.name}: pos=({sat.position[0]:.0f}, "
              f"{sat.position[1]:.0f}, {sat.position[2]:.0f}) km")


def demo_quantum_routing():
    print("\n" + "─" * 60)
    print("  DEMO 2: Quantum Routing Between Satellites")
    print("─" * 60)
    network = SatelliteQuantumNetwork(num_satellites=50, num_planes=5)
    pairs = [(1, 25), (1, 12), (5, 45), (10, 30), (1, 50)]
    for src, dst in pairs:
        route = network.route_quantum_request(src, dst)
        if route:
            print(f"  QSAT-{src:03d} → QSAT-{dst:03d}: "
                  f"{route.hop_count} hops, {route.total_distance_km:.0f} km, "
                  f"Fidelity={route.total_fidelity:.4f}")
        else:
            print(f"  QSAT-{src:03d} → QSAT-{dst:03d}: No route")


def demo_qkd_session():
    print("\n" + "─" * 60)
    print("  DEMO 3: Full QKD Session with Key Generation")
    print("─" * 60)
    network = SatelliteQuantumNetwork(num_satellites=30, num_planes=3)
    result = network.run_qkd_session(1, 15, key_length=256)
    if result["success"]:
        print(f"  Session: QSAT-001 → QSAT-015")
        print(f"  Route: {' → '.join(f'QSAT-{n:03d}' for n in result['route'].path)}")
        print(f"  Hops: {result['hops']}")
        print(f"  Distance: {result['distance_km']:.0f} km")
        print(f"  Keys exchanged: {result['keys_exchanged']} bits")
    network.print_network_status()


def demo_network_resilience():
    print("\n" + "─" * 60)
    print("  DEMO 4: Network Resilience (Eclipse Simulation)")
    print("─" * 60)
    network = SatelliteQuantumNetwork(num_satellites=50, num_planes=5)
    print("  Before eclipse:")
    stats = network.get_network_statistics()
    print(f"    Active: {stats['active_satellites']}")

    for sat_id in [5, 10, 15, 20, 25]:
        network.satellites[sat_id].is_eclipsed = True
    print("  After 5 satellites eclipsed:")
    stats = network.get_network_statistics()
    print(f"    Active: {stats['active_satellites']}")

    route = network.route_quantum_request(1, 30)
    if route:
        print(f"  Rerouted QSAT-001 → QSAT-030: {route.hop_count} hops "
              f"(avoiding eclipsed nodes)")


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - LEO Satellite Quantum Network")
    print("  100-Satellite Constellation with Quantum Routing")
    print("=" * 60)

    demo_constellation_init()
    demo_quantum_routing()
    demo_qkd_session()
    demo_network_resilience()

    print("\n" + "=" * 60)
    print("  Quantum satellite network operational.")
    print("  Global QKD coverage established.")
    print("=" * 60)