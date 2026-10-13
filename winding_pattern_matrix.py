"""
Winding Pattern Matrix Generator
Based on star of slots theory - generates double layer matrices
Matrix first, then patterns for visualization
"""
import numpy as np
import math
from fractions import Fraction
from dataclasses import dataclass


@dataclass
class Coil:
    """Represents a single coil in the winding"""
    begin: int  # Start slot (1-indexed)
    end: int    # End slot (1-indexed)
    nc: int     # Number of conductors (positive or negative)
    
    def __repr__(self):
        return f"Coil(begin={self.begin}, end={self.end}, nc={self.nc})"


class PhaseWinding:
    """Collection of coils that form one phase"""
    
    def __init__(self, Q, p):
        self.Q = Q  # Number of slots
        self.p = p  # Number of pole pairs
        self.coils = []
        self.slot_matrix = np.zeros(Q)
    
    def add_coil(self, coil):
        """Add a coil to this phase"""
        self.coils.append(coil)
    
    def compute_slot_matrix(self):
        """Compute the slot matrix from coils"""
        if len(self.coils) < 1:
            return False
        
        self.slot_matrix = np.zeros(self.Q)
        for coil in self.coils:
            self.slot_matrix[coil.begin - 1] += coil.nc
            self.slot_matrix[coil.end - 1] -= coil.nc
        return True
    
    def get_slot_matrix(self, normalize=True):
        """Return the slot matrix, optionally normalized"""
        self.compute_slot_matrix()
        
        if normalize:
            max_val = np.max(np.abs(self.slot_matrix))
            if max_val > 0:
                return self.slot_matrix / max_val
        return self.slot_matrix
    
    def get_double_layer_matrices(self, normalize=True):
        """
        Return separate top and bottom layer matrices
        Top layer: where coils BEGIN
        Bottom layer: where coils END
        """
        if len(self.coils) < 1:
            return np.zeros(self.Q), np.zeros(self.Q)
        
        top_layer = np.zeros(self.Q)
        bottom_layer = np.zeros(self.Q)
        
        for coil in self.coils:
            top_layer[coil.begin - 1] += coil.nc
            bottom_layer[coil.end - 1] -= coil.nc
        
        if normalize:
            max_val = max(np.max(np.abs(top_layer)), np.max(np.abs(bottom_layer)))
            if max_val > 0:
                top_layer = top_layer / max_val
                bottom_layer = bottom_layer / max_val
        
        return top_layer, bottom_layer


@dataclass
class Spoke:
    """Represents a spoke in the star of slots"""
    id: int      # Slot number (1-indexed)
    angle: float # Angle in radians
    
    def __repr__(self):
        return f"Spoke(id={self.id}, angle={self.angle * 180 / math.pi:.2f}°)"


class Sector:
    """Represents a sector in the star of slots"""
    
    def __init__(self, start_angle, end_angle):
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.slots = []
    
    def angle_inside(self, angle):
        """Check if angle is inside this sector, handling wrap-around"""
        # Check if sector wraps around 0/2π
        if self.start_angle > self.end_angle:
            # Wrap-around case: sector spans across 0°/360°
            # Angle is inside if it's > start_angle OR < end_angle
            if angle > self.start_angle or angle < self.end_angle:
                return True
        else:
            # Normal case: no wrap-around
            if angle > self.start_angle and angle < self.end_angle:
                return True
        return False
    
    def normalize_angles(self):
        """Normalize angles to 0-2π range"""
        while self.start_angle >= 2 * math.pi:
            self.start_angle -= 2 * math.pi
        while self.end_angle > 2 * math.pi:
            self.end_angle -= 2 * math.pi
    
    def __repr__(self):
        return f"Sector({self.start_angle * 180 / math.pi:.1f}° - {self.end_angle * 180 / math.pi:.1f}°, slots={self.slots})"


class StarOfSlots:
    """Star of slots implementation for balanced 3-phase windings"""
    
    def __init__(self, m, Q, p):
        """
        m: number of phases
        Q: number of slots
        p: number of pole pairs
        """
        self.m = m
        self.Q = Q
        self.p = p
        self.t = self._gcd(Q, p)  # Machine periodicity
        self.yq = int(Q / (2 * p))  # Theoretical coil throw
        if self.yq < 1:
            self.yq = 1
        
        self.star = []   # List of spokes
        self.p_sec = []  # Positive sectors
        self.n_sec = []  # Negative sectors
        
        self.single_layer_feasible = False
        self._check_feasibility()
        self.create_star()
    
    def _gcd(self, a, b):
        """Calculate greatest common divisor"""
        if b == 0:
            return a
        return self._gcd(b, a % b)
    
    def _check_feasibility(self):
        """Check if single layer winding is feasible"""
        if self._gcd(self.Q, 2) == 2:  # Q is even
            if self._gcd(int(self.Q / self.t), 2) != 2:  # Q/t is odd
                if (self.t % 2) == 0:  # t is even
                    self.single_layer_feasible = True
            else:  # Q/t is even
                if self._gcd(int(self.Q / (2 * self.t)), 2) == 2:
                    self.single_layer_feasible = True
    
    def create_star(self):
        """Create the star of slots by populating spokes"""
        self.star.clear()
        
        alpha_se = 2 * math.pi / self.Q * self.p  # Slot electrical angle
        alpha_ph = 2 * math.pi / self.Q * self.t  # Angle between adjacent phasors
        
        # Epsilon offset to avoid spokes on sector borders
        epsilon = 0
        spoke_per_phase = self.Q / (self.m * self.t)
        
        if (self.m % 2) != 0:  # m is odd
            if spoke_per_phase == 1 or spoke_per_phase == 2:
                epsilon = math.pi / self.m / 2
            elif (spoke_per_phase % 2) == 0:
                epsilon = alpha_ph / 2
            else:
                epsilon = alpha_ph / 4
        else:  # m is even
            if spoke_per_phase == 1 or spoke_per_phase == 2:
                epsilon = 0
            elif (int(spoke_per_phase / 2) % 2) == 0:
                epsilon = alpha_ph / 4
            else:
                epsilon = alpha_ph / 8  # Changed from alpha_ph/2 to alpha_ph/8 for smaller offset
        
        # Create spokes
        for i in range(self.Q):
            angle = alpha_se * i + epsilon
            spoke = Spoke(i + 1, angle)
            self.star.append(spoke)
        
        # Normalize angles to 0-2π
        for spoke in self.star:
            while spoke.angle >= 2 * math.pi:
                spoke.angle -= 2 * math.pi
            if abs(spoke.angle - 2 * math.pi) < 1e-4:
                spoke.angle = 0.0
    
    def create_sectors(self, offset=0):
        """Create positive and negative sectors"""
        self.p_sec.clear()
        self.n_sec.clear()
        
        for i in range(self.m):
            if (self.m % 2) != 0:  # Odd number of phases
                start_angle = offset + math.pi * 0.5 + math.pi / self.m * (2 * i - 0.5)
                end_angle = offset + math.pi * 0.5 + math.pi / self.m * (2 * i + 0.5)
            else:  # Even number of phases - use π/m for split-phase (dual 3-phase)
                start_angle = offset + math.pi * 0.5 + math.pi / self.m * (i - 0.5)
                end_angle = offset + math.pi * 0.5 + math.pi / self.m * (i + 0.5)
            
            # Positive sector
            sec_p = Sector(start_angle, end_angle)
            sec_p.normalize_angles()
            self.p_sec.append(sec_p)
            
            # Negative sector
            sec_n = Sector(start_angle + math.pi, end_angle + math.pi)
            sec_n.normalize_angles()
            self.n_sec.append(sec_n)
        
        # Populate sectors with slot numbers
        for spoke in self.star:
            for sector in self.p_sec:
                if sector.angle_inside(spoke.angle):
                    sector.slots.append(spoke.id)
            for sector in self.n_sec:
                if sector.angle_inside(spoke.angle):
                    sector.slots.append(spoke.id)


class MultiPhaseWinding:
    """Complete m-phase winding with matrix generation"""
    
    def __init__(self):
        self.windings = []  # List of PhaseWinding objects (one per phase)
        self.star = None
        self.p = None
        self.Q = None
        self.m = None  # Number of phases
        self.slot_matrix = None
        self.winding_pattern = []
    
    def compute_winding(self, m, Q, p, yq=-1, single_layer=False):
        """
        Compute balanced winding based on star of slots theory
        m: number of phases (2, 3, 4, 5, ...)
        Q: number of slots
        p: number of pole pairs
        yq: coil throw (default: theoretical value)
        single_layer: whether to use single layer winding
        """
        self.Q = Q
        self.p = p
        self.m = m
        self.windings.clear()
        
        # Create star of slots
        self.star = StarOfSlots(m, Q, p)
        self.star.create_sectors()
        
        # Determine coil throw
        if yq < 0:
            yq = self.star.yq
        
        if not self.star.single_layer_feasible:
            single_layer = False
        
        if single_layer and (yq % 2 == 0):
            yq = yq - 1  # yq must be odd for single layer
        
        # Create windings for each phase
        for i in range(m):
            phase_winding = PhaseWinding(Q, p)
            
            # Add coils from positive sectors
            for slot in self.star.p_sec[i].slots:
                if single_layer and (slot % 2 == 0):
                    continue
                end = slot + yq
                while end > Q:
                    end -= Q
                coil = Coil(slot, end, 1)
                phase_winding.add_coil(coil)
            
            # Add coils from negative sectors
            for slot in self.star.n_sec[i].slots:
                if single_layer and (slot % 2 == 0):
                    continue
                end = slot + yq
                while end > Q:
                    end -= Q
                coil = Coil(slot, end, -1)
                phase_winding.add_coil(coil)
            
            self.windings.append(phase_winding)
    
    def get_double_layer_matrix(self, normalize=True):
        """
        Generate 2m×Q matrix for double layer winding
        Rows 0 to m-1: Top layer for phases
        Rows m to 2m-1: Bottom layer for phases
        """
        if not self.windings or self.Q is None or self.m is None:
            return None
        
        matrix = np.zeros((2 * self.m, self.Q))
        
        for phase_idx, phase_winding in enumerate(self.windings):
            top_layer, bottom_layer = phase_winding.get_double_layer_matrices(normalize)
            matrix[phase_idx] = top_layer                # Row 0 to m-1 = Top layers
            matrix[self.m + phase_idx] = bottom_layer    # Row m to 2m-1 = Bottom layers
        
        return matrix
    
    def get_slot_matrices(self, normalize=True):
        """
        Get slot matrices for all phases (for single layer analysis)
        Returns list of arrays for phases A, B, C
        """
        if not self.windings:
            return None
        
        matrices = []
        for phase_winding in self.windings:
            matrices.append(phase_winding.get_slot_matrix(normalize))
        
        return matrices
    
    def generate_winding_pattern(self, is_double_layer=True):
        """
        Generate winding pattern from matrices for visualization
        Returns list of (top_phase, bottom_phase) tuples
        """
        if not self.windings or self.Q is None or self.m is None:
            return []
        
        pattern = []
        # Generate phase names A, B, C, D, E, F, G, H, I, J, K, L...
        phase_names = [chr(65 + i) for i in range(self.m)]
        
        if is_double_layer:
            matrix = self.get_double_layer_matrix(normalize=False)
            
            for slot_idx in range(self.Q):
                top_phase = None
                bottom_phase = None
                
                # Check top layer (rows 0 to m-1)
                for phase_idx in range(self.m):
                    if abs(matrix[phase_idx][slot_idx]) > 0:
                        top_phase = phase_names[phase_idx]
                        break
                
                # Check bottom layer (rows m to 2m-1)
                for phase_idx in range(self.m):
                    if abs(matrix[self.m + phase_idx][slot_idx]) > 0:
                        bottom_phase = phase_names[phase_idx]
                        break
                
                pattern.append((top_phase, bottom_phase))
        else:
            # Single layer
            matrices = [w.get_slot_matrix(normalize=False) for w in self.windings]
            
            for slot_idx in range(self.Q):
                phase = None
                for phase_idx, matrix in enumerate(matrices):
                    if abs(matrix[slot_idx]) > 0:
                        phase = phase_names[phase_idx]
                        break
                pattern.append((phase, None))
        
        self.winding_pattern = pattern
        return pattern


def generate_winding_pattern_from_matrix(slots, poles, coil_span, is_double_layer, phases=3):
    """
    Main interface function to generate winding pattern
    
    Parameters:
    -----------
    slots: int - number of slots
    poles: int - number of actual poles (not pole pairs)
    coil_span: int - coil span in slots
    is_double_layer: bool - whether double layer winding
    phases: int - number of phases (default 3)
    
    Returns:
    --------
    winding_pattern: list of (top_phase, bottom_phase) tuples
    winding_obj: MultiPhaseWinding object for further analysis
    """
    pole_pairs = poles // 2
    
    # Create and compute winding
    winding = MultiPhaseWinding()
    winding.compute_winding(
        m=phases,
        Q=slots,
        p=pole_pairs,
        yq=coil_span,
        single_layer=not is_double_layer
    )
    
    # Generate pattern for visualization
    pattern = winding.generate_winding_pattern(is_double_layer)
    
    return pattern, winding
