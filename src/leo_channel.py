#!/usr/bin/env python3
"""
QuantumCommRelay - LEO Quantum Channel Model
Atmospheric loss, Doppler shift, decoherence, and photon loss
For satellite-to-satellite and satellite-to-ground quantum links

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import IntEnum
import math
import time

from qubit import Qubit


class LinkType(IntEnum):
    SATELLITE_TO_SATELLITE = 0
    SATELLITE_TO_GROUND = 1
    GROUND_TO_SATELLITE = 2


@dataclass
class OrbitalState:
    semi_major_axis_km: float = 6871.0
    eccentricity: float = 0.001
    inclination_deg: float = 97.4
    raan_deg: float = 0.0
    arg_perigee_deg: float = 0.0
    mean_anomaly_deg: float = 0.0
    epoch: float = 0.0

    def propagate(self, delta_time_s: float) -> 'OrbitalState':
        mean_motion = math.sqrt(398600.4418 / self.semi_major_axis_km**3)
        new_anomaly = (self.mean_anomaly_deg +
                      math.degrees(mean_motion * delta_time_s)) % 360.0
        return OrbitalState(
            semi_major_axis_km=self.semi_major_axis_km,
            eccentricity=self.eccentricity,
            inclination_deg=self.inclination_deg,
            raan_deg=self.raan_deg,
            arg_perigee_deg=self.arg_perigee_deg,
            mean_anomaly_deg=new_anomaly,
            epoch=self.epoch + delta_time_s,
        )

    def to_eci_position(self) -> Tuple[float, float, float]:
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
        x = x_orb * (math.cos(raan) * math.cos(argp) - math.sin(raan) * math.sin(argp) * math.cos(inc))
        x -= y_orb * (math.cos(raan) * math.sin(argp) + math.sin(raan) * math.cos(argp) * math.cos(inc))
        y = x_orb * (math.sin(raan) * math.cos(argp) + math.cos(raan) * math.sin(argp) * math.cos(inc))
        y += y_orb * (math.cos(raan) * math.cos(argp) * math.cos(inc) - math.sin(raan) * math.sin(argp))
        z = x_orb * (math.sin(argp) * math.sin(inc)) + y_orb * (math.cos(argp) * math.sin(inc))
        return (x, y, z)


@dataclass
class AtmosphericProfile:
    altitude_grid_km: np.ndarray = field(default_factory=lambda: np.linspace(0, 100, 101))
    density_profile: np.ndarray = field(default_factory=lambda: np.zeros(101))
    temperature_profile: np.ndarray = field(default_factory=lambda: np.zeros(101))

    def __post_init__(self):
        self._build_standard_atmosphere()

    def _build_standard_atmosphere(self):
        for i, h in enumerate(self.altitude_grid_km):
            if h < 11.0:
                self.temperature_profile[i] = 288.15 - 6.5 * h
                self.density_profile[i] = 1.225 * (1.0 - h / 44.33) ** 4.256
            elif h < 25.0:
                self.temperature_profile[i] = 216.65
                self.density_profile[i] = 0.36391 * math.exp(-(h - 11.0) / 6.346)
            elif h < 50.0:
                self.temperature_profile[i] = 216.65 + 1.0 * (h - 25.0)
                self.density_profile[i] = 0.001 * math.exp(-(h - 25.0) / 7.0)
            else:
                self.temperature_profile[i] = 270.65
                self.density_profile[i] = 1.0e-10

    def get_density_at_altitude(self, altitude_km: float) -> float:
        if altitude_km < 0:
            return self.density_profile[0]
        if altitude_km >= 100:
            return 1.0e-15
        idx = int(altitude_km)
        frac = altitude_km - idx
        return float(self.density_profile[idx] * (1 - frac) +
                    self.density_profile[min(idx + 1, 100)] * frac)


class LEOQuantumChannel:
    def __init__(self, link_type: LinkType = LinkType.SATELLITE_TO_SATELLITE):
        self.link_type = link_type
        self.atmosphere = AtmosphericProfile()
        self.sat1_state = OrbitalState()
        self.sat2_state = OrbitalState(mean_anomaly_deg=15.0)
        self.ground_station = (6371.0, 0.0, 0.0)

        self.c = 299792.458
        self.boltzmann = 1.380649e-23
        self.planck = 6.62607015e-34
        self.photon_frequency_hz = 500e12
        self.photon_wavelength_nm = 600.0

        self.turbulence_strength_cn2 = 1.0e-15
        self.wind_speed_ms = 30.0

        self.background_sources = {
            "sun": {"flux_photons_per_s_per_m2": 1.0e14, "solid_angle_sr": 6.8e-5},
            "moon": {"flux_photons_per_s_per_m2": 1.0e10, "solid_angle_sr": 6.8e-5},
            "earth_albedo": {"flux_photons_per_s_per_m2": 1.0e12, "solid_angle_sr": 2.0 * math.pi},
            "star_background": {"flux_photons_per_s_per_m2": 1.0e8, "solid_angle_sr": 4.0 * math.pi},
        }

        self.telescope_diameter_m = 0.3
        self.telescope_efficiency = 0.6
        self.telescope_fov_rad = 1.0e-5
        self.detector_dark_count_hz = 100.0
        self.detector_efficiency = 0.85
        self.timing_resolution_ns = 1.0

        self.stats = {
            "total_photons_sent": 0,
            "total_photons_received": 0,
            "total_photons_lost": 0,
            "total_decoherence_events": 0,
            "doppler_shifts_applied": 0,
            "background_noise_photons": 0,
        }

    def set_satellite_positions(self, sat1: OrbitalState, sat2: OrbitalState):
        self.sat1_state = sat1
        self.sat2_state = sat2

    def calculate_distance(self) -> float:
        pos1 = np.array(self.sat1_state.to_eci_position())
        pos2 = np.array(self.sat2_state.to_eci_position())
        return float(np.linalg.norm(pos1 - pos2))

    def calculate_relative_velocity(self) -> float:
        pos1 = np.array(self.sat1_state.to_eci_position())
        pos2 = np.array(self.sat2_state.to_eci_position())
        delta = 0.01
        sat1_forward = self.sat1_state
        sat1_forward.mean_anomaly_deg += 0.01
        pos1_new = np.array(sat1_forward.to_eci_position())
        vel1 = (pos1_new - pos1) / delta
        sat2_forward = self.sat2_state
        sat2_forward.mean_anomaly_deg += 0.01
        pos2_new = np.array(sat2_forward.to_eci_position())
        vel2 = (pos2_new - pos2) / delta
        rel_vel = vel2 - vel1
        direction = pos2 - pos1
        direction_norm = np.linalg.norm(direction)
        if direction_norm < 1.0:
            return 0.0
        return float(np.dot(rel_vel, direction / direction_norm))

    def calculate_doppler_shift(self) -> float:
        rel_vel = self.calculate_relative_velocity()
        shift_hz = self.photon_frequency_hz * rel_vel / self.c
        self.stats["doppler_shifts_applied"] += 1
        return shift_hz

    def calculate_atmospheric_loss(self, elevation_angle_deg: float,
                                   altitude_km: float = 500.0) -> float:
        if self.link_type == LinkType.SATELLITE_TO_SATELLITE:
            return 0.0
        if elevation_angle_deg < 0:
            return 1.0
        slant_path = altitude_km / math.sin(math.radians(elevation_angle_deg + 0.1))
        optical_depth = 0.0
        num_steps = 100
        for i in range(num_steps):
            h = altitude_km * (1.0 - i / num_steps)
            density = self.atmosphere.get_density_at_altitude(h)
            optical_depth += density * (slant_path / num_steps)
        extinction_coeff = 0.00005
        transmittance = math.exp(-extinction_coeff * optical_depth)
        return 1.0 - transmittance

    def calculate_scintillation_loss(self, distance_km: float) -> float:
        k = 2.0 * math.pi / (self.photon_wavelength_nm * 1.0e-9)
        rytov_variance = 1.23 * self.turbulence_strength_cn2 * k**(7.0/6.0)
        rytov_variance *= (distance_km * 1000.0)**(11.0/6.0)
        if rytov_variance > 1.0:
            scintillation_index = 1.0 + 0.86 / rytov_variance**0.4
        else:
            scintillation_index = math.exp(rytov_variance)
        fade_probability = min(0.5, (scintillation_index - 1.0) / 5.0)
        return fade_probability

    def calculate_background_noise(self, distance_km: float,
                                   sun_angle_deg: float = 90.0) -> float:
        receiver_area = math.pi * (self.telescope_diameter_m / 2.0)**2
        total_background = 0.0
        for source, params in self.background_sources.items():
            if source == "sun" and sun_angle_deg < 5.0:
                total_background += params["flux_photons_per_s_per_m2"] * receiver_area
            elif source == "moon":
                total_background += params["flux_photons_per_s_per_m2"] * receiver_area * 0.1
            else:
                total_background += params["flux_photons_per_s_per_m2"] * receiver_area * 0.001
        background_per_pulse = total_background * self.timing_resolution_ns * 1.0e-9
        self.stats["background_noise_photons"] += int(background_per_pulse)
        return background_per_pulse

    def calculate_photon_loss_probability(self, distance_km: float,
                                         elevation_deg: float = 90.0,
                                         sun_angle_deg: float = 90.0) -> float:
        geometric_loss = 1.0 - (self.telescope_diameter_m**2 /
                               (distance_km * 1000.0)**2 / 1.0e-10)
        geometric_loss = min(1.0, max(0.0, geometric_loss))
        atmospheric_loss = self.calculate_atmospheric_loss(elevation_deg)
        scintillation_loss = self.calculate_scintillation_loss(distance_km)
        total_loss = 1.0 - (1.0 - geometric_loss) * (1.0 - atmospheric_loss) * \
                    (1.0 - scintillation_loss) * self.telescope_efficiency * \
                    self.detector_efficiency
        return total_loss

    def apply_decoherence(self, qubit: Qubit, distance_km: float,
                         altitude_km: float = 500.0) -> Qubit:
        radiation_dose = 0.5 + (altitude_km - 400.0) / 100.0 * 0.2
        radiation_dose = max(0.1, radiation_dose)
        decoherence_rate = (radiation_dose * distance_km / 1000.0 * 0.01 +
                          self.atmosphere.get_density_at_altitude(altitude_km) * 1000.0)
        decoherence_rate = min(0.5, max(0.0, decoherence_rate))
        qubit.apply_noise(decoherence_rate)
        self.stats["total_decoherence_events"] += 1
        return qubit

    def transmit_qubit(self, qubit: Qubit, distance_km: float,
                      elevation_deg: float = 90.0,
                      sun_angle_deg: float = 90.0,
                      altitude_km: float = 500.0) -> Optional[Qubit]:
        self.stats["total_photons_sent"] += 1
        loss_prob = self.calculate_photon_loss_probability(
            distance_km, elevation_deg, sun_angle_deg)
        if np.random.random() < loss_prob:
            self.stats["total_photons_lost"] += 1
            return None
        doppler_hz = self.calculate_doppler_shift()
        doppler_factor = doppler_hz / self.photon_frequency_hz
        received = qubit.clone()
        if abs(doppler_factor) > 0.01:
            received.apply_noise(abs(doppler_factor) * 0.01)
        received = self.apply_decoherence(received, distance_km, altitude_km)
        self.calculate_background_noise(distance_km, sun_angle_deg)
        self.stats["total_photons_received"] += 1
        return received

    def get_link_budget(self, distance_km: float) -> Dict:
        loss_db = 10.0 * math.log10(
            (self.photon_wavelength_nm * 1.0e-9) / (4.0 * math.pi * distance_km * 1000.0))
        geometric_loss_db = 20.0 * math.log10(
            self.telescope_diameter_m / (distance_km * 1000.0 * 1.0e-6))
        atmospheric_transmittance = 1.0 - self.calculate_atmospheric_loss(90.0)
        atmospheric_loss_db = (10.0 * math.log10(atmospheric_transmittance)
                              if atmospheric_transmittance > 0 else -100.0)
        receiver_gain_db = 10.0 * math.log10(
            (math.pi * self.telescope_diameter_m / 2.0)**2)
        noise_power = (self.boltzmann * 290.0 * 1.0e9 *
                      self.detector_dark_count_hz)
        noise_power_dbm = 10.0 * math.log10(noise_power * 1000.0)

        return {
            "distance_km": distance_km,
            "wavelength_nm": self.photon_wavelength_nm,
            "free_space_loss_db": loss_db,
            "geometric_loss_db": geometric_loss_db,
            "atmospheric_loss_db": atmospheric_loss_db,
            "receiver_gain_db": receiver_gain_db,
            "noise_power_dbm": noise_power_dbm,
            "telescope_diameter_m": self.telescope_diameter_m,
            "detector_efficiency": self.detector_efficiency,
        }

    def get_statistics(self) -> Dict:
        return {
            **self.stats,
            "transmission_efficiency": (self.stats["total_photons_received"] /
                                       max(1, self.stats["total_photons_sent"])),
            "photon_loss_rate": (self.stats["total_photons_lost"] /
                                max(1, self.stats["total_photons_sent"])),
        }


def demo_satellite_to_satellite():
    print("\n" + "─" * 60)
    print("  DEMO 1: Satellite-to-Satellite Quantum Link")
    print("─" * 60)
    channel = LEOQuantumChannel(LinkType.SATELLITE_TO_SATELLITE)
    distances = [100, 500, 1000, 2000, 3000]
    for d in distances:
        q = Qubit(1.0, 0.0)
        q.apply_gate(HADAMARD)
        received = channel.transmit_qubit(q, d, altitude_km=500)
        if received:
            fidelity = q.fidelity(received)
            print(f"  {d:5d} km: ✓ Received, Fidelity={fidelity:.4f}")
        else:
            print(f"  {d:5d} km: ✗ Photon lost")

    budget = channel.get_link_budget(1000)
    print(f"\n  Link Budget (1000 km):")
    print(f"    Free space loss: {budget['free_space_loss_db']:.1f} dB")
    print(f"    Geometric loss: {budget['geometric_loss_db']:.1f} dB")
    print(f"    Detector efficiency: {budget['detector_efficiency']*100:.0f}%")


def demo_doppler_effect():
    print("\n" + "─" * 60)
    print("  DEMO 2: Doppler Shift Effects")
    print("─" * 60)
    channel = LEOQuantumChannel()
    for offset in [0, 5, 10, 20, 45]:
        sat1 = OrbitalState(mean_anomaly_deg=0)
        sat2 = OrbitalState(mean_anomaly_deg=offset)
        channel.set_satellite_positions(sat1, sat2)
        dist = channel.calculate_distance()
        vel = channel.calculate_relative_velocity()
        doppler = channel.calculate_doppler_shift()
        print(f"  Δ{offset:3d}°: Dist={dist:.0f} km, RelVel={vel:.1f} km/s, "
              f"Doppler={doppler/1e6:.2f} MHz")


def demo_atmospheric_loss():
    print("\n" + "─" * 60)
    print("  DEMO 3: Atmospheric Loss vs Elevation (Sat-to-Ground)")
    print("─" * 60)
    channel = LEOQuantumChannel(LinkType.SATELLITE_TO_GROUND)
    for elev in [5, 10, 20, 45, 90]:
        loss = channel.calculate_atmospheric_loss(elevation_angle_deg=elev)
        transmittance = (1.0 - loss) * 100.0
        print(f"  Elevation {elev:3d}°: Loss={loss*100:.1f}%, "
              f"Transmittance={transmittance:.1f}%")


def demo_statistics():
    print("\n" + "─" * 60)
    print("  DEMO 4: Channel Statistics")
    print("─" * 60)
    channel = LEOQuantumChannel()
    for _ in range(1000):
        q = Qubit(1.0, 0.0)
        q.apply_gate(HADAMARD)
        channel.transmit_qubit(q, np.random.uniform(500, 2000))
    stats = channel.get_statistics()
    print(f"  Photons sent: {stats['total_photons_sent']}")
    print(f"  Photons received: {stats['total_photons_received']}")
    print(f"  Transmission efficiency: {stats['transmission_efficiency']*100:.1f}%")
    print(f"  Decoherence events: {stats['total_decoherence_events']}")
    print(f"  Doppler shifts: {stats['doppler_shifts_applied']}")


if __name__ == "__main__":
    print("=" * 60)
    print("  QuantumCommRelay - LEO Quantum Channel Model")
    print("  Atmospheric + Doppler + Decoherence + Noise")
    print("=" * 60)

    demo_satellite_to_satellite()
    demo_doppler_effect()
    demo_atmospheric_loss()
    demo_statistics()

    print("\n" + "=" * 60)
    print("  LEO channel model operational.")
    print("  Ready for quantum network integration.")
    print("=" * 60)