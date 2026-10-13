from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QRadioButton,
                             QButtonGroup, QPushButton, QFrame, QScrollArea, QSplitter, QSizePolicy, QFileDialog,
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from StatorDrawing import StatorDrawing
from explanation import check_winding_feasibility, generate_winding_explanation
import numpy as np
import pandas as pd

def update_span_for_double_layer(self):
    """Update span value to pole pitch when in double layer mode"""
    if self.double_layer.isChecked():
        actual_poles = self.poles_spin.value() * 2  # Convert pair of poles to actual poles
        pole_pitch = self.slots_spin.value() // actual_poles
        self.span_spin.setValue(pole_pitch)

def check_feasibility_only(self):
    """Check feasibility and update UI without generating winding"""
    slots = self.slots_spin.value()
    pair_of_poles = self.poles_spin.value()
    actual_poles = pair_of_poles * 2
    coil_span = slots // actual_poles if self.single_layer.isChecked() else self.span_spin.value()
    is_double_layer = self.double_layer.isChecked()
    phases = self.phases_spin.value()
    
    feasible, messages, q, single_layer_feasible = check_winding_feasibility(slots, actual_poles, phases)
    
    # Update labels
    self.slots_per_pole_label.setText(f"Slots per pole: {slots / actual_poles:.2f}")
    self.slots_per_phase_label.setText(f"Slots per pole per phase (q): {q}")
    self.winding_type_label.setText("Winding type: " + ("Fractional slot winding" if q.denominator > 1 else "Integer slot winding"))
    
    # Update explanation text with current configuration
    self.explanation_text.setText(generate_winding_explanation(slots, actual_poles, coil_span, is_double_layer, q, single_layer_feasible, phases))
    
    # Update feasibility display
    if feasible:
        self.feasibility_label.setText("Feasibility: ✓ FEASIBLE")
        self.feasibility_label.setStyleSheet("color: green")
    else:
        self.feasibility_label.setText(f"Feasibility: ✗ NOT FEASIBLE\n" + "\n".join(messages))
        self.feasibility_label.setStyleSheet("color: red")
    
    # Enable/disable single layer based on feasibility
    self.single_layer.setEnabled(single_layer_feasible)
    if not single_layer_feasible and self.single_layer.isChecked():
        # If single layer is selected but not feasible, switch to double layer
        self.double_layer.setChecked(True)
    
    # Add single layer feasibility warning
    if feasible and not single_layer_feasible:
        current_text = self.feasibility_label.text()
        self.feasibility_label.setText(current_text + "\n⚠ Single layer not feasible")
        self.feasibility_label.setStyleSheet("color: #ffa500")  # Orange

def setup_main_tab(self):
    # Bind the functions to self
    self.update_span_for_double_layer = lambda: update_span_for_double_layer(self)
    self.check_feasibility_only = lambda: check_feasibility_only(self)
    self.show_connection_matrix = lambda: show_connection_matrix(self)
    
    # Define spinbox styling (matching MMF_Harmonics_tab style)
    spinbox_style = """
        QSpinBox {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 5px;
            font-size: 13px;
        }
    """
    
    self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #dddddd;
                font-family: Segoe UI, sans-serif;
                font-size: 14px;
            }

            QLabel {
                font-size: 14px;
            }

            QRadioButton, QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #444444;
                padding: 4px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #3d3d3d;
            }

            QFrame {
                background-color: #262626;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px;
            }

            QGroupBox {
                border: 1px solid #444;
                margin-top: 6px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }

            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1e1e1e;
            }

            QTabBar::tab {
                min-width: 250px;           /* minimum width for label to fit */
                padding: 10px;         /* vertical and horizontal padding */
                font-size: 14px;
                background-color: #2d2d2d;
                color: #dddddd;
                border: 1px solid #444444;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 1px;
            }


            QTabBar::tab:selected {
                background: #3d3d3d;
                font-weight: bold;
            }

            QTabBar::tab:hover {
                background: #444;
            }
        """)

    main_splitter = QSplitter(Qt.Horizontal)
    main_layout = QHBoxLayout(self.tab_main)
    main_layout.addWidget(main_splitter)

    left_widget = QWidget()
    left_layout = QHBoxLayout(left_widget)

    control_widget = QWidget()
    control_widget.setFixedWidth(285)
    control_layout = QVBoxLayout(control_widget)

    self.slots_spin = QSpinBox()
    self.slots_spin.setRange(6, 244)
    self.slots_spin.setValue(36)  # Changed from 24 to 36
    self.slots_spin.setStyleSheet(spinbox_style)
    self.slots_spin.valueChanged.connect(self.check_feasibility_only)
    self.slots_spin.valueChanged.connect(lambda: self.span_spin.setMaximum(self.slots_spin.value()))
    self.slots_spin.valueChanged.connect(lambda: self.poles_spin.setMaximum(self.slots_spin.value()))
    self.slots_spin.valueChanged.connect(self.update_span_for_double_layer)
    self.slots_spin.valueChanged.connect(self.update_winding)  # Auto-update

    self.poles_spin = QSpinBox()
    self.poles_spin.setRange(1, self.slots_spin.value())  # Range for pair of poles - allows fractional slot windings
    self.poles_spin.setSingleStep(1)  # Change step to 1 for pair of poles
    self.poles_spin.setValue(2)  # Default to 2 pair of poles (4 actual poles)
    self.poles_spin.setStyleSheet(spinbox_style)
    self.poles_spin.valueChanged.connect(self.check_feasibility_only)
    self.poles_spin.valueChanged.connect(self.update_span_for_double_layer)
    self.poles_spin.valueChanged.connect(self.update_winding)  # Auto-update

    self.span_spin = QSpinBox()
    self.span_spin.setRange(1, self.slots_spin.value())
    self.span_spin.setValue(self.slots_spin.value() // self.poles_spin.value())
    self.span_spin.setStyleSheet(spinbox_style)
    self.span_spin.valueChanged.connect(self.check_feasibility_only)  # Update explanation when span changes
    self.span_spin.valueChanged.connect(self.update_winding)  # Auto-update

    self.single_layer = QRadioButton("Single Layer")
    self.double_layer = QRadioButton("Double Layer")
    self.double_layer.setChecked(True)
    self.single_layer.toggled.connect(self.check_feasibility_only)  # Update explanation when toggled
    self.single_layer.toggled.connect(self.handle_single_layer_toggle)
    self.single_layer.toggled.connect(self.update_winding)  # Auto-update

    winding_group = QButtonGroup()
    winding_group.addButton(self.single_layer)
    winding_group.addButton(self.double_layer)

    # Custom spinbox for phases: minimum 2, no practical upper cap
    self.phases_spin = QSpinBox()
    self.phases_spin.setRange(2, 999)
    self.phases_spin.setValue(3)
    self.phases_spin.setStyleSheet(spinbox_style)
    
    # Track if we're programmatically changing the value
    self._updating_phases = False
    self._last_valid_phases = 3
    
    # Enforce valid phase values: allow 2 and any odd ≥ 3
    def enforce_valid_phases(value):
        if self._updating_phases:
            return
        # Valid if 2-phase or odd number ≥ 3
        is_valid = (value == 2) or (value >= 3 and (value % 2 == 1))
        if not is_valid:
            # Show warning message
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Phase Number",
                f"Phase number {value} is not supported.\n\n"
                f"Only odd phases (≥3) and 2-phase are allowed.\n"
                f"Even phases are not supported.",
                QMessageBox.Ok
            )
            
            # Revert to last valid value
            self._updating_phases = True
            self.phases_spin.setValue(self._last_valid_phases)
            self._updating_phases = False
        else:
            self._last_valid_phases = value
    
    self.phases_spin.valueChanged.connect(enforce_valid_phases)
    self.phases_spin.valueChanged.connect(self.check_feasibility_only)
    self.phases_spin.valueChanged.connect(self.update_winding)

    control_layout.addWidget(QLabel("Number of Phases:"))
    control_layout.addWidget(self.phases_spin)
    control_layout.addWidget(QLabel("Number of Slots:"))
    control_layout.addWidget(self.slots_spin)
    control_layout.addWidget(QLabel("Number of Pair of Poles:"))  # Changed label
    control_layout.addWidget(self.poles_spin)
    control_layout.addWidget(QLabel("Coil Span (slots):"))
    control_layout.addWidget(self.span_spin)
    control_layout.addWidget(QLabel("Winding Type:"))
    control_layout.addWidget(self.single_layer)
    control_layout.addWidget(self.double_layer)

    self.slots_per_pole_label = QLabel("Slots per pole: -")
    self.slots_per_phase_label = QLabel("Slots per pole per phase (q): -")
    self.winding_type_label = QLabel("Winding type: -")
    self.feasibility_label = QLabel("Feasibility: -")
    self.feasibility_label.setWordWrap(True)
    self.feasibility_label.setFixedHeight(120)
    self.feasibility_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    control_layout.addWidget(self.slots_per_pole_label)
    control_layout.addWidget(self.slots_per_phase_label)
    control_layout.addWidget(self.winding_type_label)
    control_layout.addWidget(self.feasibility_label)

    explanation_container = QWidget()
    explanation_container.setFixedWidth(400)
    explanation_layout = QVBoxLayout(explanation_container)

    self.explanation_text = QLabel()
    self.explanation_text.setWordWrap(True)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(self.explanation_text)
    explanation_layout.addWidget(scroll)

    left_layout.addWidget(control_widget)
    left_layout.addWidget(explanation_container)

    right_widget = QWidget()
    right_widget.setFixedWidth(1180)
    right_layout = QVBoxLayout(right_widget)

    drawing_container = QFrame()
    drawing_container.setStyleSheet("background-color: white;")
    drawing_layout = QVBoxLayout(drawing_container)

    self.stator_drawing = StatorDrawing()
    self.stator_drawing.setFixedSize(900, 800)
    drawing_layout.addWidget(self.stator_drawing, alignment=Qt.AlignCenter)

    # Buttons layout
    buttons_layout = QHBoxLayout()
    
    save_image_btn = QPushButton("Save Drawing")
    save_image_btn.setStyleSheet("background-color: #2d2d2d; color: white;")
    save_image_btn.clicked.connect(self.save_stator_image)
    buttons_layout.addWidget(save_image_btn)
    
    show_matrix_btn = QPushButton("Show Connection Matrix")
    show_matrix_btn.setStyleSheet("background-color: #2d2d2d; color: white;")
    show_matrix_btn.clicked.connect(self.show_connection_matrix)
    buttons_layout.addWidget(show_matrix_btn)
    
    buttons_layout.addStretch()
    drawing_layout.addLayout(buttons_layout)

    right_layout.addWidget(drawing_container)

    main_splitter.addWidget(left_widget)
    main_splitter.addWidget(right_widget)
    main_splitter.setCollapsible(0, False)
    main_splitter.setCollapsible(1, False)
    left_widget.setFixedWidth(710)
    right_widget.setFixedWidth(1120)
    main_splitter.setHandleWidth(1)

    self.update_winding()

def update_winding(self):
    slots = self.slots_spin.value()
    pair_of_poles = self.poles_spin.value()
    actual_poles = pair_of_poles * 2  # Convert to actual poles for calculations
    coil_span = slots // actual_poles if self.single_layer.isChecked() else self.span_spin.value()
    is_double_layer = self.double_layer.isChecked()
    phases = self.phases_spin.value()

    feasible, messages, q, single_layer_feasible = check_winding_feasibility(slots, actual_poles, phases)

    self.slots_per_pole_label.setText(f"Slots per pole: {slots / actual_poles:.2f}")
    self.slots_per_phase_label.setText(f"Slots per pole per phase (q): {q}")
    self.winding_type_label.setText("Winding type: " + ("Fractional slot winding" if q.denominator > 1 else "Integer slot winding"))

    # Update feasibility display
    if feasible:
        self.feasibility_label.setText("Feasibility: ✓ FEASIBLE")
        self.feasibility_label.setStyleSheet("color: green")
    else:
        self.feasibility_label.setText(f"Feasibility: ✗ NOT FEASIBLE\n" + "\n".join(messages))
        self.feasibility_label.setStyleSheet("color: red")
    
    # Enable/disable single layer based on feasibility
    self.single_layer.setEnabled(single_layer_feasible)
    if not single_layer_feasible and self.single_layer.isChecked():
        # If single layer is selected but not feasible, switch to double layer
        self.double_layer.setChecked(True)
        is_double_layer = True
    
    # Add single layer feasibility warning to feasibility label
    if feasible and not single_layer_feasible:
        current_text = self.feasibility_label.text()
        self.feasibility_label.setText(current_text + "\n⚠ Single layer not feasible for this config")
        self.feasibility_label.setStyleSheet("color: #ffa500")  # Orange

    self.explanation_text.setText(generate_winding_explanation(slots, actual_poles, coil_span, is_double_layer, q, single_layer_feasible, phases))
    self.stator_drawing.update_parameters(slots, actual_poles, coil_span, is_double_layer, phases)

    # Check for incomplete layer filling in double layer winding
    if is_double_layer and feasible:
        pattern = self.stator_drawing.winding_pattern
        incomplete_slots = []
        for i, (top, bottom) in enumerate(pattern):
            if (top is None and bottom is not None) or (top is not None and bottom is None):
                incomplete_slots.append(i + 1)
        
        if incomplete_slots:
            current_text = self.feasibility_label.text()
            warning = f"\n⚠ WARNING: {len(incomplete_slots)} slots have incomplete layer filling"
            if len(incomplete_slots) <= 10:
                warning += f"\nSlots: {', '.join(map(str, incomplete_slots))}"
            self.feasibility_label.setText(current_text + warning)
            self.feasibility_label.setStyleSheet("color: orange")

    # Update MMF and Harmonics tab with new parameters
    if hasattr(self, 'koil_harmonics_tab'):
        self.koil_harmonics_tab.update_matrix(
            self.stator_drawing.winding_pattern,
            self.stator_drawing.is_double_layer,
            actual_poles  # Pass actual poles to calculations
        )
    # Update Voltage tab analysis from winding
    if hasattr(self, 'voltage_tab'):
        try:
            self.voltage_tab.recompute_from_winding()
        except Exception:
            pass
    if hasattr(self, 'fmm_plot_widget'):
        self.fmm_plot_widget.update_matrix_from_parameters(
            self.stator_drawing.winding_pattern,
            self.stator_drawing.is_double_layer,
            actual_poles  # Pass actual poles to calculations
        )

def save_stator_image(self):
    # Generate dynamic filename based on configuration
    slots = self.slots_spin.value()
    pair_of_poles = self.poles_spin.value()
    actual_poles = pair_of_poles * 2  # Convert for calculations
    phases = self.phases_spin.value()
    winding_type = "SingleL" if self.single_layer.isChecked() else "DoubleL"  # SL = Single Layer, DL = Double Layer

    # Determine q type (fractional or integer)
    feasible, messages, q, _ = check_winding_feasibility(slots, actual_poles, phases)
    q_type = "qfrac" if q.denominator > 1 else "qint"
    
    if self.single_layer.isChecked():
        # For single layer, don't include coil span
        default_filename = f"{slots}slots_{pair_of_poles}pairpoles_{phases}phases_{winding_type}_{q_type}.png"
    else:
        # For double layer, include coil span
        coil_span = self.span_spin.value()
        default_filename = f"{slots}slots_{pair_of_poles}pairpoles_{phases}phases_{winding_type}_span{coil_span}_{q_type}.png"
    
    filename, _ = QFileDialog.getSaveFileName(self, "Save Drawing", default_filename, "PNG Files (*.png)")
    if filename:
        self.stator_drawing.save_drawing(filename)

def handle_single_layer_toggle(self):
    is_single = self.single_layer.isChecked()
    self.span_spin.setEnabled(not is_single)
    if is_single:
        self.span_spin.clear()
    else:
        # Set to pole pitch when switching to double layer
        actual_poles = self.poles_spin.value() * 2  # Convert pair of poles to actual poles
        pole_pitch = self.slots_spin.value() // actual_poles
        self.span_spin.setValue(pole_pitch)
        self.span_spin.clear()

def show_connection_matrix(self):
    """Show connection matrix in a popup dialog window"""
    if not hasattr(self.stator_drawing, 'winding_obj') or self.stator_drawing.winding_obj is None:
        QMessageBox.warning(self, "No Matrix", "No connection matrix available. Please generate a winding first.")
        return
    
    # Get the matrix from the winding object
    winding_obj = self.stator_drawing.winding_obj
    is_double_layer = self.stator_drawing.is_double_layer
    
    if is_double_layer:
        matrix = winding_obj.get_double_layer_matrix(normalize=True)
    else:
        # For single layer, get slot matrices for all phases
        matrices = winding_obj.get_slot_matrices(normalize=True)
        if matrices and len(matrices) > 0:
            # Stack matrices vertically: each row is one phase
            matrix = np.vstack(matrices)
        else:
            matrix = None
    
    if matrix is None or matrix.size == 0:
        QMessageBox.warning(self, "No Matrix", "Failed to generate connection matrix.")
        return
    
    # Normalize matrix to ensure values are -1, 0, or +1
    matrix_normalized = np.zeros_like(matrix)
    matrix_normalized[matrix > 0.01] = 1
    matrix_normalized[matrix < -0.01] = -1
    
    # Create dialog
    dialog = ConnectionMatrixDialog(matrix_normalized, is_double_layer, winding_obj.m, winding_obj.Q, self)
    dialog.exec_()

class ConnectionMatrixDialog(QDialog):
    """Dialog to display and export connection matrix"""
    def __init__(self, matrix, is_double_layer, num_phases, num_slots, parent=None):
        super().__init__(parent)
        self.matrix = matrix
        self.is_double_layer = is_double_layer
        self.num_phases = num_phases
        self.num_slots = num_slots
        
        self.setWindowTitle("Connection Matrix")
        # Increased window size for better readability
        self.resize(1400, 700)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Winding Connection Matrix")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Info label
        phase_list = ", ".join([chr(65 + i) for i in range(self.num_phases)])
        if self.is_double_layer:
            info_text = f"Double Layer Winding: {2*self.num_phases} phases × {self.num_slots} slots\n"
            info_text += f"Phases {phase_list} | Top layer (A+, B+, ...) and Bottom layer (A-, B-, ...)\n"
            info_text += f"Values: +1 (go in), -1 (go out), 0 (no conductor)"
        else:
            info_text = f"Single Layer Winding: {self.num_phases} phases × {self.num_slots} slots\n"
            info_text += f"Phases: {phase_list}\n"
            info_text += f"Values: +1 (go in), -1 (go out), 0 (no conductor)"
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #cccccc; padding: 10px; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Table widget
        self.table = QTableWidget()
        self.populate_table()
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export to Excel")
        export_btn.setStyleSheet("background-color: #2d2d2d; color: white; padding: 8px; font-size: 13px;")
        export_btn.clicked.connect(self.export_to_excel)
        button_layout.addWidget(export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #2d2d2d; color: white; padding: 8px; font-size: 13px;")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def populate_table(self):
        """Populate table with matrix data"""
        rows, cols = self.matrix.shape
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)
        
        # Set column headers (Slot numbers) - just numbers
        col_headers = [str(i+1) for i in range(cols)]
        self.table.setHorizontalHeaderLabels(col_headers)
        
        # Set row headers (Phase labels) - clear and concise
        row_headers = []
        phase_names = [chr(65 + i) for i in range(self.num_phases)]  # A, B, C, D, E, ...
        
        if self.is_double_layer:
            # For double layer: A+, B+, C+, ... for top, A-, B-, C-, ... for bottom
            for phase in phase_names:
                row_headers.append(f"{phase}+")
            for phase in phase_names:
                row_headers.append(f"{phase}-")
        else:
            # For single layer: just A, B, C, D, E, ...
            row_headers = phase_names[:rows]
        
        self.table.setVerticalHeaderLabels(row_headers)
        
        # Fill table with matrix values (should be -1, 0, or +1)
        for i in range(rows):
            for j in range(cols):
                value = self.matrix[i, j]
                
                # Display format
                if abs(value) < 0.01:  # Close to zero
                    display_text = ""
                elif value > 0:
                    display_text = "+1"
                elif value < 0:
                    display_text = "-1"
                else:
                    display_text = str(int(value) if value == int(value) else f"{value:.1f}")
                
                item = QTableWidgetItem(display_text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(QFont("Segoe UI", 11))  # Clean, readable font
                
                # Color code non-zero values
                if value > 0.01:
                    item.setBackground(QColor(200, 255, 200))  # Light green for +1
                    item.setForeground(QColor(0, 120, 0))      # Dark green text
                    item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                elif value < -0.01:
                    item.setBackground(QColor(255, 200, 200))  # Light red for -1
                    item.setForeground(QColor(150, 0, 0))      # Dark red text
                    item.setFont(QFont("Segoe UI", 11, QFont.Bold))
                else:
                    item.setBackground(QColor(240, 240, 240))  # Light gray for empty
                    item.setForeground(QColor(180, 180, 180))  # Gray for 0
                
                self.table.setItem(i, j, item)
        
        # Set uniform column and row sizes for perfect alignment
        for col in range(cols):
            self.table.setColumnWidth(col, 50)
        
        for row in range(rows):
            self.table.setRowHeight(row, 40)
        
        # Style for vertical header (phase names)
        self.table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #444444;
                font-size: 14px;
                font-weight: bold;
                min-width: 60px;
            }
        """)
        
        # Style for horizontal header (slot numbers)
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #444444;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                gridline-color: #888888;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 0px;
                border: 1px solid #cccccc;
            }
            QTableWidget::item:selected {
                background-color: #e0e0ff;
            }
        """)
    
    def export_to_excel(self):
        """Export connection matrix to Excel file"""
        # Generate default filename
        slots = self.num_slots
        phases = self.num_phases
        layer_type = "DoubleLayer" if self.is_double_layer else "SingleLayer"
        default_filename = f"ConnectionMatrix_{slots}slots_{phases}phases_{layer_type}.xlsx"
        
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Connection Matrix", 
            default_filename, 
            "Excel Files (*.xlsx);;All Files (*)"
        )
        
        if filename:
            try:
                # Create DataFrame
                phase_names = [chr(65 + i) for i in range(self.num_phases)]
                col_labels = [f"Slot {i+1}" for i in range(self.num_slots)]
                
                if self.is_double_layer:
                    row_labels = []
                    for phase in phase_names:
                        row_labels.append(f"{phase} Top")
                    for phase in phase_names:
                        row_labels.append(f"{phase} Bottom")
                else:
                    row_labels = phase_names[:self.matrix.shape[0]]
                
                df = pd.DataFrame(self.matrix, index=row_labels, columns=col_labels)
                
                # Export to Excel
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Connection Matrix')
                    
                    # Get the workbook and worksheet
                    workbook = writer.book
                    worksheet = writer.sheets['Connection Matrix']
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(cell.value)
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 15)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                QMessageBox.information(self, "Success", f"Matrix exported successfully to:\n{filename}")
            
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export matrix:\n{str(e)}")
