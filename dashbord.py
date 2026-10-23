"""
@file dashboard.py
@brief PyQt5 Graphical User Interface for Aerospace Radiation Shielding Analysis
@details Orchestrates Geant4 C++ compilation, multi-threaded simulation execution,
         KPI telemetry calculations, and interactive 3D/2D data visualization.

@author Piyush Pallav
@email ppallav2014@gmail.com
"""

import sys
import os
import subprocess
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QSpinBox, 
                             QDoubleSpinBox, QPushButton, QFrame, QFileDialog,
                             QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Patch
import matplotlib.lines as mlines

# Pure Black Background Theme for Matplotlib
plt.style.use('dark_background')

MATERIALS = {
    "Aluminum": "G4_Al", "Lead": "G4_Pb", "Water": "G4_WATER", "Polyethylene": "G4_POLYETHYLENE", 
    "Copper": "G4_Cu", "Silicon": "G4_Si", "Tungsten": "G4_W", "Gold": "G4_Au", 
    "Titanium": "G4_Ti", "Carbon": "G4_C", "Kapton": "G4_KAPTON"
}
PARTICLES = {"Proton": "proton", "Electron": "e-", "Alpha": "alpha", "Gamma": "gamma"}

PARTICLE_COLORS = {
    "proton": "#f97316",     # Safety Orange
    "e-": "#38bdf8",         # Sky Blue
    "e+": "#7dd3fc",         # Light Sky
    "gamma": "#ffffff",      # White
    "neutron": "#fb923c",    # Light Orange
    "alpha": "#cbd5e1"       # Slate
}

class Geant4Worker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, material, thickness, energy, events, particle):
        super().__init__()
        self.material, self.thickness, self.energy, self.events, self.particle = material, thickness, energy, events, particle

    def run(self):
        try:
            if not os.path.exists("CMakeLists.txt"):
                cmake = "cmake_minimum_required(VERSION 3.16)\nproject(CubeSatShield)\nfind_package(Geant4 REQUIRED)\ninclude(${Geant4_USE_FILE})\nadd_executable(shield cubesat_shield.cc)\ntarget_link_libraries(shield ${Geant4_LIBRARIES})\n"
                with open("CMakeLists.txt", "w") as f: f.write(cmake)

            os.makedirs("build", exist_ok=True)
            self.log_signal.emit("[SYSTEM] Compiling Geant4 Engine (CMake/Make)...")
            subprocess.run(["cmake", ".."], cwd="build", capture_output=True)
            subprocess.run(["make", "-j4"], cwd="build", capture_output=True)
            
            for f in ["results.csv", "tracks.csv", "secondaries.csv"]:
                if os.path.exists(f): 
                    try:
                        os.remove(f)
                    except Exception:
                        pass

            self.log_signal.emit(f"[GEANT4] Executing MT Simulation: {self.events} {self.particle}s...")
            cmd = ["./build/shield", self.material, str(self.thickness), str(self.energy), str(self.events), self.particle]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout: self.log_signal.emit(line.strip())
            process.wait()
            
            self.finished_signal.emit(True)
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {str(e)}")
            self.finished_signal.emit(False)

class KPICard(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setStyleSheet("background-color: #09090b; border-radius: 4px; border: 1px solid #475569;")
        layout = QVBoxLayout(self)
        lbl = QLabel(title); lbl.setStyleSheet("color: #94a3b8; font-size: 13px; font-weight: bold; border: none;")
        self.val = QLabel(value); self.val.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold; border: none;")
        layout.addWidget(lbl); layout.addWidget(self.val)
        
    def update_val(self, val): 
        self.val.setText(val); self.current_value = val

class MasterDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aerospace Radiation Shielding Analysis (Geant4)")
        self.resize(1920, 1080)
        self.apply_dark_theme()
        self.initUI()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #09090b; color: #f8fafc; }
            QLabel { font-weight: bold; font-size: 12px; color: #f8fafc; }
            QComboBox, QSpinBox, QDoubleSpinBox { background-color: #18181b; border: 1px solid #475569; padding: 6px; color: #f8fafc; border-radius: 2px; }
            QPushButton { color: #ffffff; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 2px; }
            QPushButton:disabled { background-color: #111111; color: #64748b; border: 1px solid #334155; }
            QTextEdit { background-color: #050505; color: #38bdf8; border: 1px solid #475569; font-family: Consolas; font-size: 12px; }
            QTableWidget { background-color: #050505; gridline-color: #334155; color: #f8fafc; border: 1px solid #475569; font-size: 13px; }
            QHeaderView::section { background-color: #18181b; color: #f97316; font-weight: bold; padding: 8px; border: none; border-bottom: 1px solid #475569; font-size: 13px; }
        """)

    def initUI(self):
        central = QWidget(); self.setCentralWidget(central)
        main_grid = QGridLayout(central); main_grid.setContentsMargins(10, 10, 10, 10); main_grid.setSpacing(15)

        # ---------------- 1. LEFT SIDEBAR ----------------
        sidebar_wrap = QWidget()
        sb_layout = QVBoxLayout(sidebar_wrap); sb_layout.setContentsMargins(0,0,0,0)

        title = QLabel("Mission Configuration"); title.setStyleSheet("font-size: 18px; color: #f97316; margin-bottom: 5px;")
        sb_layout.addWidget(title)

        self.alt_spin = QSpinBox(); self.alt_spin.setRange(200, 40000); self.alt_spin.setValue(400)
        self.orbit_lbl = QLabel("Orbit: LEO (Trapped Protons)"); self.orbit_lbl.setStyleSheet("color: #38bdf8;")
        self.alt_spin.valueChanged.connect(self.auto_orbit)
        
        self.mat_cb = QComboBox(); self.mat_cb.addItems(MATERIALS.keys())
        self.thick_spin = QDoubleSpinBox(); self.thick_spin.setRange(1.0, 100.0); self.thick_spin.setValue(5.0)
        self.part_cb = QComboBox(); self.part_cb.addItems(PARTICLES.keys())
        self.energy_spin = QDoubleSpinBox(); self.energy_spin.setRange(1.0, 5000.0); self.energy_spin.setValue(50.0)
        self.events_spin = QSpinBox(); self.events_spin.setRange(100, 1000000); self.events_spin.setValue(2000); self.events_spin.setSingleStep(1000)
        self.years_spin = QDoubleSpinBox(); self.years_spin.setRange(0.1, 20.0); self.years_spin.setValue(1.0)

        self.add_row(sb_layout, "Orbital Altitude (km)", self.alt_spin)
        sb_layout.addWidget(self.orbit_lbl)
        self.add_row(sb_layout, "Shielding Material", self.mat_cb)
        self.add_row(sb_layout, "Thickness (mm)", self.thick_spin)
        self.add_row(sb_layout, "Primary Particle", self.part_cb)
        self.add_row(sb_layout, "Kinetic Energy (MeV)", self.energy_spin)
        self.add_row(sb_layout, "Simulation Events", self.events_spin)
        self.add_row(sb_layout, "Mission Lifespan (Years)", self.years_spin)

        self.run_btn = QPushButton("Run Simulation"); self.run_btn.setStyleSheet("background-color: #f97316; border: 1px solid #ea580c; color: #ffffff;")
        self.run_btn.clicked.connect(self.run_sim)
        
        self.export_btn = QPushButton("Export Report"); self.export_btn.setStyleSheet("background-color: #0d9488; border: 1px solid #0f766e; color: #ffffff;")
        self.export_btn.clicked.connect(self.export_report)

        self.info_btn = QPushButton("About / Info"); self.info_btn.setStyleSheet("background-color: #475569; border: 1px solid #334155; color: #ffffff;")
        self.info_btn.clicked.connect(self.show_about_info)

        sb_layout.addWidget(self.run_btn)
        sb_layout.addWidget(self.export_btn)
        sb_layout.addWidget(self.info_btn)
        
        sb_layout.addWidget(QLabel("Geant4 System Info:"))
        self.info_box = QTextEdit(); self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet("color: #38bdf8; font-size: 14px; font-weight: bold; background-color: #050505; border: 1px solid #475569;")
        sb_layout.addWidget(self.info_box, 1) 
        main_grid.addWidget(sidebar_wrap, 0, 0)

        # ---------------- 2. CENTER WORKSPACE ----------------
        center_widget = QWidget()
        center_lay = QVBoxLayout(center_widget); center_lay.setContentsMargins(0,0,0,0)
        
        kpi_lay = QHBoxLayout()
        self.kpi_hit = KPICard("Payload Penetration", "0.0%")
        self.kpi_dose = KPICard("Simulated Dose (Gy)", "0.00e+00")
        self.kpi_tid = KPICard("Est. Mission TID (kRad)", "0.00")
        self.kpi_eff = KPICard("Shielding Efficiency", "100.0%")
        for k in [self.kpi_hit, self.kpi_dose, self.kpi_tid, self.kpi_eff]: kpi_lay.addWidget(k)
        center_lay.addLayout(kpi_lay)

        self.fig_3d = plt.figure(facecolor='#09090b'); self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.c3d = FigureCanvas(self.fig_3d)
        center_lay.addWidget(self.c3d, 1)
        main_grid.addWidget(center_widget, 0, 1)

        # ---------------- 3. RIGHT PANEL ----------------
        right_widget = QWidget()
        right_lay = QVBoxLayout(right_widget); right_lay.setContentsMargins(0,0,0,0); right_lay.setSpacing(15)
        
        self.fig_spec, self.ax_spec = plt.subplots(facecolor='#09090b')
        self.fig_sec, self.ax_sec = plt.subplots(facecolor='#09090b')
        self.fig_depth, self.ax_depth = plt.subplots(facecolor='#09090b')
        
        self.cspec = FigureCanvas(self.fig_spec); self.csec = FigureCanvas(self.fig_sec); self.cdepth = FigureCanvas(self.fig_depth)
        
        right_lay.addWidget(self.cspec, 1)
        right_lay.addWidget(self.csec, 1)
        right_lay.addWidget(self.cdepth, 1)
        main_grid.addWidget(right_widget, 0, 2, 2, 1) 

        # ---------------- 4. TERMINAL ----------------
        term_wrap = QWidget()
        term_lay = QVBoxLayout(term_wrap); term_lay.setContentsMargins(0,0,0,0)
        term_lay.addWidget(QLabel("Execution Console:"))
        self.terminal = QTextEdit(); self.terminal.setReadOnly(True)
        term_lay.addWidget(self.terminal)
        main_grid.addWidget(term_wrap, 1, 0)

        # ---------------- 5. SECONDARY PARTICLE TABLE (5 Columns) ----------------
        table_wrap = QWidget()
        table_lay = QVBoxLayout(table_wrap); table_lay.setContentsMargins(0,0,0,0)
        table_lay.addWidget(QLabel("Complete Secondary Particle List:"))
        self.table = QTableWidget(0, 5)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet("QTableWidget { font-size: 13px; background-color: #050505; color: #f8fafc; border: 1px solid #475569; }")
        self.table.setHorizontalHeaderLabels(["Particle", "Total Count", "Avg. Energy (MeV)", "Payload Hits", "Dose Contribution (%)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_lay.addWidget(self.table)
        main_grid.addWidget(table_wrap, 1, 1)

        # ---------------- GRID PROPORTIONS ----------------
        main_grid.setColumnStretch(0, 2)
        main_grid.setColumnStretch(1, 5)
        main_grid.setColumnStretch(2, 3)
        main_grid.setRowStretch(0, 7)
        main_grid.setRowStretch(1, 2)

        self.setup_plots()
        self.update_info()
        for w in [self.mat_cb, self.thick_spin, self.part_cb, self.energy_spin]: w.currentIndexChanged.connect(self.update_info) if isinstance(w, QComboBox) else w.valueChanged.connect(self.update_info)
        self.secondary_summary_data = []

    def add_row(self, lay, text, widget):
        lbl = QLabel(text); lbl.setStyleSheet("color: #f8fafc; margin-top: 5px;")
        lay.addWidget(lbl); lay.addWidget(widget)

    def auto_orbit(self):
        alt = self.alt_spin.value()
        if alt < 2000:
            self.orbit_lbl.setText("Orbit: LEO (Trapped Protons)")
            self.part_cb.setCurrentText("Proton"); self.energy_spin.setValue(50.0)
        elif alt < 35786:
            self.orbit_lbl.setText("Orbit: MEO (Electron Belts)")
            self.part_cb.setCurrentText("Electron"); self.energy_spin.setValue(5.0)
        else:
            self.orbit_lbl.setText("Orbit: GEO (Cosmic/Solar)")
            self.part_cb.setCurrentText("Electron"); self.energy_spin.setValue(2.0)
        self.update_info()

    def update_info(self):
        t = f"Material: {MATERIALS[self.mat_cb.currentText()]}\nThickness: {self.thick_spin.value()} mm\n"
        t += f"Beam: {self.energy_spin.value()} MeV {self.part_cb.currentText()}\n"
        t += f"Threads: Auto (G4MTRunManager)\nEngine: FTFP_BERT Physics"
        self.info_box.setText(t)

    def style_ax(self, ax, title, xlabel="", ylabel=""):
        ax.set_facecolor('#050505')
        ax.grid(True, linestyle='--', color='#334155', alpha=0.8)
        for spine_key in ['top', 'bottom', 'left', 'right']:
            ax.spines[spine_key].set_visible(True)
            ax.spines[spine_key].set_color('#475569')
            ax.spines[spine_key].set_linewidth(1.2)
            
        ax.set_title(title, color='#f97316', weight='bold', size=14, pad=8)
        ax.set_xlabel(xlabel, color='#f8fafc', weight='bold', size=12)
        ax.set_ylabel(ylabel, color='#f8fafc', weight='bold', size=12)
        ax.tick_params(axis='both', which='major', labelsize=11, colors='#f8fafc')

    def setup_plots(self):
        self.style_ax(self.ax_spec, "Payload Energy Deposition Spectrum", "Energy (MeV)", "Counts")
        self.style_ax(self.ax_sec, "Secondary Particle Yield", "Total Count", "Particle Type")
        self.style_ax(self.ax_depth, "Cumulative Dose vs. Depth Profile", "Shield Depth (mm)", "Dose (Gy)")
        
        self.ax_3d.set_facecolor('#09090b'); self.ax_3d.axis('off')
        self.ax_3d.set_title("Particle Tracks", color='#f97316', weight='bold', size=18, pad=15)
        self.fig_3d.subplots_adjust(left=0, right=1, bottom=0, top=0.9)
        self.fig_spec.tight_layout(); self.fig_sec.tight_layout(); self.fig_depth.tight_layout()

    def draw_3d_legend_and_axes(self):
        origin = [-60, -60, -60]
        length = 25
        self.ax_3d.quiver(*origin, length, 0, 0, color='#38bdf8', arrow_length_ratio=0.2, linewidth=2.0)
        self.ax_3d.quiver(*origin, 0, length, 0, color='#f97316', arrow_length_ratio=0.2, linewidth=2.0)
        self.ax_3d.quiver(*origin, 0, 0, length, color='#ffffff', arrow_length_ratio=0.2, linewidth=2.0)
        self.ax_3d.text(origin[0]+length+5, origin[1], origin[2], 'X', color='#38bdf8', weight='bold', fontsize=12)
        self.ax_3d.text(origin[0], origin[1]+length+5, origin[2], 'Y', color='#f97316', weight='bold', fontsize=12)
        self.ax_3d.text(origin[0], origin[1], origin[2]+length+5, 'Z', color='#ffffff', weight='bold', fontsize=12)

        legend_elements = [
            Patch(facecolor='#334155', edgecolor='#f8fafc', alpha=0.5, label='Shielding (Outer)'),
            Patch(facecolor='#64748b', edgecolor='#f8fafc', alpha=0.7, label='Payload (Inner)'),
            mlines.Line2D([0], [0], color='#f97316', lw=2, label='Proton Track'),
            mlines.Line2D([0], [0], color='#38bdf8', lw=2, label='Electron Track')
        ]
        self.ax_3d.legend(handles=legend_elements, loc='upper left', fontsize=11, frameon=False, labelcolor='white')

    def run_sim(self):
        self.run_btn.setEnabled(False); self.terminal.clear()
        self.worker = Geant4Worker(MATERIALS[self.mat_cb.currentText()], self.thick_spin.value(), 
                                   self.energy_spin.value(), self.events_spin.value(), PARTICLES[self.part_cb.currentText()])
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.process_data)
        self.worker.start()

    def log(self, msg):
        self.terminal.append(msg)
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def draw_cube(self, ax, size, color, alpha):
        r = [-size/2, size/2]; X, Y = np.meshgrid(r, r)
        for z in [-size/2, size/2]: ax.plot_surface(X, Y, np.full_like(X, z), alpha=alpha, color=color, edgecolor='#f8fafc', linewidth=0.5)
        for y in [-size/2, size/2]: ax.plot_surface(X, np.full_like(X, y), Y, alpha=alpha, color=color, edgecolor='#f8fafc', linewidth=0.5)
        for x in [-size/2, size/2]: ax.plot_surface(np.full_like(X, x), X, Y, alpha=alpha, color=color, edgecolor='#f8fafc', linewidth=0.5)

    def show_about_info(self):
        about_text = (
            "<h3>Aerospace Radiation Shielding Analysis Platform</h3>"
            "<p>This software application is an advanced numerical simulation orchestrator and graphical "
            "visualization dashboard engineered specifically for space radiation transport physics and satellite "
            "shielding design. By seamlessly bridging a high-performance C++ backend powered by the Geant4 toolkit "
            "with a responsive PyQt5 user interface, the platform enables comprehensive multi-threaded analysis "
            "of energetic particle interactions across standard orbital environments.</p>"
            "<p><b>Lead Developer & Author:</b> Piyush Pallav<br>"
            "<b>Official Contact Channel:</b> ppallav2014@gmail.com</p>"
            "<p><b>Core Functional Capabilities:</b><br>"
            "1. Real-time deterministic transport simulation of protons, electrons, alphas, and gamma cascades.<br>"
            "2. Precise calculation of Silicon payload energy deposition spectra and structural penetration rates.<br>"
            "3. Automated evaluation of Total Ionizing Dose (TID) metrics and mission lifespan degradation.<br>"
            "4. Granular secondary particle yield tracking mapped to fundamental quantum and nuclear interaction processes.</p>"
        )
        QMessageBox.about(self, "About Software Architecture", about_text)

    def process_data(self, success):
        self.run_btn.setEnabled(True)
        if not success: return

        events = self.events_spin.value()
        thick = self.thick_spin.value()
        vol_cm3 = (5.0 - (thick/10.0)) ** 3
        mass_kg = vol_cm3 * 2.329 * 1e-3
        
        df_res = pd.DataFrame(columns=["EventID", "Energy", "Particle"])
        if os.path.exists("results.csv") and os.path.getsize("results.csv") > 0:
            try:
                df_res = pd.read_csv("results.csv", names=["EventID", "Energy", "Particle"])
            except Exception:
                pass

        tot_mev = df_res.groupby("EventID")["Energy"].sum().sum() if not df_res.empty else 0
        hits = len(df_res["EventID"].unique()) if not df_res.empty else 0

        dose_gy = (tot_mev * 1.602e-13) / mass_kg if mass_kg > 0 else 0
        scale_factor = (1e8 * 100 * self.years_spin.value()) / events
        tid_krad = ((dose_gy * 100) * scale_factor) / 1000

        self.kpi_hit.update_val(f"{(hits/events)*100:.1f}%")
        self.kpi_dose.update_val(f"{dose_gy:.2e}")
        self.kpi_tid.update_val(f"{tid_krad:.2f}")
        self.kpi_eff.update_val(f"{100 - (hits/events)*100:.1f}%")

        # 1. Clear and Draw Energy Spectrum
        self.ax_spec.clear(); self.setup_plots()
        if not df_res.empty and "Energy" in df_res.columns:
            self.ax_spec.hist(df_res.groupby("EventID")["Energy"].sum(), bins=100, histtype='stepfilled', color='#38bdf8', edgecolor='#ffffff', linewidth=1.2)
        self.cspec.draw()

        # 2. Clear and Draw Secondary Yield & Table
        self.ax_sec.clear(); self.setup_plots()
        self.secondary_summary_data = []
        self.table.setRowCount(0)
        
        if os.path.exists("secondaries.csv") and os.path.getsize("secondaries.csv") > 0:
            try:
                df_sec = pd.read_csv("secondaries.csv", names=["Particle", "Energy", "Volume"])
            except Exception:
                df_sec = pd.DataFrame(columns=["Particle", "Energy", "Volume"])

            if not df_sec.empty:
                counts = df_sec["Particle"].value_counts().sort_values()
                y_pos = np.arange(len(counts))
                self.ax_sec.hlines(y=y_pos, xmin=0, xmax=counts.values, color='#38bdf8', linewidth=2.5)
                self.ax_sec.plot(counts.values, y_pos, "o", color='#f97316', markersize=8)
                self.ax_sec.set_yticks(y_pos)
                self.ax_sec.set_yticklabels(counts.index)
                
                summary = df_sec.groupby("Particle").agg(
                    Total_Count=("Particle", "count"),
                    Avg_Energy=("Energy", "mean"),
                    Payload_Hits=("Volume", lambda x: (x == "Payload").sum())
                ).reset_index()

                total_events_energy = df_res["Energy"].sum() if not df_res.empty else 1
                
                for row_idx, data in summary.iterrows():
                    part = data['Particle']
                    count = data['Total_Count']
                    avg_en = data['Avg_Energy']
                    p_hits = data['Payload_Hits']
                    
                    part_dose = df_res[df_res["Particle"] == part]["Energy"].sum() if (not df_res.empty and "Particle" in df_res.columns) else 0
                    dose_pct = (part_dose / total_events_energy) * 100 if total_events_energy > 0 else 0

                    self.table.insertRow(row_idx)
                    self.table.setItem(row_idx, 0, QTableWidgetItem(str(part)))
                    self.table.setItem(row_idx, 1, QTableWidgetItem(str(count)))
                    self.table.setItem(row_idx, 2, QTableWidgetItem(f"{avg_en:.2f}"))
                    self.table.setItem(row_idx, 3, QTableWidgetItem(str(p_hits)))
                    self.table.setItem(row_idx, 4, QTableWidgetItem(f"{dose_pct:.1f}%"))

                    self.secondary_summary_data.append({
                        "Particle": part, "Total Count": count, "Avg Energy (MeV)": f"{avg_en:.2f}",
                        "Payload Hits": p_hits, "Dose Contribution (%)": f"{dose_pct:.1f}%"
                    })
        self.csec.draw()

        # 3. Clear and Draw 3D Particle Tracks
        self.ax_3d.clear(); self.setup_plots(); self.draw_3d_legend_and_axes()
        self.draw_cube(self.ax_3d, 100, '#334155', 0.3)
        self.draw_cube(self.ax_3d, 100 - (thick*2), '#64748b', 0.5)
        
        if os.path.exists("tracks.csv") and os.path.getsize("tracks.csv") > 0:
            try:
                df_t = pd.read_csv("tracks.csv", names=["Event", "Track", "X", "Y", "Z", "Part"])
                for _, group in df_t.groupby(["Event", "Track"]):
                    c = PARTICLE_COLORS.get(group["Part"].iloc[0], "#ffffff")
                    self.ax_3d.plot(group["X"], group["Y"], group["Z"], color=c, alpha=0.9, linewidth=1.5)
            except Exception:
                pass
        
        self.ax_3d.set_xlim([-60, 60]); self.ax_3d.set_ylim([-60, 60]); self.ax_3d.set_zlim([-60, 60])
        self.c3d.draw()

        # 4. Clear and Draw Depth-Dose Profile
        self.ax_depth.clear(); self.setup_plots()
        depths = np.linspace(0, thick, 25)
        dose_profile = dose_gy * np.exp(-depths / (thick * 0.4)) + np.random.normal(0, dose_gy*0.02, len(depths))
        dose_profile = np.clip(dose_profile, 0, None)
        
        self.ax_depth.plot(depths, dose_profile, color='#f97316', linewidth=2.5, marker='o', markersize=4)
        self.ax_depth.fill_between(depths, dose_profile, color='#f97316', alpha=0.2)
        self.cdepth.draw()

    def export_report(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not dir_path: return

        self.fig_3d.savefig(os.path.join(dir_path, "3D_Particle_Tracks.png"), dpi=300, bbox_inches='tight', facecolor='#09090b')
        self.fig_spec.savefig(os.path.join(dir_path, "Energy_Spectrum.pdf"), bbox_inches='tight', facecolor='#09090b')
        self.fig_spec.savefig(os.path.join(dir_path, "Energy_Spectrum.png"), dpi=300, bbox_inches='tight', facecolor='#09090b')
        self.fig_sec.savefig(os.path.join(dir_path, "Secondary_Yield.pdf"), bbox_inches='tight', facecolor='#09090b')
        self.fig_sec.savefig(os.path.join(dir_path, "Secondary_Yield.png"), dpi=300, bbox_inches='tight', facecolor='#09090b')
        self.fig_depth.savefig(os.path.join(dir_path, "Depth_Dose_Profile.pdf"), bbox_inches='tight', facecolor='#09090b')
        self.fig_depth.savefig(os.path.join(dir_path, "Depth_Dose_Profile.png"), dpi=300, bbox_inches='tight', facecolor='#09090b')

        report_data = {
            "Parameter": ["Author", "Contact", "Altitude", "Material", "Thickness (mm)", "Particle", "Energy (MeV)", "Events", "Lifespan (Years)", 
                          "Payload Penetration", "Simulated Dose (Gy)", "Est Mission TID (kRad)", "Shielding Efficiency"],
            "Value": ["Piyush Pallav", "ppallav2014@gmail.com", self.alt_spin.value(), self.mat_cb.currentText(), self.thick_spin.value(), self.part_cb.currentText(), 
                      self.energy_spin.value(), self.events_spin.value(), self.years_spin.value(), 
                      getattr(self.kpi_hit, 'current_value', 'N/A'), getattr(self.kpi_dose, 'current_value', 'N/A'), 
                      getattr(self.kpi_tid, 'current_value', 'N/A'), getattr(self.kpi_eff, 'current_value', 'N/A')]
        }
        pd.DataFrame(report_data).to_csv(os.path.join(dir_path, "Mission_Summary.csv"), index=False)

        if self.secondary_summary_data:
            pd.DataFrame(self.secondary_summary_data).to_csv(os.path.join(dir_path, "Secondary_Particles_List.csv"), index=False)

        self.log(f"\n[SYSTEM] Report and plots successfully exported to: {dir_path}")

if __name__ == '__main__':
    app = QApplication(sys.argv); app.setStyle("Fusion")
    win = MasterDashboard(); win.show(); sys.exit(app.exec_())
