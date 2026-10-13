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
from mmf_calculation_engine import MMFPlotWidget

class ResultantAnimationWindow(QDialog):
    """Window for animated resultant plot that varies with Wt"""
    def __init__(self, parent=None, mmf_calculator=None):
        super().__init__(parent)
        self.parent = parent
        self.mmf_calculator = mmf_calculator
        self.current_wt = 0.0
        self.wt_step = 2.5  # Default step size changed to Mid
        self.speed_steps = {'Slow': 1.0, 'Mid': 2.5, 'Fast': 7.5}  # Updated speed options
        self.current_speed = 'Mid'  # Changed default to Mid
        
        self.setWindowTitle("Resultant MMF Animation - Wt Variable")
        self.setGeometry(100, 100, 1400, 800)  # Increased from 1000x600 to 1400x800
        
        self._init_ui()
        self._setup_animation()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create matplotlib canvas for animation
        self.canvas = FigureCanvas(Figure(figsize=(16, 8)))  # Increased from (12, 6) to (16, 8)
        self.fig = self.canvas.figure
        self.ax = self.fig.add_subplot(111)
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        layout.addWidget(self.canvas)
        
        # Add control buttons
        controls_layout = QHBoxLayout()
        
        # Current Wt display
        self.wt_label = QLabel(f"Current Wt: {self.current_wt:.1f}°")
        self.wt_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        controls_layout.addWidget(self.wt_label)
        
        controls_layout.addStretch()
        
        # Speed controls group
        speed_group = QGroupBox("Animation Speed")
        speed_group.setStyleSheet("QGroupBox { color: #ffffff; }")
        speed_layout = QHBoxLayout(speed_group)
        speed_layout.setSpacing(5)
        
        # Speed buttons
        self.speed_buttons = {}
        for speed_name in ['Slow', 'Mid', 'Fast']:
            btn = QPushButton(speed_name)
            btn.setCheckable(True)
            btn.setMinimumWidth(60)
            btn.clicked.connect(lambda checked, name=speed_name: self.set_speed(name))
            self.speed_buttons[speed_name] = btn
            speed_layout.addWidget(btn)
        
        # Set default speed
        self.speed_buttons[self.current_speed].setChecked(True)
        controls_layout.addWidget(speed_group)
        
        controls_layout.addStretch()
        
        # Pause/Resume button
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_animation)
        self.pause_btn.setMinimumWidth(80)
        controls_layout.addWidget(self.pause_btn)
        
        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_animation)
        reset_btn.setMinimumWidth(80)
        controls_layout.addWidget(reset_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(80)
        controls_layout.addWidget(close_btn)
        
        layout.addLayout(controls_layout)
        
    def set_speed(self, speed_name):
        """Set animation speed and update button states"""
        # Update current speed and step size
        self.current_speed = speed_name
        self.wt_step = self.speed_steps[speed_name]
        
        # Update button states
        for name, btn in self.speed_buttons.items():
            btn.setChecked(name == speed_name)
        
        print(f"Animation speed set to {speed_name} (step: {self.wt_step}°)")
        
    def _setup_animation(self):
        """Setup the animation timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)  # Update every 50ms for smooth animation
        self.is_paused = False
        
    def update_animation(self):
        """Update the animation by incrementing Wt and replotting"""
        if self.is_paused:
            return
            
        # Update Wt angle
        self.current_wt += self.wt_step
        if self.current_wt >= 360:
            self.current_wt = 0.0
            
        # Update the MMF calculator with new Wt
        original_wt = self.mmf_calculator.Wt
        self.mmf_calculator.Wt = self.current_wt
        
        # Recalculate only the resultant profile
        if self.mmf_calculator.matrix is not None:
            # Get current phase profiles (don't recalculate them)
            prof_A = self.mmf_calculator.mmf_profile_A
            prof_B = self.mmf_calculator.mmf_profile_B
            prof_C = self.mmf_calculator.mmf_profile_C
            
            if prof_A and prof_B and prof_C:
                # Recalculate only the resultant with new Wt
                self.mmf_calculator.mmf_profile_resultant = self.mmf_calculator._calculate_resultant_new_formula(
                    prof_A, prof_B, prof_C)
                
                # Update the plot
                self.plot_resultant()
        
        # Update the Wt display
        self.wt_label.setText(f"Current Wt: {self.current_wt:.1f}°")
        
    def plot_resultant(self):
        """Plot only the resultant curve"""
        self.ax.clear()
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        # Get resultant data
        angles, values = self.mmf_calculator.get_profile_data('resultant')
        
        if angles is not None and values is not None:
            self.ax.plot(angles, values, 
                        color='red', linestyle='-', linewidth=3)
            
            self.ax.set_xlabel('Mechanical Angle [degrees]', color='black')
            self.ax.set_ylabel('MMF [A·t]', color='black')
            self.ax.set_title('Variation of Resultant MMF with Time', color='black')  # Updated title
            self.ax.grid(True, color='black', alpha=0.3)
            self.ax.set_xlim(0, 360)
            self.ax.tick_params(colors='black')
            # Legend removed - no longer needed
            
        self.canvas.draw()
        
    def toggle_animation(self):
        """Pause or resume the animation"""
        self.is_paused = not self.is_paused
        self.pause_btn.setText("Resume" if self.is_paused else "Pause")
        
    def reset_animation(self):
        """Reset animation to start from Wt = 0°"""
        self.current_wt = 0.0
        self.wt_label.setText(f"Current Wt: {self.current_wt:.1f}°")
        # Reset to default speed (now Mid)
        self.set_speed('Mid')
        
    def closeEvent(self, event):
        """Handle window close event"""
        self.timer.stop()
        event.accept()

class ConnectionMatrixTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        # Create calculation engine
        self.mmf_calculator = MMFPlotWidget()

        # Create matplotlib canvas
        self.canvas = FigureCanvas(Figure(figsize=(10, 4)))
        self.fig = self.canvas.figure
        self.ax = self.fig.add_subplot(111)
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        
        # Define spinbox styling to match slot arc design
        spinbox_style = """
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 4px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 70px;
            }
            QSpinBox:hover {
                background-color: #3d3d3d;
                border: 1px solid #555555;
            }
            QSpinBox:focus {
                background-color: #3d3d3d;
                border: 1px solid #0078d4;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #444444;
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #555555;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                color: #ffffff;
                width: 8px;
                height: 8px;
            }
        """
        
        # Create control panel directly (no tabs)
        control_panel = QWidget()
        control_panel.setMinimumHeight(80)  # Reduced height
        control_panel.setMaximumHeight(100)  # Reduced maximum height
        
        # Main horizontal layout for all controls
        controls_layout = QHBoxLayout(control_panel)
        controls_layout.setContentsMargins(10, 10, 10, 10)
        controls_layout.setSpacing(15)
        
        # Add left spacer to center the main controls
        left_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        controls_layout.addItem(left_spacer)
        
        # Create phase selection group
        phase_group = QGroupBox("Phases to Plot")
        phase_group.setMinimumWidth(250)  # Increased width to accommodate resultant
        phase_layout = QHBoxLayout(phase_group)  # Keep horizontal
        phase_layout.setSpacing(10)
        
        # Add checkboxes for phases (will be populated dynamically)
        self.phase_checkboxes = {}
        self.phase_group_layout = phase_layout  # Store reference for dynamic updates
        
        # Initialize with 3 phases by default
        self._create_phase_checkboxes(3)
        
        # Add resultant checkbox
        self.resultant_checkbox = QCheckBox("Resultant")
        self.resultant_checkbox.setChecked(False)
        self.resultant_checkbox.stateChanged.connect(self.update_plot)
        phase_layout.addWidget(self.resultant_checkbox)

        controls_layout.addWidget(phase_group)
        
        # Create linewidth controls group (removed layer controls)
        linewidth_group = QGroupBox("Line Width")
        linewidth_group.setMinimumWidth(150)  # Reduced width since only one control
        linewidth_layout = QHBoxLayout(linewidth_group)
        linewidth_layout.setSpacing(10)
        
        # Phase linewidth control only
        phase_lw_label = QLabel("Phases:")
        self.phase_linewidth_spin = QSpinBox()
        self.phase_linewidth_spin.setMinimum(1)
        self.phase_linewidth_spin.setMaximum(10)
        self.phase_linewidth_spin.setValue(2)
        self.phase_linewidth_spin.setSuffix(" px")
        self.phase_linewidth_spin.setStyleSheet(spinbox_style)
        self.phase_linewidth_spin.valueChanged.connect(self.update_plot)
        linewidth_layout.addWidget(phase_lw_label)
        linewidth_layout.addWidget(self.phase_linewidth_spin)
        
        controls_layout.addWidget(linewidth_group)
        
        # Create turns and current controls group (horizontal layout)
        params_group = QGroupBox("MMF Parameters")
        params_group.setMinimumWidth(240)  # Increased from 180 to accommodate Wt control
        params_layout = QHBoxLayout(params_group)  # Changed from QVBoxLayout to QHBoxLayout
        params_layout.setSpacing(6)  # Reduced spacing
        
        # Number of turns control
        turns_label = QLabel("N:")  # Shortened label
        self.turns_spin = QSpinBox()
        self.turns_spin.setMinimum(1)
        self.turns_spin.setMaximum(1000)
        self.turns_spin.setValue(204)  # Changed from 30 to 204
        self.turns_spin.setStyleSheet(spinbox_style)
        self.turns_spin.valueChanged.connect(self.update_turns)
        params_layout.addWidget(turns_label)
        params_layout.addWidget(self.turns_spin)
        
        # Current control
        current_label = QLabel("I:")  # Shortened label
        self.current_spin = QDoubleSpinBox()  # Keep as QDoubleSpinBox
        self.current_spin.setMinimum(0.1)
        self.current_spin.setMaximum(1000.0)
        self.current_spin.setValue(2.8)  # Changed from 20 to 2.8
        self.current_spin.setDecimals(3)  # Keep 3 decimal places
        self.current_spin.setSuffix(" A")
        self.current_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 4px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 70px;
            }
            QDoubleSpinBox:hover {
                background-color: #3d3d3d;
                border: 1px solid #555555;
            }
            QDoubleSpinBox:focus {
                background-color: #3d3d3d;
                border: 1px solid #0078d4;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #444444;
                border: none;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #555555;
            }
            QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {
                color: #ffffff;
                width: 8px;
                height: 8px;
            }
        """)
        self.current_spin.valueChanged.connect(self.update_current)
        params_layout.addWidget(current_label)
        params_layout.addWidget(self.current_spin)
        
        # Add "A" suffix label after the input
        current_suffix_label = QLabel("A")
        current_suffix_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        params_layout.addWidget(current_suffix_label)
        
        # Wt angle control
        wt_label = QLabel("Wt:")
        self.wt_spin = QSpinBox()
        self.wt_spin.setMinimum(0)
        self.wt_spin.setMaximum(360)
        self.wt_spin.setValue(90)  # Default 90 degrees
        self.wt_spin.setSuffix("°")
        self.wt_spin.setStyleSheet(spinbox_style)
        self.wt_spin.valueChanged.connect(self.update_wt_angle)
        params_layout.addWidget(wt_label)
        params_layout.addWidget(self.wt_spin)
        
        controls_layout.addWidget(params_group)

        # Create slot arc angle control group
        slot_arc_group = QGroupBox("Slot Arc Angle")
        slot_arc_group.setMinimumWidth(140)  # Reduced from 150
        slot_arc_layout = QHBoxLayout(slot_arc_group)
        slot_arc_layout.setSpacing(10)
        
        slot_arc_label = QLabel("Angle:")
        self.slot_arc_spin = QDoubleSpinBox()
        self.slot_arc_spin.setMinimum(0.5)
        self.slot_arc_spin.setSingleStep(0.5)
        self.slot_arc_spin.setValue(5)  # Initial value, will be updated dynamically
        self.slot_arc_spin.setSuffix("°")
        self.slot_arc_spin.setDecimals(2)  # Changed to 2 decimal places for formula precision
        self.slot_arc_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 4px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 70px;
            }
            QDoubleSpinBox:hover {
                background-color: #3d3d3d;
                border: 1px solid #555555;
            }
            QDoubleSpinBox:focus {
                background-color: #3d3d3d;
                border: 1px solid #0078d4;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background-color: #444444;
                border: none;
                width: 16px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #555555;
            }
            QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow {
                color: #ffffff;
                width: 8px;
                height: 8px;
            }
        """)
        self.slot_arc_spin.valueChanged.connect(self.update_slot_arc)
        slot_arc_layout.addWidget(slot_arc_label)
        slot_arc_layout.addWidget(self.slot_arc_spin)
        
        controls_layout.addWidget(slot_arc_group)
        
        # Add reset button
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_controls)
        reset_btn.setMinimumWidth(80)  # Reduced from 100
        reset_btn.setMinimumHeight(35)  # Reduced from 40
        controls_layout.addWidget(reset_btn)
        
        # Add save plot button
        save_plot_btn = QPushButton("Save Plot")
        save_plot_btn.clicked.connect(self.save_plot)
        save_plot_btn.setMinimumWidth(90)  # Reduced from 120
        save_plot_btn.setMinimumHeight(35)  # Reduced from 40
        controls_layout.addWidget(save_plot_btn)
        
        # Add export tooth data button
        export_tooth_btn = QPushButton("Export Data")  # Shortened text
        export_tooth_btn.clicked.connect(self.export_tooth_data)
        export_tooth_btn.setMinimumWidth(100)  # Reduced from 140
        export_tooth_btn.setMinimumHeight(35)  # Reduced from 40
        controls_layout.addWidget(export_tooth_btn)

        # Add Resultant(Wt) animation button
        resultant_anim_btn = QPushButton("Resultant(Wt)")
        resultant_anim_btn.clicked.connect(self.show_resultant_animation)
        resultant_anim_btn.setMinimumWidth(110)
        resultant_anim_btn.setMinimumHeight(35)
        controls_layout.addWidget(resultant_anim_btn)

        # Add Harmonics Analysis button
        harmonics_btn = QPushButton("Harmonics")
        harmonics_btn.clicked.connect(self.show_harmonics_window)
        harmonics_btn.setMinimumWidth(100)
        harmonics_btn.setMinimumHeight(35)
        controls_layout.addWidget(harmonics_btn)

        # Add center spacer to push matrix button to the right
        center_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        controls_layout.addItem(center_spacer)
        
        # Add matrix button on the right
        matrix_btn = QPushButton("Matrix")
        matrix_btn.clicked.connect(self.show_matrix_window)
        matrix_btn.setMinimumWidth(90)  # Reduced from 120
        matrix_btn.setMinimumHeight(35)  # Reduced from 40
        controls_layout.addWidget(matrix_btn)

        # Add control panel to main layout
        layout.addWidget(control_panel)
    
    def _create_phase_checkboxes(self, num_phases):
        """Create phase checkboxes dynamically based on number of phases"""
        # Clear existing checkboxes (except resultant)
        for phase, cb in list(self.phase_checkboxes.items()):
            cb.setParent(None)
            cb.deleteLater()
        self.phase_checkboxes.clear()
        
        # Generate phase names A, B, C, D, ...
        phase_names = [chr(65 + i) for i in range(num_phases)]  # 65 = 'A' in ASCII
        
        # Create checkboxes
        for phase in phase_names:
            cb = QCheckBox(f"Phase {phase}")
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_plot)
            self.phase_checkboxes[phase] = cb
            # Insert before the resultant checkbox
            self.phase_group_layout.insertWidget(len(self.phase_checkboxes) - 1, cb)
    
    def update_slot_arc(self):
        """Update the slot arc angle in the MMF calculation engine and refresh plot"""
        new_slot_arc = self.slot_arc_spin.value()
        self.mmf_calculator.update_slot_arc(new_slot_arc)
        self.update_plot()

    def update_turns(self):
        """Update the number of turns in the MMF calculation engine and refresh plot"""
        new_turns = self.turns_spin.value()
        self.mmf_calculator.update_turns(new_turns)
        self.update_plot()

    def update_current(self):
        """Update the current in the MMF calculation engine and refresh plot"""
        new_current = self.current_spin.value()
        self.mmf_calculator.update_current(new_current)
        self.update_plot()

    def update_wt_angle(self):
        """Update the Wt angle in the MMF calculation engine and refresh plot"""
        new_wt = self.wt_spin.value()
        self.mmf_calculator.update_wt_angle(new_wt)
        self.update_plot()

    def update_matrix(self, winding_pattern, is_double_layer, poles):
        """
        Update the connection matrix using parameters from the main GUI
        Gets the matrix from the parent's StatorDrawing winding object
        """
        # Get the matrix from the winding object
        if hasattr(self.parent, 'stator_drawing') and self.parent.stator_drawing.winding_obj:
            if is_double_layer:
                self.matrix = self.parent.stator_drawing.get_double_layer_matrix()
            else:
                # For single layer, get m×Q matrix
                matrices = self.parent.stator_drawing.winding_obj.get_slot_matrices(normalize=True)
                self.matrix = np.array(matrices) if matrices else None
        else:
            self.matrix = None
        
        # Detect number of phases and update checkboxes
        if self.matrix is not None:
            if is_double_layer:
                # Double layer: matrix shape is 2m×Q
                num_phases = self.matrix.shape[0] // 2
            else:
                # Single layer: matrix shape is m×Q
                num_phases = self.matrix.shape[0]
            
            # Update phase checkboxes if phase count changed
            if len(self.phase_checkboxes) != num_phases:
                self._create_phase_checkboxes(num_phases)
        
        # Update the calculation engine with new matrix
        if self.matrix is not None:
            self.mmf_calculator.update_matrix_from_parameters(self.matrix, is_double_layer)
        
        # Update slot arc maximum and default value based on number of slots
        if self.matrix is not None:
            n_slots = self.matrix.shape[1]
            max_slot_arc = (360 / n_slots) - 0.5
            self.slot_arc_spin.setMaximum(max_slot_arc)
            
            # Set slot arc to dynamic formula: 360 / (2 * number of slots)
            dynamic_slot_arc = 360 / (2 * n_slots)
            if dynamic_slot_arc <= max_slot_arc:
                self.slot_arc_spin.setValue(dynamic_slot_arc)
            else:
                self.slot_arc_spin.setValue(max_slot_arc)
            
            # Set current values from UI controls
            self.mmf_calculator.update_slot_arc(self.slot_arc_spin.value())
            self.mmf_calculator.update_turns(self.turns_spin.value())
            self.mmf_calculator.update_current(self.current_spin.value())
            self.mmf_calculator.update_wt_angle(self.wt_spin.value())

        # Update the plot
        self.update_plot()
    
    def update_plot(self):
        """Update the plot based on current checkbox selections"""
        self.ax.clear()
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        # Get selected phases
        selected_phases = [ph for ph, cb in self.phase_checkboxes.items() if cb.isChecked()]
        
        # Always plot phases (sum for double layer, direct for single layer)
        self.plot_selected_phases(selected_phases)
        
        self.ax.set_xlabel('Mechanical Angle [degrees]', color='black')
        self.ax.set_ylabel('MMF [A·t]', color='black')
        self.ax.set_title('MMF Distribution', color='black')
        self.ax.grid(True, color='black', alpha=0.3)
        self.ax.tick_params(colors='black')
        
        # Set x-axis limits to always show 0 to 360 degrees
        self.ax.set_xlim(0, 360)
        
        # Only add legend if there are items to show
        if len(self.ax.get_lines()) > 0:
            self.ax.legend(facecolor='white', edgecolor='black', labelcolor='black')
            
        self.canvas.draw()
    
    def plot_selected_phases(self, selected_phases):
        """Plot selected phases (always sum for double layer)"""
        # Generate dynamic styles for all phases
        styles = self._generate_phase_styles(len(self.phase_checkboxes))
        phase_linewidth = self.phase_linewidth_spin.value()
        
        # Check if we're in double layer mode
        if self.matrix is not None:
            is_double_layer = (self.matrix.shape[0] == 2 * len(self.phase_checkboxes))
        else:
            is_double_layer = False
        layer_type = 'sum' if is_double_layer else None
        
        for ph in selected_phases:
            angles, values = self.mmf_calculator.get_profile_data(ph, layer_type)
            if angles is not None:
                col, ls = styles[ph]
                self.ax.plot(angles, values, label=f'Phase {ph}', color=col, 
                           linestyle=ls, linewidth=phase_linewidth)
        
        # Plot resultant if selected
        if self.resultant_checkbox.isChecked():
            angles, values = self.mmf_calculator.get_profile_data('resultant')
            if angles is not None:
                wt_angle = self.wt_spin.value()
                self.ax.plot(angles, values, label=f'Resultant', 
                           color='black', linestyle='-', linewidth=phase_linewidth+1)
    
    def _generate_phase_styles(self, num_phases):
        """Generate matplotlib colors for any number of phases"""
        styles = {}
        phase_names = [chr(65 + i) for i in range(num_phases)]  # A, B, C, D, ...
        
        # Pre-defined colors matching StatorDrawing
        if num_phases == 2:
            colors = ['red', 'blue']
        elif num_phases == 3:
            colors = ['red', 'blue', 'green']
        elif num_phases == 4:
            colors = ['red', 'green', 'blue', 'yellow']
        elif num_phases == 5:
            colors = ['red', 'green', 'blue', 'yellow', 'magenta']
        elif num_phases == 6:
            colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
        else:
            # Generate colors using HSV for 7+ phases
            import colorsys
            colors = []
            for i in range(num_phases):
                hue = i / num_phases
                rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                colors.append(rgb)
        
        for i, phase in enumerate(phase_names):
            styles[phase] = (colors[i], '-')
        
        return styles
    
    def show_matrix_window(self):
        """Show connection matrix in a dialog window"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Connection Matrix")
        dialog.setStyle(QStyleFactory.create("Fusion"))
        dialog.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #dddddd;
                gridline-color: transparent;
                border: none;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #dddddd;
                padding: 6px;
                border: none;
            }
            QTableWidget::item {
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #1e1e1e;
                color: white;
            }
            QTableCornerButton::section {
                background-color: #1c1c1c;
                border: none;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                background: #1e1e1e;
                border: none;
                height: 16px;
                width: 16px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background: #444444;
                border-radius: 6px;
                min-width: 25px;
                min-height: 25px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        rows, cols = self.matrix.shape

        if rows == 6:
            phases = ["A_top", "B_top", "C_top", "A_bot", "B_bot", "C_bot"]
        else:
            phases = ["A", "B", "C"]

        table.setRowCount(rows)
        table.setColumnCount(cols)
        table.setVerticalHeaderLabels(phases)
        table.setHorizontalHeaderLabels([str(i + 1) for i in range(cols)])

        table.setShowGrid(True)
        table.setWordWrap(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectItems)
        table.setSelectionMode(QTableWidget.SingleSelection)

        font = table.horizontalHeader().font()
        font.setPointSize(12)
        table.horizontalHeader().setFont(font)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        table.horizontalHeader().setFixedHeight(50)
        table.verticalHeader().setFixedWidth(70)
        table.verticalHeader().setDefaultSectionSize(43)
        table.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignTop)
        table.verticalHeader().setStretchLastSection(False)

        table.setFrameStyle(QFrame.NoFrame)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        for row in range(rows):
            for col in range(cols):
                item = QTableWidgetItem(str(self.matrix[row][col]))
                table.setItem(row, col, item)

        save_btn = QPushButton("Save as Excel")
        save_btn.clicked.connect(lambda: self._save_matrix_to_excel(self.matrix))

        layout.addWidget(table)
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.resize(1920, 450 if rows == 6 else 350)
        dialog.exec_()

    def _save_matrix_to_excel(self, matrix):
        """Save connection matrix to Excel file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Matrix", "connection_matrix.xlsx", "Excel Files (*.xlsx)")
        if filename:
            df = pd.DataFrame(matrix)
            df.to_excel(filename, index=False, header=False)
            print(f"Matrix saved to {filename}")

    def reset_controls(self):
        """Reset all controls to their default configuration"""
        # Reset phase checkboxes
        for cb in self.phase_checkboxes.values():
            cb.setChecked(True)
        
        # Reset resultant checkbox
        self.resultant_checkbox.setChecked(False)
        
        # Reset linewidth spinbox
        self.phase_linewidth_spin.setValue(2)
        
        # Reset slot arc angle based on current number of slots using dynamic formula
        if self.matrix is not None:
            n_slots = self.matrix.shape[1]
            dynamic_slot_arc = 360 / (2 * n_slots)
            max_slot_arc = self.slot_arc_spin.maximum()
            self.slot_arc_spin.setValue(min(dynamic_slot_arc, max_slot_arc))
        else:
            # Default to 36 slots if no matrix
            default_slot_arc = 360 / (2 * 36)
            self.slot_arc_spin.setValue(default_slot_arc)
        
        # Reset turns and current
        self.turns_spin.setValue(204)
        self.current_spin.setValue(2.8)
        
        # Reset Wt angle
        self.wt_spin.setValue(90)
        
        # Update the plot with default settings
        self.update_plot()

    def save_plot(self):
        """Save the current plot with auto-generated filename"""
        try:
            # Get number of slots and pair of poles
            n_slots = self.matrix.shape[1] if self.matrix is not None else 0
            pair_of_poles_spin = getattr(self.parent, 'poles_spin', None)
            pair_of_poles_value = pair_of_poles_spin.value() if pair_of_poles_spin else 0
            
            # Get selected phases
            selected_phases = [ph for ph, cb in self.phase_checkboxes.items() if cb.isChecked()]
            phases_str = "".join(sorted(selected_phases)) if selected_phases else "no_phases"
            
            # Add resultant to filename if selected
            if self.resultant_checkbox.isChecked():
                phases_str += "_resultant"
            
            # Determine layer type for filename
            num_phases = len(self.phase_checkboxes)
            is_double_layer = (self.matrix.shape[0] == 2 * num_phases) if self.matrix is not None else False
            layer_str = "double_layer_sum" if is_double_layer else "single_layer"
            
            # Generate filename: numberofslots_numberofpairpoles_phases_layertype
            filename = f"{n_slots}slots_{pair_of_poles_value}pairpoles_{phases_str}_{layer_str}.png"
            
            # Open file dialog with suggested filename
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Plot", 
                filename, 
                "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
            )
            
            if save_path:
                # Save the plot
                self.fig.savefig(save_path, dpi=300, bbox_inches='tight', 
                               facecolor='white', edgecolor='none')
                print(f"Plot saved to: {save_path}")
                
        except Exception as e:
            print(f"Error saving plot: {e}")
    
    def export_tooth_data(self):
        """Export tooth MMF values to Excel file"""
        try:
            # Update the MMF calculator with current UI Wt value before exporting
            current_wt_from_ui = self.wt_spin.value()
            original_wt = self.mmf_calculator.Wt
            self.mmf_calculator.Wt = current_wt_from_ui
            
            # Get tooth data from calculation engine with updated Wt
            tooth_data = self.mmf_calculator.get_tooth_mmf_data()
            
            # Restore original Wt value
            self.mmf_calculator.Wt = original_wt
            
            if tooth_data is None:
                print("No tooth data available for export")
                return
            
            # Generate filename
            n_slots = self.matrix.shape[1] if self.matrix is not None else 0
            pair_of_poles_spin = getattr(self.parent, 'poles_spin', None)
            pair_of_poles_value = pair_of_poles_spin.value() if pair_of_poles_spin else 0
            
            num_phases = len(self.phase_checkboxes)
            is_double_layer = (self.matrix.shape[0] == 2 * num_phases) if self.matrix is not None else False
            layer_str = "double_layer" if is_double_layer else "single_layer"
            
            # Include Wt value in filename with pair of poles
            filename = f"{n_slots}slots_{pair_of_poles_value}pairpoles_resultant_tooth_mmf_Wt{current_wt_from_ui}deg_{layer_str}.xlsx"
            
            # Open file dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Tooth Data", 
                filename, 
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if save_path:
                # Create DataFrame with resultant MMF data including Wt information
                resultant_data = {
                    'Tooth_Number': list(range(1, n_slots + 1)),
                    'Resultant_Tooth_MMF': tooth_data['Resultant']['tooth_mmf'],
                    'Wt_Angle_Degrees': [current_wt_from_ui] * n_slots  # Add Wt value for reference
                }
                
                df = pd.DataFrame(resultant_data)
                df.to_excel(save_path, index=False)
                
                print(f"Tooth data exported to: {save_path} (Wt = {current_wt_from_ui}°)")
                
        except Exception as e:
            print(f"Error exporting tooth data: {e}")

    def show_resultant_animation(self):
        """Show the resultant animation window"""
        if self.matrix is None:
            print("No matrix available for animation")
            return
            
        # Create and show the animation window
        self.animation_window = ResultantAnimationWindow(self, self.mmf_calculator)
        self.animation_window.show()

    def show_harmonics_window(self):
        """Show the harmonics analysis window"""
        if self.matrix is None:
            print("No matrix available for harmonics analysis")
            return
        
        # Create and show the harmonics window
        self.harmonics_window = HarmonicsWindow(self, self.mmf_calculator)
        
        # Populate phase checkboxes with current phases
        phase_layout = self.harmonics_window.phase_checkboxes
        for phase in self.phase_checkboxes.keys():
            cb = QCheckBox(f'Phase {phase}')
            cb.setChecked(False)  # Start with phases unchecked
            cb.setStyleSheet("QCheckBox { color: #ffffff; }")
            cb.stateChanged.connect(self.harmonics_window.perform_analysis)
            self.harmonics_window.phase_checkboxes[phase] = cb
            # Get the phase group layout and add checkbox before the last stretch
            phase_group = self.harmonics_window.findChild(QGroupBox, "Phases to Analyze")
            if phase_group is None:
                # Find it by iterating through children
                for child in self.harmonics_window.children():
                    if isinstance(child, QGroupBox) and "Phases" in child.title():
                        phase_group = child
                        break
            if phase_group:
                phase_group.layout().insertWidget(len(self.harmonics_window.phase_checkboxes), cb)
        
        self.harmonics_window.show()


class HarmonicsWindow(QDialog):
    """Window for harmonic analysis of MMF waveforms"""
    def __init__(self, parent=None, mmf_calculator=None):
        super().__init__(parent)
        self.parent = parent
        self.mmf_calculator = mmf_calculator
        
        self.setWindowTitle("MMF Harmonic Analysis")
        self.setGeometry(100, 100, 1400, 900)
        
        self._init_ui()
        self.perform_analysis()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls for analysis parameters
        controls_layout = QHBoxLayout()
        
        # Phase selection with checkboxes
        phase_group = QGroupBox("Phases to Analyze")
        phase_group.setStyleSheet("QGroupBox { color: #ffffff; font-size: 14px; }")
        phase_layout = QHBoxLayout(phase_group)
        
        # Create checkboxes for phases (will be populated when window is shown)
        self.phase_checkboxes = {}
        
        # Resultant checkbox
        self.resultant_checkbox = QCheckBox("Resultant")
        self.resultant_checkbox.setChecked(True)
        self.resultant_checkbox.setStyleSheet("QCheckBox { color: #ffffff; }")
        self.resultant_checkbox.stateChanged.connect(self.perform_analysis)
        phase_layout.addWidget(self.resultant_checkbox)
        
        phase_group.setLayout(phase_layout)
        controls_layout.addWidget(phase_group)
        
        # Number of harmonics
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
        
        # Left side: Bar chart of harmonics
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
        """Perform harmonic analysis and update displays for all selected phases"""
        nu_max = self.nu_max_spin.value()
        
        # Get all selected phases
        selected_phases = []
        if self.resultant_checkbox.isChecked():
            selected_phases.append(('resultant', 'Resultant'))
        
        for phase_name, cb in self.phase_checkboxes.items():
            if cb.isChecked():
                selected_phases.append((phase_name, f'Phase {phase_name}'))
        
        if not selected_phases:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'No phase selected', ha='center', va='center', 
                        fontsize=14, color='white')
            self.canvas.draw()
            self.summary_text.setPlainText("No phase selected for analysis")
            return
        
        print(f"Performing harmonic analysis for {[p[1] for p in selected_phases]} with nu_max={nu_max}")
        
        # Collect harmonics data for all selected phases
        all_harmonics_data = {}
        for phase, label in selected_phases:
            harmonics_data = self.mmf_calculator.calculate_harmonics(
                D=1.0, 
                nu_max=nu_max, 
                phase=phase
            )
            if harmonics_data is not None:
                all_harmonics_data[label] = harmonics_data
        
        if not all_harmonics_data:
            print("ERROR: No harmonics data available")
            return
        
        # Store for export
        self.all_harmonics_data = all_harmonics_data
        
        # Update plot with all selected phases
        self.plot_harmonics_multi(all_harmonics_data)
        
        # Update summary text with all phases
        summary = ""
        for label, data in all_harmonics_data.items():
            phase = 'resultant' if label == 'Resultant' else label.split()[-1]
            phase_summary = self.mmf_calculator.get_harmonic_summary(
                D=1.0, 
                nu_max=nu_max, 
                phase=phase
            )
            summary += f"\n{'='*80}\n{label}\n{'='*80}\n{phase_summary}\n"
        
        self.summary_text.setPlainText(summary)
        
    def plot_harmonics_multi(self, all_harmonics_data):
        """Plot harmonic bar chart for multiple phases"""
        self.ax.clear()
        
        if not all_harmonics_data:
            return
        
        # Generate colors for each phase
        num_phases = len(all_harmonics_data)
        if num_phases == 1:
            phase_colors = ['#2E86AB']
        else:
            # Use distinct colors for multiple phases
            import colorsys
            phase_colors = []
            for i in range(num_phases):
                hue = i / num_phases
                rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
                phase_colors.append(rgb)
        
        # Get all unique harmonics
        all_harmonics = set()
        for data in all_harmonics_data.values():
            all_harmonics.update(data['harmonics'])
        all_harmonics = sorted(all_harmonics)
        
        # Prepare data for grouped bar chart
        bar_width = 0.8 / num_phases
        x_positions = np.arange(len(all_harmonics))
        
        for idx, (label, data) in enumerate(all_harmonics_data.items()):
            harmonics = data['harmonics']
            percentages = data['percentage']
            
            # Map percentages to all_harmonics positions
            y_values = []
            for h in all_harmonics:
                if h in harmonics:
                    h_idx = harmonics.index(h)
                    y_values.append(percentages[h_idx])
                else:
                    y_values.append(0)
            
            # Plot bars
            offset = (idx - num_phases/2 + 0.5) * bar_width
            self.ax.bar(x_positions + offset, y_values, bar_width, 
                       label=label, color=phase_colors[idx], alpha=0.8, edgecolor='white', linewidth=0.5)
        
        # Set white background
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        self.ax.set_xlabel('Harmonic Order', fontsize=12, color='black')
        self.ax.set_ylabel('Magnitude (% of Fundamental)', fontsize=12, color='black')
        self.ax.set_title(f'MMF Harmonic Spectrum Comparison', 
                         fontsize=14, color='black', fontweight='bold')
        self.ax.set_xticks(x_positions)
        self.ax.set_xticklabels([str(h) for h in all_harmonics])
        self.ax.legend(facecolor='white', edgecolor='black', labelcolor='black')
        self.ax.grid(True, alpha=0.3, color='black', axis='y')
        self.ax.tick_params(colors='black')
        
        self.canvas.draw()
    
    def export_harmonics(self):
        """Export harmonics data to CSV file for all selected phases"""
        if not hasattr(self, 'all_harmonics_data') or not self.all_harmonics_data:
            print("No harmonics data to export")
            return
        
        try:
            # Generate filename
            filename = f"harmonics_analysis.csv"
            
            # Open file dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Harmonics Data", 
                filename, 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if save_path:
                # Get all unique harmonics
                all_harmonics = set()
                for data in self.all_harmonics_data.values():
                    all_harmonics.update(data['harmonics'])
                all_harmonics = sorted(all_harmonics)
                
                # Create DataFrame with columns for each phase
                export_data = {'Harmonic_Order': all_harmonics}
                
                for label, data in self.all_harmonics_data.items():
                    harmonics = data['harmonics']
                    
                    # Create columns for this phase
                    col_prefix = label.replace(' ', '_')
                    
                    # Map data to all_harmonics
                    amplitude = []
                    percentage = []
                    phase_angle = []
                    a_coef = []
                    b_coef = []
                    
                    for h in all_harmonics:
                        if h in harmonics:
                            h_idx = harmonics.index(h)
                            amplitude.append(data['mmf_amplitude'][h_idx])
                            percentage.append(data['percentage'][h_idx])
                            phase_angle.append(data['phase'][h_idx])
                            a_coef.append(data['a'][h_idx])
                            b_coef.append(data['b'][h_idx])
                        else:
                            amplitude.append(0)
                            percentage.append(0)
                            phase_angle.append(0)
                            a_coef.append(0)
                            b_coef.append(0)
                    
                    export_data[f'{col_prefix}_Amplitude'] = amplitude
                    export_data[f'{col_prefix}_Percentage'] = percentage
                    export_data[f'{col_prefix}_Phase_rad'] = phase_angle
                    export_data[f'{col_prefix}_a_coef'] = a_coef
                    export_data[f'{col_prefix}_b_coef'] = b_coef
                
                df = pd.DataFrame(export_data)
                df.to_csv(save_path, index=False)
                print(f"Harmonics data exported to: {save_path}")
                
        except Exception as e:
            print(f"Error exporting harmonics data: {e}")



def setup_connection_matrix_tab(self):
    """
    Setup the connection matrix tab with the improved architecture
    """
    self.connection_tab = ConnectionMatrixTab(self)
    layout = QVBoxLayout()
    layout.addWidget(self.connection_tab)
    self.tab_connection.setLayout(layout)

    # Force initial update on tab setup
    actual_poles = self.poles_spin.value() * 2  # Convert pair of poles to actual poles
    self.connection_tab.update_matrix(
        self.stator_drawing.winding_pattern,
        self.stator_drawing.is_double_layer,
        actual_poles
    )

    # Update the matrix when switching to the tab
    def update_connection_tab():
        """
        Update the connection matrix and plots when switching to this tab.
        """
        actual_poles = self.poles_spin.value() * 2  # Convert pair of poles to actual poles
        self.connection_tab.update_matrix(
            self.stator_drawing.winding_pattern,
            self.stator_drawing.is_double_layer,
            actual_poles
        )

    # Connect tab change event to update function
    self.tabs.currentChanged.connect(
        lambda index: update_connection_tab() if self.tabs.tabText(index) == "MMF Curves" else None
    )
