from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QDialog, QFileDialog, QStyleFactory,
    QFrame, QHeaderView, QTabWidget, QCheckBox, QGroupBox, QLabel, QSpacerItem,
    QSizePolicy, QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QPlainTextEdit
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
import math


class KoilHarmonicsEngine:
    """
    Harmonic calculation engine using koil.py methodology
    Uses slot current matrix approach - supports m phases
    """
    def __init__(self):
        self.matrix = None
        self.N_slots = 0
        self.num_phases = 3
        self.slot_cur_matrix = None
        self.N = 204  # Number of turns
        self.I_phase = 2.8  # Phase current magnitude
        self.phase_currents = {}  # Dict of phase currents {A: I_a, B: I_b, ...}
        self.Wt = 0.0  # Electrical angle
        self.pole_pairs = 1  # Number of pole pairs
        self.is_double_layer = False
        
    def set_matrix(self, matrix, is_double_layer=False):
        """Set the winding matrix and detect number of phases"""
        self.matrix = matrix
        self.is_double_layer = is_double_layer
        self.N_slots = matrix.shape[1] if matrix is not None else 0
        
        # Detect number of phases from matrix dimensions
        if matrix is not None:
            if is_double_layer:
                self.num_phases = matrix.shape[0] // 2
            else:
                self.num_phases = matrix.shape[0]
            
            # Initialize phase currents
            self.phase_currents = {}
            for i in range(self.num_phases):
                phase_name = chr(65 + i)  # A, B, C, D, ...
                self.phase_currents[phase_name] = self.I_phase
        
        self.compute_slot_current_matrix()
        
    def compute_slot_current_matrix(self):
        """
        Compute slot current matrix using koil.py approach for m phases
        slot_cur_matrix[j] = sum of phase contributions at slot j
        Phase k has current: I_k * cos(Wt - 2*pi*k/m)
        """
        if self.matrix is None:
            return
        
        Q = self.N_slots
        m = self.num_phases
        
        # Calculate instantaneous current factors based on Wt
        # For m phases: phase k has angle offset 2*pi*k/m
        wt_rad = np.radians(self.Wt)
        
        current_factors = []
        for k in range(m):
            phase_angle = 2 * np.pi * k / m
            phase_name = chr(65 + k)
            I_magnitude = self.phase_currents.get(phase_name, self.I_phase)
            i_k = I_magnitude * np.cos(wt_rad - phase_angle)
            current_factors.append(i_k)
        
        # Build slot current matrix
        self.slot_cur_matrix = np.zeros(Q)
        
        if self.is_double_layer:
            # Double layer: matrix is 2m × Q
            # Top layers: rows 0 to m-1
            # Bottom layers: rows m to 2m-1
            for k in range(m):
                phase_top = self.matrix[k]
                phase_bot = self.matrix[k + m]
                phase_sum = phase_top + phase_bot
                self.slot_cur_matrix += phase_sum * current_factors[k]
        else:
            # Single layer: matrix is m × Q
            for k in range(m):
                phase_matrix = self.matrix[k]
                self.slot_cur_matrix += phase_matrix * current_factors[k]
    
    def calculate_mmf_koil(self):
        """
        Calculate MMF using koil.py method - step waveform on slots
        Returns x positions and mmf values for plotting (total MMF)
        """
        if self.slot_cur_matrix is None:
            return None, None
        
        Q = self.N_slots
        D = 1.0  # Normalized diameter
        ws = 1e-3  # Small slot width for visualization
        ps = math.pi * D / Q  # Slot pitch
        
        mmf = []
        x = []
        
        mmf_temp = 0
        int_mmf = 0
        
        for i in range(Q):
            # Start of slot
            x.append((ps - ws) / 2 + ps * i)
            mmf.append(mmf_temp)
            
            # Add current contribution
            mmf_temp += self.slot_cur_matrix[i]
            
            # End of slot
            x.append((ps + ws) / 2 + ps * i)
            mmf.append(mmf_temp)
            
            int_mmf += mmf_temp
        
        # Remove average to center the waveform
        avg_mmf = int_mmf / Q
        mmf_centered = [m - avg_mmf for m in mmf]
        
        return x, mmf_centered
    
    def calculate_mmf_single_phase(self, phase_name):
        """
        Calculate MMF for a single phase using koil.py method
        
        Parameters:
        -----------
        phase_name : str
            Phase name (A, B, C, D, ...)
            
        Returns:
        --------
        x, mmf : arrays for plotting
        """
        if self.matrix is None:
            return None, None
        
        Q = self.N_slots
        m = self.num_phases
        
        # Get phase index
        phase_idx = ord(phase_name) - 65  # A=0, B=1, C=2, ...
        if phase_idx < 0 or phase_idx >= m:
            return None, None
        
        # Calculate current factor for this phase
        wt_rad = np.radians(self.Wt)
        phase_angle = 2 * np.pi * phase_idx / m
        I_magnitude = self.phase_currents.get(phase_name, self.I_phase)
        i_phase = I_magnitude * np.cos(wt_rad - phase_angle)
        
        # Get phase contribution to slot current
        if self.is_double_layer:
            phase_top = self.matrix[phase_idx]
            phase_bot = self.matrix[phase_idx + m]
            phase_slot_current = (phase_top + phase_bot) * i_phase
        else:
            phase_slot_current = self.matrix[phase_idx] * i_phase
        
        # Calculate MMF step waveform
        D = 1.0
        ws = 1e-3
        ps = math.pi * D / Q
        
        mmf = []
        x = []
        mmf_temp = 0
        int_mmf = 0
        
        for i in range(Q):
            x.append((ps - ws) / 2 + ps * i)
            mmf.append(mmf_temp)
            
            mmf_temp += phase_slot_current[i]
            
            x.append((ps + ws) / 2 + ps * i)
            mmf.append(mmf_temp)
            
            int_mmf += mmf_temp
        
        # Center the waveform
        avg_mmf = int_mmf / Q
        mmf_centered = [m - avg_mmf for m in mmf]
        
        return x, mmf_centered
    
    def calculate_harmonics(self, D=1.0, nu_max=50, ws=0):
        """
        Calculate harmonics using exact koil.py method
        
        Parameters:
        -----------
        D : float
            Stator airgap diameter
        nu_max : int
            Maximum harmonic order
        ws : float
            Slot opening width
            
        Returns:
        --------
        dict : Harmonics data
        """
        if self.slot_cur_matrix is None:
            return None
        
        Q = self.N_slots
        
        # Check slot width feasibility
        if ws > math.pi * D / Q:
            ws = 0
        
        # Calculate a and b coefficients (koil.py method)
        a = []
        b = []
        
        for nu in range(nu_max + 1):  # Include nu=0
            # Cosine coefficient
            _sum_a = 0
            for j in range(Q):
                _sum_a += self.slot_cur_matrix[j] * math.cos(nu * 2 * math.pi / Q * (j + 0.5))
            
            if ws == 0:
                a_nu = _sum_a * 2 / (math.pi * D)
            else:
                if nu == 0:
                    a_nu = _sum_a * 2 / (math.pi * D)
                else:
                    a_nu = _sum_a * 2 / (math.pi * nu * ws) * math.sin(nu * ws / D)
            
            a.append(a_nu)
            
            # Sine coefficient
            _sum_b = 0
            for j in range(Q):
                _sum_b += self.slot_cur_matrix[j] * math.sin(nu * 2 * math.pi / Q * (j + 0.5))
            
            if ws == 0:
                b_nu = _sum_b * 2 / (math.pi * D)
            else:
                if nu == 0:
                    b_nu = _sum_b * 2 / (math.pi * D)
                else:
                    b_nu = _sum_b * 2 / (math.pi * nu * ws) * math.sin(nu * ws / D)
            
            b.append(b_nu)
        
        # Calculate phi and c (koil.py method)
        phi = []
        c = []
        for nu in range(nu_max + 1):
            if abs(b[nu]) < 1e-10:
                # b is zero, c is purely from a coefficient
                phi.append(-math.pi / 2 if a[nu] >= 0 else math.pi / 2)
                c.append(abs(a[nu]))
            elif abs(a[nu]) < 1e-10:
                # a is zero, c is purely from b coefficient  
                phi.append(0)
                c.append(abs(b[nu]))
            else:
                phi.append(math.atan2(a[nu], b[nu]))
                c.append(b[nu] / math.cos(phi[nu]))
        
        # Calculate d (MMF amplitude) - koil.py method
        d = []
        for nu in range(nu_max + 1):
            if nu == 0:
                d.append(0)
            else:
                d.append(-D / 2 * c[nu] / nu)
        
        # Build results (skip nu=0 for display)
        harmonics = list(range(1, nu_max + 1))
        a_coeffs = a[1:]
        b_coeffs = b[1:]
        amplitudes = [abs(c[i]) for i in range(1, nu_max + 1)]
        phases = phi[1:]
        mmf_amplitudes = [abs(d[i]) for i in range(1, nu_max + 1)]
        
        # Calculate percentage relative to pole_pairs harmonic (fundamental)
        fundamental_idx = self.pole_pairs - 1  # Index of fundamental harmonic
        if fundamental_idx < len(mmf_amplitudes) and mmf_amplitudes[fundamental_idx] != 0:
            fundamental = mmf_amplitudes[fundamental_idx]
        else:
            fundamental = max(mmf_amplitudes) if mmf_amplitudes else 1
        percentages = [(amp / fundamental * 100) for amp in mmf_amplitudes]
        
        return {
            'harmonics': harmonics,
            'a': a_coeffs,
            'b': b_coeffs,
            'amplitude': amplitudes,
            'phase': phases,
            'mmf_amplitude': mmf_amplitudes,
            'percentage': percentages,
            'fundamental': fundamental
        }
    
    def update_current(self, new_current):
        """Update current values for all phases"""
        self.I_phase = new_current
        for phase_name in self.phase_currents.keys():
            self.phase_currents[phase_name] = new_current
        self.compute_slot_current_matrix()
    
    def update_wt_angle(self, new_wt):
        """Update Wt angle"""
        self.Wt = new_wt
        self.compute_slot_current_matrix()


class KoilHarmonicsTab(QWidget):
    """Tab for koil-method harmonic analysis"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Create koil harmonics engine
        self.koil_engine = KoilHarmonicsEngine()
        self.matrix = None
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.advance_animation)
        self.is_animating = False
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget for different views
        self.view_tabs = QTabWidget()
        
        # Tab 1: Slot Current Matrix
        slot_tab = QWidget()
        slot_layout = QVBoxLayout(slot_tab)
        self.canvas_slot = FigureCanvas(Figure(figsize=(10, 4)))
        self.fig_slot = self.canvas_slot.figure
        self.ax_slot = self.fig_slot.add_subplot(111)
        
        # Set white background
        self.fig_slot.patch.set_facecolor('white')
        self.ax_slot.set_facecolor('white')
        
        slot_layout.addWidget(self.canvas_slot)
        self.view_tabs.addTab(slot_tab, "Slot Current Matrix")
        
        # Tab 2: MMF Waveform (Koil method)
        mmf_tab = QWidget()
        mmf_layout = QVBoxLayout(mmf_tab)
        self.canvas_mmf = FigureCanvas(Figure(figsize=(10, 4)))
        self.fig_mmf = self.canvas_mmf.figure
        self.ax_mmf = self.fig_mmf.add_subplot(111)
        
        # Set white background
        self.fig_mmf.patch.set_facecolor('white')
        self.ax_mmf.set_facecolor('white')
        
        mmf_layout.addWidget(self.canvas_mmf)
        self.view_tabs.addTab(mmf_tab, "MMF Waveform")
        
        layout.addWidget(self.view_tabs)
        
        # Control panel
        control_panel = QFrame()
        control_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        controls_layout = QHBoxLayout(control_panel)
        
        # Current input
        current_group = QGroupBox("Current (A)")
        current_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        current_layout = QHBoxLayout(current_group)
        
        self.current_spin = QDoubleSpinBox()
        self.current_spin.setRange(0.1, 1000.0)
        self.current_spin.setValue(2.8)
        self.current_spin.setSingleStep(0.1)
        self.current_spin.setDecimals(2)
        self.current_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 13px;
            }
        """)
        self.current_spin.valueChanged.connect(self.update_current)
        current_layout.addWidget(self.current_spin)
        controls_layout.addWidget(current_group)
        
        # Wt angle input
        wt_group = QGroupBox("Wt Angle (°)")
        wt_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        wt_layout = QHBoxLayout(wt_group)
        
        self.wt_spin = QDoubleSpinBox()
        self.wt_spin.setRange(0, 360)
        self.wt_spin.setValue(0)
        self.wt_spin.setSingleStep(1.0)
        self.wt_spin.setDecimals(1)
        self.wt_spin.setWrapping(True)
        self.wt_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 13px;
            }
        """)
        self.wt_spin.valueChanged.connect(self.update_wt_angle)
        wt_layout.addWidget(self.wt_spin)
        controls_layout.addWidget(wt_group)
        
        # Phase selection group
        phase_group = QGroupBox("Phases to Plot")
        phase_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        self.phase_layout = QHBoxLayout(phase_group)
        
        # Phase checkboxes will be added dynamically
        self.phase_checkboxes = {}
        
        # Resultant checkbox
        self.resultant_checkbox = QCheckBox("Resultant")
        self.resultant_checkbox.setChecked(True)
        self.resultant_checkbox.setStyleSheet("QCheckBox { color: #ffffff; }")
        self.resultant_checkbox.stateChanged.connect(self.update_mmf_plot)
        self.phase_layout.addWidget(self.resultant_checkbox)
        
        controls_layout.addWidget(phase_group)
        
        # Animation button
        self.animate_btn = QPushButton("Start Animation")
        self.animate_btn.clicked.connect(self.toggle_animation)
        self.animate_btn.setMinimumWidth(140)
        self.animate_btn.setMinimumHeight(35)
        self.animate_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        controls_layout.addWidget(self.animate_btn)
        
        # Harmonics button
        harmonics_btn = QPushButton("Analyze Harmonics")
        harmonics_btn.clicked.connect(self.show_harmonics_window)
        harmonics_btn.setMinimumWidth(140)
        harmonics_btn.setMinimumHeight(35)
        controls_layout.addWidget(harmonics_btn)
        
        # Spacer
        controls_layout.addStretch()
        
        layout.addWidget(control_panel)
        
    def update_matrix(self, winding_pattern, is_double_layer, poles):
        """Update the winding matrix and create phase checkboxes"""
        self.koil_engine.pole_pairs = poles
        
        if hasattr(self.parent, 'stator_drawing') and self.parent.stator_drawing.winding_obj:
            if is_double_layer:
                self.matrix = self.parent.stator_drawing.get_double_layer_matrix()
            else:
                matrices = self.parent.stator_drawing.winding_obj.get_slot_matrices(normalize=True)
                self.matrix = np.array(matrices) if matrices else None
            
            if self.matrix is not None:
                self.koil_engine.set_matrix(self.matrix, is_double_layer)
                
                # Create phase checkboxes dynamically
                self._create_phase_checkboxes()
                
                self.update_plot()
    
    def _create_phase_checkboxes(self):
        """Create phase checkboxes based on number of phases"""
        # Clear existing phase checkboxes
        for phase, cb in list(self.phase_checkboxes.items()):
            cb.setParent(None)
            cb.deleteLater()
        self.phase_checkboxes.clear()
        
        # Get number of phases
        num_phases = self.koil_engine.num_phases
        
        # Create checkboxes for each phase
        for i in range(num_phases):
            phase_name = chr(65 + i)  # A, B, C, D, ...
            cb = QCheckBox(f"Phase {phase_name}")
            cb.setChecked(False)  # Start unchecked
            cb.setStyleSheet("QCheckBox { color: #ffffff; }")
            cb.stateChanged.connect(self.update_mmf_plot)
            self.phase_checkboxes[phase_name] = cb
            # Insert before resultant checkbox
            self.phase_layout.insertWidget(len(self.phase_checkboxes) - 1, cb)
    
    def update_current(self):
        """Update current in engine"""
        new_current = self.current_spin.value()
        self.koil_engine.update_current(new_current)
        self.update_plot()
    
    def update_wt_angle(self):
        """Update Wt angle in engine"""
        new_wt = self.wt_spin.value()
        self.koil_engine.update_wt_angle(new_wt)
        self.update_plot()
    
    def toggle_animation(self):
        """Start or stop the animation"""
        if self.is_animating:
            # Stop animation
            self.animation_timer.stop()
            self.is_animating = False
            self.animate_btn.setText("Start Animation")
            self.animate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
            """)
        else:
            # Start animation
            self.animation_timer.start(50)  # Update every 50ms
            self.is_animating = True
            self.animate_btn.setText("Stop Animation")
            self.animate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #c83200;
                    color: white;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #e03a00;
                }
            """)
    
    def advance_animation(self):
        """Advance the Wt angle for animation"""
        current_wt = self.wt_spin.value()
        new_wt = (current_wt + 2) % 360  # Increment by 2 degrees
        self.wt_spin.setValue(new_wt)
    
    def update_plot(self):
        """Update both plots"""
        self.update_slot_current_plot()
        self.update_mmf_plot()
    
    def update_slot_current_plot(self):
        """Update the slot current matrix plot"""
        self.ax_slot.clear()
        
        if self.koil_engine.slot_cur_matrix is None:
            return
        
        Q = self.koil_engine.N_slots
        slots = np.arange(1, Q + 1)
        values = self.koil_engine.slot_cur_matrix
        
        # Bar plot of slot current matrix
        colors = ['red' if v > 0 else 'blue' if v < 0 else 'gray' for v in values]
        self.ax_slot.bar(slots, values, color=colors, alpha=0.7, edgecolor='black')
        
        self.ax_slot.set_xlabel('Slot Number', fontsize=12, color='black')
        self.ax_slot.set_ylabel('Slot Current (normalized)', fontsize=12, color='black')
        self.ax_slot.set_title(f'Slot Current Matrix - Wt = {self.koil_engine.Wt:.1f}°', 
                         fontsize=14, color='black', fontweight='bold')
        self.ax_slot.grid(True, alpha=0.3, color='black')
        self.ax_slot.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        # Style
        self.ax_slot.set_facecolor('white')
        self.fig_slot.patch.set_facecolor('white')
        self.ax_slot.tick_params(colors='black')
        self.ax_slot.spines['bottom'].set_color('black')
        self.ax_slot.spines['left'].set_color('black')
        self.ax_slot.spines['top'].set_color('black')
        self.ax_slot.spines['right'].set_color('black')
        
        self.fig_slot.tight_layout()
        self.canvas_slot.draw()
    
    def update_mmf_plot(self):
        """Update the MMF waveform plot with individual phases and resultant"""
        self.ax_mmf.clear()
        
        if self.koil_engine.slot_cur_matrix is None:
            return
        
        # Generate colors for phases
        num_phases = self.koil_engine.num_phases
        phase_colors = self._generate_phase_colors(num_phases)
        
        # Plot individual phases if selected
        for phase_name, cb in self.phase_checkboxes.items():
            if cb.isChecked():
                x, mmf = self.koil_engine.calculate_mmf_single_phase(phase_name)
                if x is not None and mmf is not None:
                    color = phase_colors.get(phase_name, 'white')
                    self.ax_mmf.plot(x, mmf, color=color, linestyle='-', linewidth=1.5, 
                                    label=f'Phase {phase_name}', alpha=0.8)
        
        # Plot resultant if selected
        if self.resultant_checkbox.isChecked():
            x, mmf = self.koil_engine.calculate_mmf_koil()
            if x is not None and mmf is not None:
                self.ax_mmf.plot(x, mmf, color='cyan', linestyle='-', linewidth=2.5, 
                                label='Resultant', alpha=1.0)
                self.ax_mmf.fill_between(x, mmf, alpha=0.2, color='cyan')
        
        self.ax_mmf.set_xlabel('Position (normalized)', fontsize=12, color='black')
        self.ax_mmf.set_ylabel('MMF (normalized)', fontsize=12, color='black')
        self.ax_mmf.set_title(f'MMF Step Waveform - Wt = {self.koil_engine.Wt:.1f}°', 
                             fontsize=14, color='black', fontweight='bold')
        self.ax_mmf.grid(True, alpha=0.3, color='black')
        self.ax_mmf.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        # Add legend if any phases are plotted
        if any(cb.isChecked() for cb in self.phase_checkboxes.values()) or self.resultant_checkbox.isChecked():
            self.ax_mmf.legend(facecolor='white', edgecolor='black', labelcolor='black', fontsize=10)
        
        # Style
        self.ax_mmf.set_facecolor('white')
        self.fig_mmf.patch.set_facecolor('white')
        self.ax_mmf.tick_params(colors='black')
        self.ax_mmf.spines['bottom'].set_color('black')
        self.ax_mmf.spines['left'].set_color('black')
        self.ax_mmf.spines['top'].set_color('black')
        self.ax_mmf.spines['right'].set_color('black')
        
        self.fig_mmf.tight_layout()
        self.canvas_mmf.draw()
    
    def _generate_phase_colors(self, num_phases):
        """Generate colors for phases matching StatorDrawing colors"""
        colors = {}
        phase_names = [chr(65 + i) for i in range(num_phases)]
        
        if num_phases == 2:
            color_list = ['red', 'blue']
        elif num_phases == 3:
            color_list = ['red', 'blue', 'green']
        elif num_phases == 4:
            color_list = ['red', 'green', 'blue', 'yellow']
        elif num_phases == 5:
            color_list = ['red', 'green', 'blue', 'yellow', 'magenta']
        elif num_phases == 6:
            color_list = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
        else:
            # Generate colors using HSV for 7+ phases
            import colorsys
            color_list = []
            for i in range(num_phases):
                hue = i / num_phases
                rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                # Convert to hex
                color_list.append('#%02x%02x%02x' % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255)))
        
        for i, phase in enumerate(phase_names):
            colors[phase] = color_list[i]
        
        return colors
    
    def show_harmonics_window(self):
        """Show harmonics analysis window"""
        if self.matrix is None:
            return
        
        self.harmonics_window = KoilHarmonicsWindow(self, self.koil_engine)
        self.harmonics_window.show()


class KoilHarmonicsWindow(QDialog):
    """Window for koil-method harmonic analysis"""
    def __init__(self, parent=None, koil_engine=None):
        super().__init__(parent)
        self.parent = parent
        self.koil_engine = koil_engine
        
        self.setWindowTitle("Koil Method - Harmonic Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        self._init_ui()
        self.perform_analysis()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Max harmonic order
        harmonics_group = QGroupBox("Max Harmonic Order")
        harmonics_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        harmonics_layout = QHBoxLayout(harmonics_group)
        
        self.nu_max_spin = QSpinBox()
        self.nu_max_spin.setRange(10, 100)
        self.nu_max_spin.setValue(50)
        self.nu_max_spin.setSingleStep(10)
        self.nu_max_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 13px;
            }
        """)
        self.nu_max_spin.valueChanged.connect(self.perform_analysis)
        harmonics_layout.addWidget(self.nu_max_spin)
        controls_layout.addWidget(harmonics_group)
        
        # Diameter
        diameter_group = QGroupBox("Diameter D")
        diameter_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        diameter_layout = QHBoxLayout(diameter_group)
        
        self.diameter_spin = QDoubleSpinBox()
        self.diameter_spin.setRange(0.1, 10.0)
        self.diameter_spin.setValue(1.0)
        self.diameter_spin.setSingleStep(0.1)
        self.diameter_spin.setDecimals(2)
        self.diameter_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px;
                font-size: 13px;
            }
        """)
        self.diameter_spin.valueChanged.connect(self.perform_analysis)
        diameter_layout.addWidget(self.diameter_spin)
        controls_layout.addWidget(diameter_group)
        
        # Recompute button
        recompute_btn = QPushButton("Recompute")
        recompute_btn.setMinimumWidth(100)
        recompute_btn.setMinimumHeight(35)
        recompute_btn.clicked.connect(self.perform_analysis)
        controls_layout.addWidget(recompute_btn)
        
        # Export button
        export_btn = QPushButton("Export CSV")
        export_btn.setMinimumWidth(100)
        export_btn.setMinimumHeight(35)
        export_btn.clicked.connect(self.export_harmonics)
        controls_layout.addWidget(export_btn)
        
        controls_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(80)
        close_btn.setMinimumHeight(35)
        close_btn.clicked.connect(self.close)
        controls_layout.addWidget(close_btn)
        
        layout.addLayout(controls_layout)
        
        # Splitter for plots and text
        splitter = QWidget()
        splitter_layout = QHBoxLayout(splitter)
        
        # Left side: Bar chart
        self.canvas = FigureCanvas(Figure(figsize=(10, 8)))
        self.fig = self.canvas.figure
        self.ax = self.fig.add_subplot(111)
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        splitter_layout.addWidget(self.canvas, stretch=2)
        
        # Right side: Text summary
        summary_group = QGroupBox("Harmonic Summary")
        summary_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; font-weight: bold; }")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QPlainTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QPlainTextEdit { 
                background-color: #1e1e1e; 
                color: #dddddd; 
                font-family: Consolas, monospace; 
                font-size: 12px; 
            }
        """)
        summary_layout.addWidget(self.summary_text)
        splitter_layout.addWidget(summary_group, stretch=1)
        
        layout.addWidget(splitter)
        
    def perform_analysis(self):
        """Perform harmonic analysis"""
        nu_max = self.nu_max_spin.value()
        D = self.diameter_spin.value()
        
        # Get harmonics data
        self.harmonics_data = self.koil_engine.calculate_harmonics(D=D, nu_max=nu_max, ws=0)
        
        if self.harmonics_data is None:
            return
        
        # Update plot
        self.plot_harmonics()
        
        # Update summary text
        summary = self.create_summary()
        self.summary_text.setPlainText(summary)
        
    def create_summary(self):
        """Create text summary"""
        summary = []
        P = self.koil_engine.pole_pairs
        summary.append("=" * 80)
        summary.append("MMF HARMONIC ANALYSIS")
        summary.append("=" * 80)
        summary.append(f"Pole Pairs: {P}")
        summary.append(f"Fundamental (harmonic {P}) Amplitude: {self.harmonics_data['fundamental']:.6f}")
        summary.append(f"Number of harmonics analyzed: {len(self.harmonics_data['harmonics'])}")
        summary.append("")
        summary.append("All Harmonics:")
        summary.append("-" * 80)
        summary.append(f"{'Order':<8} {'Amplitude':<15} {'% of Fund.':<15} {'Phase (deg)':<15}")
        summary.append("-" * 80)
        
        # Show all harmonics
        for i, nu in enumerate(self.harmonics_data['harmonics']):
            amp = self.harmonics_data['mmf_amplitude'][i]
            pct = self.harmonics_data['percentage'][i]
            phase_deg = np.degrees(self.harmonics_data['phase'][i])
            
            if nu == P:
                summary.append(f"{nu:<8} {amp:<15.6f} {pct:<15.2f} {phase_deg:<15.2f} (FUNDAMENTAL)")
            elif pct > 1.0:
                summary.append(f"{nu:<8} {amp:<15.6f} {pct:<15.2f} {phase_deg:<15.2f}")
        
        summary.append("-" * 80)
        
        # THD calculation
        if len(self.harmonics_data['mmf_amplitude']) > 1:
            fundamental_idx = P - 1
            if fundamental_idx < len(self.harmonics_data['mmf_amplitude']):
                fundamental = self.harmonics_data['mmf_amplitude'][fundamental_idx]
                # Sum all harmonics except the fundamental
                harmonics_sum = sum([amp**2 for i, amp in enumerate(self.harmonics_data['mmf_amplitude']) 
                                    if i != fundamental_idx])
                thd = np.sqrt(harmonics_sum) / fundamental * 100 if fundamental > 0 else 0
                summary.append(f"Total Harmonic Distortion (THD): {thd:.2f}%")
        
        summary.append("=" * 80)
        
        return "\n".join(summary)
        
    def plot_harmonics(self):
        """Plot harmonic bar chart"""
        self.ax.clear()
        
        harmonics = self.harmonics_data['harmonics']
        percentages = self.harmonics_data['percentage']
        
        # Bar chart
        P = self.koil_engine.pole_pairs
        colors = ['red' if h % 2 == 1 else 'blue' for h in harmonics]
        bars = self.ax.bar(harmonics, percentages, color=colors, alpha=0.7, edgecolor='black')
        
        # Highlight fundamental (harmonic equal to pole pairs)
        if P in harmonics:
            fundamental_idx = harmonics.index(P)
            bars[fundamental_idx].set_color('green')
            bars[fundamental_idx].set_alpha(1.0)
        
        self.ax.set_xlabel('Harmonic Order', fontsize=12, color='black')
        self.ax.set_ylabel('Magnitude (% of Fundamental)', fontsize=12, color='black')
        self.ax.set_title('MMF Harmonic Spectrum', 
                         fontsize=14, color='black', fontweight='bold')
        self.ax.grid(True, alpha=0.3, color='black')
        self.ax.set_xlim(0, max(harmonics) + 1)
        
        # Style
        self.ax.set_facecolor('white')
        self.fig.patch.set_facecolor('white')
        self.ax.tick_params(colors='black')
        self.ax.spines['bottom'].set_color('black')
        self.ax.spines['left'].set_color('black')
        self.ax.spines['top'].set_color('black')
        self.ax.spines['right'].set_color('black')
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='green', alpha=1.0, label='Fundamental'),
            Patch(facecolor='red', alpha=0.7, label='Odd Harmonics'),
            Patch(facecolor='blue', alpha=0.7, label='Even Harmonics')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', 
                      facecolor='white', edgecolor='black', 
                      labelcolor='black', fontsize=10)
        
        self.fig.tight_layout()
        self.canvas.draw()
        
    def export_harmonics(self):
        """Export harmonics data to CSV"""
        if self.harmonics_data is None:
            return
        
        try:
            filename = f"koil_harmonics_Wt{self.koil_engine.Wt:.0f}deg.csv"
            
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Koil Harmonics Data", 
                filename, 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if save_path:
                df = pd.DataFrame({
                    'Harmonic_Order': self.harmonics_data['harmonics'],
                    'Amplitude': self.harmonics_data['mmf_amplitude'],
                    'Percentage_of_Fundamental': self.harmonics_data['percentage'],
                    'Phase_Angle_rad': self.harmonics_data['phase'],
                    'a_coefficient': self.harmonics_data['a'],
                    'b_coefficient': self.harmonics_data['b']
                })
                
                df.to_csv(save_path, index=False)
                
        except Exception as e:
            pass


def setup_koil_harmonics_tab(self):
    """Setup the koil harmonics tab"""
    self.koil_harmonics_tab = KoilHarmonicsTab(self)
    layout = QVBoxLayout()
    layout.addWidget(self.koil_harmonics_tab)
    self.tab_koil_harmonics.setLayout(layout)
    
    # Update when switching to tab
    def update_koil_tab():
        pole_pairs = self.poles_spin.value()  # User enters pole pairs directly
        self.koil_harmonics_tab.update_matrix(
            self.stator_drawing.winding_pattern,
            self.stator_drawing.is_double_layer,
            pole_pairs
        )
    
    self.tabs.currentChanged.connect(
        lambda index: update_koil_tab() if self.tabs.tabText(index) == "MMF and Harmonics" else None
    )
