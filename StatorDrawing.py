from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPixmap
from PyQt5.QtCore import Qt, QPoint, QRect
from fractions import Fraction
import math
from winding_pattern_matrix import generate_winding_pattern_from_matrix

class StatorDrawing(QWidget):
    def __init__(self):
        super().__init__()
        self.slots = 36  # Changed from 24 to 36
        self.poles = 4  # Keep as actual poles internally for calculations
        self.coil_span = 6
        self.is_double_layer = True
        self.phases = 3  # Default 3 phases
        self.colors = self._generate_phase_colors(3)
        self.setMinimumSize(400, 400)
        self.winding_obj = None  # Store winding object for matrix access
        self.winding_pattern = self.calculate_winding_pattern()
    
    def _generate_phase_colors(self, num_phases):
        """Generate visually distinct colors for any number of phases"""
        colors = {}
        phase_names = [chr(65 + i) for i in range(num_phases)]  # A, B, C, D, ...
        
        # Pre-defined colors for common phase numbers
        if num_phases == 2:
            predefined = [QColor(255, 0, 0), QColor(0, 0, 255)]  # Red, Blue
        elif num_phases == 3:
            predefined = [QColor(255, 0, 0), QColor(0, 0, 255), QColor(0, 255, 0)]  # Red, Blue, Green
        elif num_phases == 4:
            predefined = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), QColor(255, 255, 0)]
        elif num_phases == 5:
            predefined = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), QColor(255, 255, 0), QColor(255, 0, 255)]
        elif num_phases == 6:
            predefined = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), 
                         QColor(255, 255, 0), QColor(255, 0, 255), QColor(0, 255, 255)]
        else:
            # Generate colors using HSV color space for other phase numbers
            predefined = []
            for i in range(num_phases):
                hue = int((360 * i) / num_phases)
                predefined.append(QColor.fromHsv(hue, 255, 255))
        
        for i, phase in enumerate(phase_names):
            colors[phase] = predefined[i]
        
        return colors

    def calculate_winding_pattern(self):
        """
        Generate winding pattern using matrix-based approach (like koil)
        Matrix is generated first, then converted to pattern for plotting
        """
        try:
            # Generate pattern from matrix using star of slots theory
            pattern, winding_obj = generate_winding_pattern_from_matrix(
                slots=self.slots,
                poles=self.poles,
                coil_span=self.coil_span,
                is_double_layer=self.is_double_layer,
                phases=self.phases
            )
            self.winding_obj = winding_obj  # Store for matrix access
            return pattern
        except Exception as e:
            print(f"Error generating winding pattern: {e}")
            # Fallback to simple pattern
            return [(None, None)] * self.slots

    def save_drawing(self, filename):
        pixmap = QPixmap(self.size())
        self.render(pixmap)
        pixmap.save(filename)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = QPoint(self.width() // 2, self.height() // 2)
        radius = min(self.width(), self.height()) // 2 - 20
        inner_radius = radius * 0.65
        rotor_radius = inner_radius * 0.95

        slot_angle = 360 / self.slots
        slot_arc_width = 3  # Keep constant at 3 instead of dynamic formula

        # Draw outer circle
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(center, radius, radius)

        for i in range(self.slots):
            # Slot arc - changed to counterclockwise
            angle_deg = -i * slot_angle  # Negative for counterclockwise
            arc_start = (angle_deg - slot_arc_width / 2) * 16
            arc_span = slot_arc_width * 16

            if self.is_double_layer:
                arc_radius = int(inner_radius) + 33
            else:
                arc_radius = int(inner_radius) + 15

            rect = QRect(center.x() - arc_radius, center.y() - arc_radius, arc_radius * 2, arc_radius * 2)
            painter.setPen(QPen(Qt.black, 2))
            painter.drawArc(rect, int(arc_start), int(arc_span))

            # Tooth arc: between current slot and next slot
            tooth_start_deg = angle_deg + slot_arc_width / 2
            tooth_span_deg = slot_angle - slot_arc_width

            tooth_start = (tooth_start_deg) * 16
            tooth_span = tooth_span_deg * 16

            tooth_radius = int(inner_radius) - 4

            tooth_rect = QRect(center.x() - tooth_radius, center.y() - tooth_radius, tooth_radius * 2, tooth_radius * 2)
            painter.setPen(QPen(Qt.black, 2))
            painter.drawArc(tooth_rect, int(tooth_start), int(tooth_span))

            # Partial radial lines from slot arc to tooth arc
            mid_angle_rad1 = math.radians(angle_deg - slot_arc_width / 2)
            mid_angle_rad2 = math.radians(angle_deg + slot_arc_width / 2)

            line_start_radius = tooth_radius
            line_end_radius = arc_radius

            # First side of slot
            x1 = center.x() + line_start_radius * math.cos(mid_angle_rad1)
            y1 = center.y() + line_start_radius * math.sin(mid_angle_rad1)
            x2 = center.x() + line_end_radius * math.cos(mid_angle_rad1)
            y2 = center.y() + line_end_radius * math.sin(mid_angle_rad1)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Second side of slot
            x3 = center.x() + line_start_radius * math.cos(mid_angle_rad2)
            y3 = center.y() + line_start_radius * math.sin(mid_angle_rad2)
            x4 = center.x() + line_end_radius * math.cos(mid_angle_rad2)
            y4 = center.y() + line_end_radius * math.sin(mid_angle_rad2)
            painter.drawLine(int(x3), int(y3), int(x4), int(y4))

            # Draw slot number
            number_radius = arc_radius + 20  # distance from center
            number_angle_rad = math.radians(angle_deg)

            nx = center.x() + number_radius * math.cos(number_angle_rad)
            ny = center.y() + number_radius * math.sin(number_angle_rad)

            painter.setPen(Qt.black)
            painter.setFont(QFont("Arial", 10))
            painter.drawText(int(nx) - 8, int(ny) + 4, str(i + 1))


            self.draw_slot_winding(painter, i, center, inner_radius, radius)

        # Draw centered title text - changed title
        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        text = "STATOR WINDING"
        text_rect = QRect(center.x() - 150, center.y() - 10, 300, 20)
        painter.drawText(text_rect, Qt.AlignCenter, text)
        
        self.draw_legend(painter)

    def draw_slot_winding(self, painter, slot_num, center, inner_radius, outer_radius):
        slot_angle = 360 / self.slots
        angle = -slot_angle * slot_num  # Negative for counterclockwise
        rad = math.radians(angle)

        if self.is_double_layer:
            r1 = (inner_radius + outer_radius) * 0.43
            r2 = (inner_radius + outer_radius) * 0.4

            if slot_num < len(self.winding_pattern):
                bottom_phase = self.winding_pattern[slot_num][1]
                if bottom_phase:
                    self.draw_symbol(painter, center, r1, rad, bottom_phase)

            if slot_num < len(self.winding_pattern):
                top_phase = self.winding_pattern[slot_num][0]
                if top_phase:
                    self.draw_symbol(painter, center, r2, rad, top_phase)
        else:
            r = (inner_radius + outer_radius) * 0.4
            if slot_num < len(self.winding_pattern):
                phase = self.winding_pattern[slot_num][0]
                if phase:
                    self.draw_symbol(painter, center, r, rad, phase)

    def draw_symbol(self, painter, center, r, rad, phase):
        x = center.x() + r * math.cos(rad)
        y = center.y() + r * math.sin(rad)

        size = 12
        color = self.colors[phase]

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(int(x - size / 2), int(y - size / 2), size, size)

    def draw_legend(self, painter):
        legend_x = self.width() - 120
        legend_y = 20
        size = 22
        spacing = 25

        painter.setPen(QPen(Qt.black))
        # Generate phase names dynamically
        phase_names = [chr(65 + i) for i in range(self.phases)]
        for i, phase in enumerate(phase_names):
            if phase in self.colors:
                color = self.colors[phase]
                painter.setBrush(color)
                painter.drawEllipse(legend_x, legend_y + i * spacing, size, size)
                painter.setPen(QPen(Qt.black))
                painter.drawText(legend_x + size + 5, legend_y + i * spacing + size - 2, f"Phase {phase}")

    def update_parameters(self, slots, poles, coil_span, is_double_layer, phases=3):
        self.slots = slots
        self.poles = poles  # This receives actual poles from the UI calculations
        self.coil_span = coil_span
        self.is_double_layer = is_double_layer
        self.phases = phases
        self.colors = self._generate_phase_colors(phases)  # Regenerate colors for new phase count
        self.winding_pattern = self.calculate_winding_pattern()
        self.update()
    
    def get_double_layer_matrix(self):
        """
        Get the 2m×Q double layer matrix
        Rows 0 to m-1: Top layer for phases
        Rows m to 2m-1: Bottom layer for phases
        """
        if self.winding_obj:
            return self.winding_obj.get_double_layer_matrix(normalize=True)
        return None
    
    def get_slot_matrices(self):
        """
        Get the individual phase slot matrices (for single layer)
        Returns list of m arrays for all phases
        """
        if self.winding_obj:
            return self.winding_obj.get_slot_matrices(normalize=True)
        return None