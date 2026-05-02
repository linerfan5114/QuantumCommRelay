#!/usr/bin/env python3
"""
QuantumCommRelay - 3D Network Visualization
Interactive 3D rendering of LEO satellite quantum network
Entanglement links, QKD routes, and security monitoring dashboard

Author: QuantumCommRelay Team
License: MIT
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from typing import List, Tuple, Dict, Optional
import math


class QuantumNetworkVisualizer:
    def __init__(self, earth_radius_km: float = 6371.0,
                 orbit_radius_km: float = 6871.0):
        self.earth_radius = earth_radius_km
        self.orbit_radius = orbit_radius_km
        self.fig = None

    def _create_earth_sphere(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        phi = np.linspace(0, 2 * np.pi, 50)
        theta = np.linspace(0, np.pi, 50)
        phi, theta = np.meshgrid(phi, theta)
        x = self.earth_radius * np.cos(phi) * np.sin(theta)
        y = self.earth_radius * np.sin(phi) * np.sin(theta)
        z = self.earth_radius * np.cos(theta)
        return x, y, z

    def create_network_scene(self,
                             satellites: List[Dict],
                             links: Optional[List[Dict]] = None,
                             qkd_routes: Optional[List[Dict]] = None,
                             attacks: Optional[List[Dict]] = None,
                             view_angle: str = "default") -> go.Figure:
        fig = go.Figure()

        x, y, z = self._create_earth_sphere()
        fig.add_trace(go.Surface(
            x=x, y=y, z=z,
            colorscale=[[0, '#0a3d6b'], [0.5, '#1a6eb5'], [1, '#2e8b57']],
            showscale=False,
            name='Earth',
            opacity=0.9,
            lighting=dict(ambient=0.3, diffuse=0.7, specular=0.1),
        ))

        if satellites:
            sat_x, sat_y, sat_z = [], [], []
            sat_colors, sat_sizes, sat_labels = [], [], []
            for sat in satellites:
                pos = sat.get("position", (0, 0, 0))
                sat_x.append(pos[0])
                sat_y.append(pos[1])
                sat_z.append(pos[2])
                is_eclipsed = sat.get("is_eclipsed", False)
                has_entanglement = sat.get("entangled_links", 0) > 0
                if has_entanglement:
                    sat_colors.append('#00ffff')
                    sat_sizes.append(6)
                elif is_eclipsed:
                    sat_colors.append('#666666')
                    sat_sizes.append(3)
                else:
                    sat_colors.append('#00ff88')
                    sat_sizes.append(4)
                sat_labels.append(
                    f"{sat.get('name', 'Unknown')}<br>"
                    f"Keys: {sat.get('keys_generated', 0):,} bits<br>"
                    f"QKD sessions: {sat.get('active_qkd_sessions', 0)}<br>"
                    f"Eclipsed: {is_eclipsed}<br>"
                    f"Entangled links: {sat.get('entangled_links', 0)}"
                )

            fig.add_trace(go.Scatter3d(
                x=sat_x, y=sat_y, z=sat_z,
                mode='markers',
                marker=dict(
                    size=sat_sizes,
                    color=sat_colors,
                    opacity=0.9,
                    symbol='circle',
                    line=dict(color='white', width=0.5),
                ),
                text=sat_labels,
                hoverinfo='text',
                name='Satellites',
                showlegend=True,
            ))

        if links:
            for link in links:
                src_pos = link.get("source_pos", (0, 0, 0))
                tgt_pos = link.get("target_pos", (0, 0, 0))
                fidelity = link.get("fidelity", 0.5)
                if fidelity > 0.9:
                    color = '#ff00ff'
                    width = 3
                elif fidelity > 0.7:
                    color = '#00ffff'
                    width = 2
                else:
                    color = '#ffff00'
                    width = 1

                fig.add_trace(go.Scatter3d(
                    x=[src_pos[0], tgt_pos[0]],
                    y=[src_pos[1], tgt_pos[1]],
                    z=[src_pos[2], tgt_pos[2]],
                    mode='lines',
                    line=dict(color=color, width=width, dash='solid'),
                    opacity=0.6,
                    hovertext=f"Fidelity: {fidelity:.4f}<br>"
                             f"Distance: {link.get('distance_km', 0):.0f} km",
                    showlegend=False,
                ))

        if qkd_routes:
            for route in qkd_routes:
                path = route.get("path_positions", [])
                if len(path) >= 2:
                    route_x = [p[0] for p in path]
                    route_y = [p[1] for p in path]
                    route_z = [p[2] for p in path]
                    fig.add_trace(go.Scatter3d(
                        x=route_x, y=route_y, z=route_z,
                        mode='lines+markers',
                        line=dict(color='#ff8800', width=4, dash='dash'),
                        marker=dict(size=5, color='#ff8800', symbol='diamond'),
                        hovertext=f"QKD Route: {route.get('hops', 0)} hops<br>"
                                 f"Distance: {route.get('distance_km', 0):.0f} km<br>"
                                 f"Keys: {route.get('keys_exchanged', 0)} bits",
                        name=f"QKD Route ({route.get('hops', 0)} hops)",
                        showlegend=True,
                    ))

        if attacks:
            attack_x, attack_y, attack_z = [], [], []
            attack_colors, attack_sizes = [], []
            for attack in attacks:
                pos = attack.get("position", (0, 0, 0))
                attack_x.append(pos[0])
                attack_y.append(pos[1])
                attack_z.append(pos[2])
                if attack.get("detected", False):
                    attack_colors.append('#ff0000')
                    attack_sizes.append(10)
                else:
                    attack_colors.append('#ff8800')
                    attack_sizes.append(7)

            if attack_x:
                fig.add_trace(go.Scatter3d(
                    x=attack_x, y=attack_y, z=attack_z,
                    mode='markers',
                    marker=dict(
                        size=attack_sizes,
                        color=attack_colors,
                        opacity=0.9,
                        symbol='x',
                        line=dict(color='white', width=1),
                    ),
                    name='Attacks',
                    showlegend=True,
                ))

        camera = dict()
        if view_angle == "top":
            camera = dict(eye=dict(x=0, y=0, z=self.orbit_radius * 2))
        elif view_angle == "side":
            camera = dict(eye=dict(x=self.orbit_radius * 2, y=0, z=0))
        elif view_angle == "front":
            camera = dict(eye=dict(x=0, y=self.orbit_radius * 2, z=0))
        else:
            camera = dict(eye=dict(x=self.orbit_radius * 1.2,
                                  y=self.orbit_radius * 0.8,
                                  z=self.orbit_radius * 1.2))

        fig.update_layout(
            title=dict(
                text="QuantumCommRelay - LEO Quantum Network",
                font=dict(size=22, color='#00ffff', family='monospace'),
                x=0.5,
            ),
            scene=dict(
                xaxis=dict(title='X (km)', showbackground=True,
                          backgroundcolor='#000011', gridcolor='#111133'),
                yaxis=dict(title='Y (km)', showbackground=True,
                          backgroundcolor='#000011', gridcolor='#111133'),
                zaxis=dict(title='Z (km)', showbackground=True,
                          backgroundcolor='#000011', gridcolor='#111133'),
                camera=camera,
                aspectmode='data',
            ),
            paper_bgcolor='#000000',
            plot_bgcolor='#000000',
            font=dict(color='#00ff88', family='monospace'),
            showlegend=True,
            legend=dict(
                x=0.01, y=0.99,
                bgcolor='rgba(0,0,20,0.9)',
                bordercolor='#00ffff',
            ),
        )

        self.fig = fig
        return fig

    def create_dashboard(self, simulation_data: Dict) -> go.Figure:
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                "QBER Over Time",
                "Key Rate (bps)",
                "Active Satellites",
                "Entangled Pairs",
                "Attack Detection Rate",
                "Network Security Status"
            ),
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "indicator"}, {"type": "indicator"}],
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.10,
        )

        time_axis = np.linspace(0, simulation_data.get("duration_s", 3600), 100)
        qber_data = simulation_data.get("qber_history", [0.02] * 100)
        if len(qber_data) < 100:
            qber_data = list(qber_data) + [qber_data[-1]] * (100 - len(qber_data))
        fig.add_trace(
            go.Scatter(x=time_axis, y=qber_data[:100], mode='lines',
                      line=dict(color='#ff4444', width=2),
                      name='QBER'),
            row=1, col=1,
        )
        fig.add_hline(y=0.11, line_dash="dash", line_color="#ff0000",
                     annotation_text="Detection Threshold", row=1, col=1)

        key_rate = simulation_data.get("key_rate_history", [5000] * 100)
        if len(key_rate) < 100:
            key_rate = list(key_rate) + [key_rate[-1]] * (100 - len(key_rate))
        fig.add_trace(
            go.Scatter(x=time_axis, y=key_rate[:100], mode='lines',
                      line=dict(color='#00ff88', width=2),
                      fill='tozeroy', fillcolor='rgba(0,255,136,0.1)',
                      name='Key Rate'),
            row=1, col=2,
        )

        active_sats = simulation_data.get("active_satellites", [100] * 100)
        if len(active_sats) < 100:
            active_sats = list(active_sats) + [active_sats[-1]] * (100 - len(active_sats))
        fig.add_trace(
            go.Scatter(x=time_axis, y=active_sats[:100], mode='lines',
                      line=dict(color='#4488ff', width=2),
                      name='Active Sats'),
            row=2, col=1,
        )

        entangled = simulation_data.get("entangled_pairs", [0] * 100)
        if len(entangled) < 100:
            entangled = list(entangled) + [entangled[-1]] * (100 - len(entangled))
        fig.add_trace(
            go.Scatter(x=time_axis, y=entangled[:100], mode='lines',
                      line=dict(color='#ff00ff', width=2),
                      name='Entangled Pairs'),
            row=2, col=2,
        )

        attack_rate = simulation_data.get("attack_detection_rate", 88.0)
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=attack_rate,
                title={'text': "Attack Detection Rate (%)"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "#00ff88"},
                       'steps': [
                           {'range': [0, 50], 'color': "#ff4444"},
                           {'range': [50, 85], 'color': "#ffaa00"},
                           {'range': [85, 100], 'color': "#00ff88"},
                       ],
                       'threshold': {'line': {'color': "red", 'width': 2},
                                    'thickness': 0.75, 'value': 90}},
            ),
            row=3, col=1,
        )

        security_score = 100 - simulation_data.get("average_qber", 0.02) * 500
        security_score = max(0, min(100, security_score))
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=security_score,
                title={'text': "Security Score (%)"},
                gauge={'axis': {'range': [0, 100]},
                       'bar': {'color': "#00ffff"},
                       'steps': [
                           {'range': [0, 30], 'color': "#ff0000"},
                           {'range': [30, 60], 'color': "#ff8800"},
                           {'range': [60, 85], 'color': "#ffff00"},
                           {'range': [85, 100], 'color': "#00ff00"},
                       ],
                       'threshold': {'line': {'color': "red", 'width': 2},
                                    'thickness': 0.75, 'value': 70}},
            ),
            row=3, col=2,
        )

        fig.update_layout(
            title=dict(
                text="QuantumCommRelay - Mission Dashboard",
                font=dict(size=22, color='#00ffff', family='monospace'),
                x=0.5,
            ),
            paper_bgcolor='#000011',
            plot_bgcolor='#000011',
            font=dict(color='#00ff88', family='monospace'),
            height=1000,
            showlegend=True,
            legend=dict(
                bgcolor='rgba(0,0,20,0.9)',
                bordercolor='#00ffff',
            ),
        )

        return fig

    def save_html(self, filepath: str = "quantum_network_3d.html"):
        if self.fig:
            self.fig.write_html(filepath)
            print(f"[Visualizer] 3D network saved to {filepath}")


def demo_visualization():
    print("=" * 60)
    print("  QuantumCommRelay - 3D Network Visualization")
    print("=" * 60)

    viz = QuantumNetworkVisualizer()

    sample_sats = []
    for i in range(60):
        angle = 2 * math.pi * i / 60
        x = 6871 * math.cos(angle)
        y = 6871 * math.sin(angle) * math.cos(math.radians(97.4))
        z = 6871 * math.sin(angle) * math.sin(math.radians(97.4)) + 500
        sample_sats.append({
            "name": f"QSAT-{i+1:03d}",
            "position": (x, y, z),
            "is_eclipsed": i % 8 == 0,
            "keys_generated": np.random.randint(1000, 100000),
            "active_qkd_sessions": np.random.randint(0, 5),
            "entangled_links": np.random.randint(0, 6),
        })

    sample_links = []
    for i in range(15):
        a = np.random.randint(0, 60)
        b = (a + np.random.randint(1, 10)) % 60
        sample_links.append({
            "source_pos": sample_sats[a]["position"],
            "target_pos": sample_sats[b]["position"],
            "fidelity": np.random.uniform(0.7, 0.99),
            "distance_km": np.random.uniform(500, 3000),
        })

    sample_routes = []
    for _ in range(3):
        path_len = np.random.randint(3, 8)
        path_pos = []
        start_idx = np.random.randint(0, 50)
        for i in range(path_len):
            idx = (start_idx + i * 3) % 60
            path_pos.append(sample_sats[idx]["position"])
        sample_routes.append({
            "path_positions": path_pos,
            "hops": path_len,
            "distance_km": np.random.uniform(1000, 5000),
            "keys_exchanged": np.random.randint(256, 1024),
        })

    sample_attacks = []
    for _ in range(4):
        idx = np.random.randint(0, 60)
        sample_attacks.append({
            "position": sample_sats[idx]["position"],
            "detected": np.random.random() > 0.3,
        })

    fig = viz.create_network_scene(
        satellites=sample_sats,
        links=sample_links,
        qkd_routes=sample_routes,
        attacks=sample_attacks,
        view_angle="default",
    )
    fig.show()
    viz.save_html("quantum_network_3d.html")

    sample_data = {
        "duration_s": 3600,
        "qber_history": [np.random.uniform(0.01, 0.15) for _ in range(100)],
        "key_rate_history": [np.random.uniform(1000, 8000) for _ in range(100)],
        "active_satellites": [np.random.randint(85, 101) for _ in range(100)],
        "entangled_pairs": [np.random.randint(10, 100) for _ in range(100)],
        "attack_detection_rate": 88.5,
        "average_qber": 0.023,
    }

    dashboard = viz.create_dashboard(sample_data)
    dashboard.show()
    dashboard.write_html("quantum_dashboard.html")

    print("\n[Visualizer] Files saved:")
    print("  - quantum_network_3d.html")
    print("  - quantum_dashboard.html")


if __name__ == "__main__":
    demo_visualization()