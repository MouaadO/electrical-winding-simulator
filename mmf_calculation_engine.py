import numpy as np
import pandas as pd
import math
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class MMFPlotWidget:
    def __init__(self):
        # Dynamic phase profiles storage
        self.num_phases = 3  # Default
        self.phase_profiles = {}  # Will store profiles for each phase (numpy arrays)
        self.phase_currents = {}  # Dynamic phase currents
        
        self.matrix = None
        self.slot_cur_matrix = None  # Koil-style slot current matrix
        self.Slot_arc = 5  # Default value, will be updated dynamically
        self.Wt = 90  # Default Wt angle in degrees
        self.N = 204  # Number of turns
        self.I = 2.8  # Current amplitude
        
        # Legacy attributes for backward compatibility
        self.mmf_profile_resultant = None
        self.mmf_profile_A = None
        self.mmf_profile_B = None
        self.mmf_profile_C = None

    def update_matrix_from_parameters(self, matrix, is_double_layer):
        """
        Update MMF calculation with new matrix from winding object.
        Matrix should be 6×Q for double layer or 3×Q for single layer.
        """
        if matrix is None:
            return None
            
        self.matrix = matrix
        
        # Update slot arc based on number of slots using dynamic formula
        if self.matrix is not None:
            n_slots = self.matrix.shape[1]
            self.Slot_arc = 360 / (2 * n_slots)
        
        self.set_connection_matrix(self.matrix)
        return self.matrix

    def set_connection_matrix(self, matrix):
        """Set the winding matrix and compute MMF using koil method"""
        # Common parameters
        self.N_slots = matrix.shape[1]
        self.Tooth_arc = (360 / self.N_slots) - self.Slot_arc
        self.lepas = self.Tooth_arc + self.Slot_arc
        
        # Determine number of phases from matrix
        rows = matrix.shape[0]
        
        # Detect if double layer by checking if rows is even and > num_phases
        # For m phases: single layer = m rows, double layer = 2m rows
        if rows >= 4 and rows % 2 == 0:
            # Likely double layer
            self.num_phases = rows // 2
            is_double_layer = True
        else:
            # Single layer
            self.num_phases = rows
            is_double_layer = False
        
        # Compute slot current matrix using koil approach
        self.compute_slot_current_matrix_koil(matrix, is_double_layer)
        
        # Calculate MMF for each phase
        self.calculate_phase_mmf_koil()
        
        # Calculate resultant MMF
        self.calculate_resultant_koil()
    
    def compute_slot_current_matrix_koil(self, matrix, is_double_layer):
        """
        Compute slot current matrix for each phase using koil.py approach.
        Each phase gets its own slot_cur_matrix based on current phase angle.
        """
        Q = self.N_slots
        m = self.num_phases
        
        # Calculate instantaneous current factors for all phases based on Wt
        wt_rad = np.radians(self.Wt)
        phase_currents = []
        for k in range(m):
            # Phase angle: 2π*k/m
            phase_angle = 2 * np.pi * k / m
            current_factor = np.cos(wt_rad - phase_angle) * self.I
            phase_currents.append(current_factor)
        
        # Build slot current matrix for each phase
        phase_names = [chr(65 + i) for i in range(m)]  # A, B, C, D, ...
        
        for idx, phase_name in enumerate(phase_names):
            if is_double_layer:
                # Double layer: sum top and bottom
                phase_matrix_top = matrix[idx]
                phase_matrix_bot = matrix[m + idx]
                phase_matrix_sum = phase_matrix_top + phase_matrix_bot
            else:
                # Single layer
                phase_matrix_sum = matrix[idx]
            
            # Store in phase_profiles (as slot current contribution)
            self.phase_profiles[phase_name] = phase_matrix_sum * phase_currents[idx]
            self.phase_currents[phase_name] = phase_currents[idx]
        
        # Compute total slot current matrix (sum of all phases)
        self.slot_cur_matrix = np.zeros(Q)
        for phase_name in phase_names:
            self.slot_cur_matrix += self.phase_profiles[phase_name]
        
        # Initialize phase currents (all equal by default)
        if not self.phase_currents:
            for i in range(self.num_phases):
                phase_name = chr(65 + i)  # A, B, C, D, ...
                self.phase_currents[phase_name] = 2.8

        self.matrix = matrix
        
        # Extract phase matrices
        phase_matrices = []
        if rows == self.num_phases:  # Single layer
            for i in range(self.num_phases):
                phase_matrices.append(matrix[i])
            self._calculate_mmf_multi_phase(phase_matrices)
        elif rows == 2 * self.num_phases:  # Double layer
            phase_matrices_top = []
            phase_matrices_bot = []
            for i in range(self.num_phases):
                top = matrix[i].copy()
                bot = matrix[self.num_phases + i].copy()
                phase_matrices.append(top + bot)
                
                # Split based on values
                top_layer = np.zeros_like(top)
                bot_layer = np.zeros_like(bot)
                for j in range(self.N_slots):
                    if abs(top[j]) == 2:
                        top_layer[j] = top[j] / 2
                        bot_layer[j] = top[j] / 2
                    elif abs(top[j]) == 1:
                        top_layer[j] = top[j]
                        bot_layer[j] = 0
                
                phase_matrices_top.append(top_layer)
                phase_matrices_bot.append(bot_layer)
            
            self._calculate_mmf_double_layer_multi_phase(phase_matrices_top, phase_matrices_bot)
        else:
            self._calculate_mmf(A, B, C)

    def _calculate_mmf(self, A, B, C):
        """
        Calculate single-layer MMF profiles for phases A, B, and C using tooth-based approach.
        """
        # Calculate MMF for each phase
        mmf_phase_A = A * self.Ia * self.N / 2
        mmf_phase_B = B * self.Ib * self.N / 2
        mmf_phase_C = C * self.Ic * self.N / 2

        # Apply tooth-based logic
        mmf_tooth_A = self.calculate_mmf_tooth_logic(mmf_phase_A)
        mmf_tooth_B = self.calculate_mmf_tooth_logic(mmf_phase_B)
        mmf_tooth_C = self.calculate_mmf_tooth_logic(mmf_phase_C)

        # Create continuous profiles
        self.mmf_profile_A, self.mmf_profile_B, self.mmf_profile_C = self.create_continuous_profiles(
            mmf_tooth_A, mmf_tooth_B, mmf_tooth_C)
        
        # Calculate resultant using new formula: A*sin(Wt) + B*sin(Wt+120°) + C*sin(Wt-120°)
        self.mmf_profile_resultant = self._calculate_resultant_new_formula(
            self.mmf_profile_A, self.mmf_profile_B, self.mmf_profile_C)

    def _calculate_mmf_double_layer(self, A_t, A_b, B_t, B_b, C_t, C_b):
        """
        Calculate double-layer MMF profiles. Computes separate top and bottom profiles,
        then sums them for overall profiles using tooth-based approach.
        """
        # Top layer
        mmf_phase_A_top = A_t * self.Ia * self.N / 2
        mmf_phase_B_top = B_t * self.Ib * self.N / 2
        mmf_phase_C_top = C_t * self.Ic * self.N / 2

        mmf_tooth_A_top = self.calculate_mmf_tooth_logic(mmf_phase_A_top)
        mmf_tooth_B_top = self.calculate_mmf_tooth_logic(mmf_phase_B_top)
        mmf_tooth_C_top = self.calculate_mmf_tooth_logic(mmf_phase_C_top)

        self.mmf_profile_A_top, self.mmf_profile_B_top, self.mmf_profile_C_top = self.create_continuous_profiles(
            mmf_tooth_A_top, mmf_tooth_B_top, mmf_tooth_C_top)

        # Bottom layer
        mmf_phase_A_bot = A_b * self.Ia * self.N / 2
        mmf_phase_B_bot = B_b * self.Ib * self.N / 2
        mmf_phase_C_bot = C_b * self.Ic * self.N / 2

        mmf_tooth_A_bot = self.calculate_mmf_tooth_logic(mmf_phase_A_bot)
        mmf_tooth_B_bot = self.calculate_mmf_tooth_logic(mmf_phase_B_bot)
        mmf_tooth_C_bot = self.calculate_mmf_tooth_logic(mmf_phase_C_bot)

        self.mmf_profile_A_bot, self.mmf_profile_B_bot, self.mmf_profile_C_bot = self.create_continuous_profiles(
            mmf_tooth_A_bot, mmf_tooth_B_bot, mmf_tooth_C_bot)

        # Sum profiles (maintain double layer logic)
        self.mmf_profile_A_sum = self._sum_continuous_profiles(self.mmf_profile_A_top, self.mmf_profile_A_bot)
        self.mmf_profile_B_sum = self._sum_continuous_profiles(self.mmf_profile_B_top, self.mmf_profile_B_bot)
        self.mmf_profile_C_sum = self._sum_continuous_profiles(self.mmf_profile_C_top, self.mmf_profile_C_bot)

        # Set default profiles to summed for phases view
        self.mmf_profile_A, self.mmf_profile_B, self.mmf_profile_C = (
            self.mmf_profile_A_sum, self.mmf_profile_B_sum, self.mmf_profile_C_sum)
        
        # Calculate resultant using new formula: A*sin(Wt) + B*sin(Wt+120°) + C*sin(Wt-120°)
        self.mmf_profile_resultant = self._calculate_resultant_new_formula(
            self.mmf_profile_A, self.mmf_profile_B, self.mmf_profile_C)

    def _calculate_mmf_multi_phase(self, phase_matrices):
        """
        Calculate MMF for multi-phase single layer winding.
        phase_matrices: list of m phase MMF matrices (one per phase)
        """
        phase_mmf_tooth_list = []
        
        for phase_matrix in phase_matrices:
            # For single layer, phase_matrix is already 1D array (Q slots)
            mmf_tooth = self.calculate_mmf_tooth_logic(phase_matrix)
            phase_mmf_tooth_list.append(mmf_tooth)
        
        # Create continuous profiles for all phases
        profiles = self.create_continuous_profiles_multi(phase_mmf_tooth_list)
        
        # Store in phase_profiles dict
        phase_names = [chr(65 + i) for i in range(len(profiles))]  # A, B, C, ...
        for name, profile in zip(phase_names, profiles):
            self.phase_profiles[name] = profile
        
        # Also populate legacy attributes if 3-phase
        if len(profiles) == 3:
            self.mmf_profile_A = profiles[0]
            self.mmf_profile_B = profiles[1]
            self.mmf_profile_C = profiles[2]
        
        # Calculate resultant
        self.mmf_profile_resultant = self.calculate_resultant_multi_phase(profiles)

    def _calculate_mmf_double_layer_multi_phase(self, phase_matrices_top, phase_matrices_bot):
        """
        Calculate MMF for multi-phase double layer winding.
        phase_matrices_top/bot: lists of m phase MMF matrices for top and bottom layers
        """
        phase_mmf_tooth_top_list = []
        phase_mmf_tooth_bot_list = []
        
        for phase_top, phase_bot in zip(phase_matrices_top, phase_matrices_bot):
            mmf_tooth_top = self.calculate_mmf_tooth_logic(phase_top)
            mmf_tooth_bot = self.calculate_mmf_tooth_logic(phase_bot)
            phase_mmf_tooth_top_list.append(mmf_tooth_top)
            phase_mmf_tooth_bot_list.append(mmf_tooth_bot)
        
        # Create continuous profiles
        profiles_top = self.create_continuous_profiles_multi(phase_mmf_tooth_top_list)
        profiles_bot = self.create_continuous_profiles_multi(phase_mmf_tooth_bot_list)
        
        # Sum top and bottom for each phase
        profiles_sum = [self._sum_continuous_profiles(top, bot) 
                        for top, bot in zip(profiles_top, profiles_bot)]
        
        # Store in phase_profiles dict
        phase_names = [chr(65 + i) for i in range(len(profiles_sum))]  # A, B, C, ...
        for name, profile in zip(phase_names, profiles_sum):
            self.phase_profiles[name] = profile
        
        # Also populate legacy attributes if 3-phase
        if len(profiles_sum) == 3:
            self.mmf_profile_A_top = profiles_top[0]
            self.mmf_profile_B_top = profiles_top[1]
            self.mmf_profile_C_top = profiles_top[2]
            self.mmf_profile_A_bot = profiles_bot[0]
            self.mmf_profile_B_bot = profiles_bot[1]
            self.mmf_profile_C_bot = profiles_bot[2]
            self.mmf_profile_A_sum = profiles_sum[0]
            self.mmf_profile_B_sum = profiles_sum[1]
            self.mmf_profile_C_sum = profiles_sum[2]
            self.mmf_profile_A = profiles_sum[0]
            self.mmf_profile_B = profiles_sum[1]
            self.mmf_profile_C = profiles_sum[2]
        
        # Calculate resultant
        self.mmf_profile_resultant = self.calculate_resultant_multi_phase(profiles_sum)

    def calculate_mmf_tooth_logic(self, phase_mmf):
        """
        Calculate MMF at tooth centers using proper electromagnetic logic.
        This is the tooth-based approach from the clean implementation.
        """
        tooth_mmf = np.zeros_like(phase_mmf)

        non_zero = self.find_first_nonzero(phase_mmf)
        number_same = self.count_same_value_around(phase_mmf, non_zero)

        for idx in range(self.N_slots):
            i = (non_zero + idx) % self.N_slots  # Start from non_zero and wrap around
            number_same_left = self.count_left_indexes(i, self.N_slots, phase_mmf)
            if idx == 0:  # First iteration (at non_zero index)
                tooth_mmf[i] = - number_same * phase_mmf[non_zero] + 2 * phase_mmf[i] * (number_same_left + 1)
            else:
                prev_i = (non_zero + idx - 1) % self.N_slots  # Previous index in the sequence
                tooth_mmf[i] = tooth_mmf[prev_i] + 2 * phase_mmf[i]
        return tooth_mmf

    def count_same_value_around(self, phase_mmf, index):
        """
        Count how many consecutive indices around the given index have the same MMF value.
        Returns the total count including the index itself, treating array as circular.
        """
        if phase_mmf[index] == 0:
            return 1
        
        target_value = phase_mmf[index]
        count = 1  # Count the index itself
        
        # Count forward (right side)
        i = (index + 1) % len(phase_mmf)
        while i != index and phase_mmf[i] == target_value:
            count += 1
            i = (i + 1) % len(phase_mmf)
        
        # Count backward (left side)
        i = (index - 1) % len(phase_mmf)
        while i != index and phase_mmf[i] == target_value:
            count += 1
            i = (i - 1) % len(phase_mmf)
        
        return count

    def count_left_indexes(self, current_index, total_length, phase_mmf):
        """
        Count how many consecutive indexes on the left side have the same value as the current index.
        Treats the array as a circular loop where index -1 is the same as last index.
        
        Args:
            current_index: The current index position
            total_length: Total length of the array
            phase_mmf: The array containing the MMF values
            
        Returns:
            Number of consecutive left indexes with the same value as current index
        """
        current_value = phase_mmf[current_index]
        count = 0
        
        # Start from immediate left neighbor and work backwards
        for offset in range(1, total_length):
            left_index = (current_index - offset) % total_length
            if phase_mmf[left_index] == current_value:
                count += 1
            else:
                break  # Stop at first non-matching value
        
        return count

    def find_first_nonzero(self, phase_mmf):
        """
        Find the index of the non-zero element that has the largest count of same values around it.
        Returns -1 if no non-zero element is found.
        """
        max_count = 0
        best_index = -1
        
        # Find all non-zero indices
        for i, value in enumerate(phase_mmf):
            if value != 0:
                # Count consecutive same values around this index
                count = self.count_same_value_around(phase_mmf, i)
                if count > max_count:
                    max_count = count
                    best_index = i
        
        return best_index

    def create_continuous_profiles(self, mmf_tooth_A, mmf_tooth_B, mmf_tooth_C):
        """
        Create continuous MMF profiles with linear interpolation in slot regions.
        Uses tooth centers with Tooth_arc for flat tops and Slot_arc for transitions.
        """
        resolution = 1000
        angles = np.linspace(0, 360, resolution, endpoint=False)

        # Initialize profiles
        mmf_profile_A = np.zeros_like(angles)
        mmf_profile_B = np.zeros_like(angles)
        mmf_profile_C = np.zeros_like(angles)

        # Tooth center angles
        tooth_centers = np.array([i * self.lepas for i in range(self.N_slots)])

        for i in range(self.N_slots):
            next_i = (i + 1) % self.N_slots
            
            # Current and next tooth center
            tc = tooth_centers[i]
            tc_next = tooth_centers[next_i] if next_i != 0 else 360
            
            # Tooth region extends Tooth_arc/2 on each side of center
            tooth_start = tc - self.Tooth_arc / 2
            tooth_end = tc + self.Tooth_arc / 2
            
            # Next tooth starts at next center - Tooth_arc/2
            next_tooth_start = tooth_centers[next_i] - self.Tooth_arc / 2
            if next_i == 0:
                next_tooth_start += 360
            
            # Apply constant MMF value across tooth region
            for idx, angle in enumerate(angles):
                # Handle wrap-around at 360 degrees
                if tooth_start < 0:
                    if angle >= tooth_start + 360 or angle < tooth_end:
                        mmf_profile_A[idx] = mmf_tooth_A[i]
                        mmf_profile_B[idx] = mmf_tooth_B[i]
                        mmf_profile_C[idx] = mmf_tooth_C[i]
                elif tooth_end > 360:
                    if angle >= tooth_start or angle < tooth_end - 360:
                        mmf_profile_A[idx] = mmf_tooth_A[i]
                        mmf_profile_B[idx] = mmf_tooth_B[i]
                        mmf_profile_C[idx] = mmf_tooth_C[i]
                else:
                    if tooth_start <= angle < tooth_end:
                        mmf_profile_A[idx] = mmf_tooth_A[i]
                        mmf_profile_B[idx] = mmf_tooth_B[i]
                        mmf_profile_C[idx] = mmf_tooth_C[i]
                
                # Linear interpolation in slot region
                if tooth_end <= angle < next_tooth_start or (next_i == 0 and angle >= tooth_end):
                    # Calculate interpolation factor
                    slot_width = next_tooth_start - tooth_end
                    if slot_width < 0:
                        slot_width += 360
                    
                    if angle >= tooth_end:
                        t = (angle - tooth_end) / slot_width if slot_width > 0 else 0
                    else:
                        t = (angle + 360 - tooth_end) / slot_width if slot_width > 0 else 0
                    
                    t = min(max(t, 0), 1)  # Clamp between 0 and 1
                    
                    mmf_profile_A[idx] = (1 - t) * mmf_tooth_A[i] + t * mmf_tooth_A[next_i]
                    mmf_profile_B[idx] = (1 - t) * mmf_tooth_B[i] + t * mmf_tooth_B[next_i]
                    mmf_profile_C[idx] = (1 - t) * mmf_tooth_C[i] + t * mmf_tooth_C[next_i]

        # Convert to (angle, value) tuples
        return [(angles[i], mmf_profile_A[i]) for i in range(len(angles))], \
               [(angles[i], mmf_profile_B[i]) for i in range(len(angles))], \
               [(angles[i], mmf_profile_C[i]) for i in range(len(angles))]

    def _sum_continuous_profiles(self, prof1, prof2):
        """
        Sum two continuous profiles maintaining the double layer logic.
        Handles both tuple format [(angle, value), ...] and numpy array format.
        """
        # Check if profiles are numpy arrays or list of tuples
        if isinstance(prof1, np.ndarray):
            # Direct numpy array addition
            return prof1 + prof2
        else:
            # Extract angles and values from tuple format
            angles1, values1 = zip(*prof1)
            angles2, values2 = zip(*prof2)
            
            # Since both profiles have the same angular resolution, we can sum directly
            return [(angles1[i], values1[i] + values2[i]) for i in range(len(angles1))]

    def _calculate_resultant(self, prof_A, prof_B, prof_C):
        """
        Calculate the resultant MMF profile using the formula: A - (B+C)/2
        """
        # Extract angles and values
        angles_A, values_A = zip(*prof_A)
        angles_B, values_B = zip(*prof_B)
        angles_C, values_C = zip(*prof_C)
        
        # Calculate resultant values: A - (B+C)/2
        resultant_values = [values_A[i] - (values_B[i] + values_C[i])/2 for i in range(len(values_A))]
        
        return [(angles_A[i], resultant_values[i]) for i in range(len(angles_A))]

    def _calculate_resultant_new_formula(self, prof_A, prof_B, prof_C):
        """
        Calculate the resultant MMF profile using the formula: A*sin(Wt) + B*sin(Wt+120°) + C*sin(Wt-120°)
        """
        # Extract angles and values
        angles_A, values_A = zip(*prof_A)
        angles_B, values_B = zip(*prof_B)
        angles_C, values_C = zip(*prof_C)
        
        # Convert Wt to radians
        wt_rad = np.radians(self.Wt)
        
        # Calculate trigonometric factors
        sin_wt = np.sin(wt_rad)
        sin_wt_120 = np.sin(wt_rad + np.radians(120))
        sin_wt_minus_120 = np.sin(wt_rad - np.radians(120))
        
        # Calculate resultant values: A*sin(Wt) + B*sin(Wt+120°) + C*sin(Wt-120°)
        resultant_values = [values_A[i] * sin_wt + values_B[i] * sin_wt_120 + values_C[i] * sin_wt_minus_120 
                           for i in range(len(values_A))]
        
        return [(angles_A[i], resultant_values[i]) for i in range(len(angles_A))]

    def get_profile_data(self, phase_name, layer=None):
        """
        Return the profile data for a specific phase and layer.
        """
        if phase_name == 'resultant':
            profile = getattr(self, 'mmf_profile_resultant', None)
        elif layer:
            attr_name = f'mmf_profile_{phase_name}_{layer}'
            profile = getattr(self, attr_name, None)
        else:
            # Try phase_profiles dict first (multi-phase), then legacy attributes
            if phase_name in self.phase_profiles:
                profile = self.phase_profiles[phase_name]
            else:
                attr_name = f'mmf_profile_{phase_name}'
                profile = getattr(self, attr_name, None)
        
        if profile is not None:
            # Check if profile is numpy array or list of tuples
            if isinstance(profile, np.ndarray):
                # Generate angles for numpy array format
                resolution = len(profile)
                angles = np.linspace(0, 360, resolution, endpoint=False)
                return angles, profile
            else:
                # Tuple format [(angle, value), ...]
                angles, values = zip(*profile)
                return angles, values
        return None, None

    def update_slot_arc(self, new_slot_arc):
        """Update slot arc angle and recalculate MMF profiles"""
        self.Slot_arc = new_slot_arc
        self.Tooth_arc = (360 / self.N_slots) - self.Slot_arc
        self.lepas = self.Tooth_arc + self.Slot_arc
        
        # Recalculate MMF profiles with new slot arc
        if self.matrix is not None:
            self.set_connection_matrix(self.matrix)

    def update_turns(self, new_turns):
        """Update number of turns and recalculate MMF profiles"""
        self.N = new_turns
        
        # Recalculate MMF profiles with new turns
        if self.matrix is not None:
            self.set_connection_matrix(self.matrix)

    def update_current(self, new_current):
        """Update current values for all phases and recalculate MMF profiles"""
        self.Ia = new_current
        self.Ib = new_current
        self.Ic = new_current
        
        # Recalculate MMF profiles with new current
        if self.matrix is not None:
            self.set_connection_matrix(self.matrix)

    def update_wt_angle(self, new_wt):
        """Update Wt angle and recalculate MMF profiles"""
        self.Wt = new_wt
        
        # Recalculate MMF profiles with new Wt angle
        if self.matrix is not None:
            self.set_connection_matrix(self.matrix)

    def get_tooth_mmf_data(self):
        """
        Export tooth MMF data for resultant only.
        Returns a dictionary with tooth data for resultant.
        """
        if self.matrix is None:
            return None
            
        # Get the original phase MMF arrays (before tooth logic calculation)
        rows = self.matrix.shape[0]
        if rows == 3:
            A, B, C = self.matrix
            phases_mmf = {
                'A': A * self.Ia * self.N / 2,
                'B': B * self.Ib * self.N / 2,
                'C': C * self.Ic * self.N / 2
            }
        elif rows == 6:
            A, B, C, A2, B2, C2 = self.matrix
            A_sum, B_sum, C_sum = A + A2, B + B2, C + C2
            phases_mmf = {
                'A': A_sum * self.Ia * self.N / 2,
                'B': B_sum * self.Ib * self.N / 2,
                'C': C_sum * self.Ic * self.N / 2
            }
        else:
            return None
            
        # Calculate tooth MMF for each phase
        tooth_mmf_data = {}
        for phase_name, phase_mmf in phases_mmf.items():
            tooth_mmf = self.calculate_mmf_tooth_logic(phase_mmf)
            tooth_mmf_data[phase_name] = tooth_mmf.tolist()
            
        # Calculate resultant using new formula: A*sin(Wt) + B*sin(Wt+120°) + C*sin(Wt-120°)
        if 'A' in tooth_mmf_data and 'B' in tooth_mmf_data and 'C' in tooth_mmf_data:
            # Convert Wt to radians
            wt_rad = np.radians(self.Wt)
            
            # Calculate trigonometric factors
            sin_wt = np.sin(wt_rad)
            sin_wt_120 = np.sin(wt_rad + np.radians(120))
            sin_wt_minus_120 = np.sin(wt_rad - np.radians(120))
            
            resultant_mmf = [tooth_mmf_data['A'][i] * sin_wt + 
                           tooth_mmf_data['B'][i] * sin_wt_120 + 
                           tooth_mmf_data['C'][i] * sin_wt_minus_120 
                           for i in range(len(tooth_mmf_data['A']))]
            return {
                'Resultant': {
                    'tooth_mmf': resultant_mmf
                }
            }
            
        return None

    def calculate_harmonics(self, D=1.0, nu_max=50, ws=0, phase='resultant'):
        """
        Calculate the MMF harmonics using Fourier analysis on tooth MMF values.
        Adapted to work with the tooth-based MMF calculation approach.
        
        Parameters:
        -----------
        D : float
            Stator airgap diameter (default: 1.0 for normalized analysis)
        nu_max : int
            Maximum harmonic order to compute (default: 50)
        ws : float
            Slot opening width (default: 0 for zero slot width)
        phase : str
            Which phase to analyze: 'A', 'B', 'C', or 'resultant' (default: 'resultant')
            
        Returns:
        --------
        dict : Dictionary containing harmonics data
        """
        import math
        
        if self.matrix is None:
            return None
        
        Q = self.N_slots
        
        # Get the actual MMF values at tooth centers based on phase selection
        if phase == 'resultant':
            # Get the resultant MMF profile
            if not hasattr(self, 'mmf_profile_resultant') or self.mmf_profile_resultant is None:
                return None
            
            # Extract values from the continuous profile at tooth positions
            angles, values = zip(*self.mmf_profile_resultant)
            angles = np.array(angles)
            values = np.array(values)
            
            # Sample at tooth centers
            tooth_centers = np.arange(0, Q) * (360 / Q)
            tooth_mmf = []
            for tc in tooth_centers:
                # Find closest angle in the profile
                idx = np.argmin(np.abs(angles - tc))
                tooth_mmf.append(values[idx])
            tooth_mmf = np.array(tooth_mmf)
            
        else:
            # Single phase analysis - get phase MMF at teeth
            phase_upper = phase.upper()
            if phase_upper not in ['A', 'B', 'C']:
                print(f'HARMONICS ERROR: Invalid phase "{phase}"')
                return None
            
            # Get the phase profile
            profile_attr = f'mmf_profile_{phase_upper}'
            if not hasattr(self, profile_attr):
                return None
            
            profile = getattr(self, profile_attr)
            if profile is None:
                return None
            
            # Extract values from the continuous profile at tooth positions
            angles, values = zip(*profile)
            angles = np.array(angles)
            values = np.array(values)
            
            # Sample at tooth centers
            tooth_centers = np.arange(0, Q) * (360 / Q)
            tooth_mmf = []
            for tc in tooth_centers:
                # Find closest angle in the profile
                idx = np.argmin(np.abs(angles - tc))
                tooth_mmf.append(values[idx])
            tooth_mmf = np.array(tooth_mmf)
        
        # Now we have tooth_mmf values at Q tooth positions
        # Apply Discrete Fourier Transform
        max_mmf = np.max(np.abs(tooth_mmf))
        
        if max_mmf < 1e-10:
            # No MMF content
            return {
                'harmonics': list(range(1, nu_max + 1)),
                'a': [0] * nu_max,
                'b': [0] * nu_max,
                'amplitude': [0] * nu_max,
                'phase': [0] * nu_max,
                'mmf_amplitude': [0] * nu_max,
                'percentage': [0] * nu_max,
                'fundamental': 0,
                'phase_analyzed': phase
            }
        
        harmonics = []
        a_coeffs = []
        b_coeffs = []
        amplitudes = []
        phases = []
        mmf_amplitudes = []
        
        # Fourier analysis on tooth MMF values
        for nu in range(1, nu_max + 1):
            # DFT coefficients for harmonic nu
            a_sum = 0
            b_sum = 0
            
            for j in range(Q):
                theta = 2 * math.pi * j / Q  # Angular position of tooth j
                a_sum += tooth_mmf[j] * math.cos(nu * theta)
                b_sum += tooth_mmf[j] * math.sin(nu * theta)
            
            # Normalize by number of samples
            a_nu = (2.0 / Q) * a_sum
            b_nu = (2.0 / Q) * b_sum
            
            # Set near-zero values to exactly zero
            if abs(a_nu) < 1e-8:
                a_nu = 0
            if abs(b_nu) < 1e-8:
                b_nu = 0
            
            # Calculate amplitude: sqrt(a² + b²)
            amplitude = math.sqrt(a_nu**2 + b_nu**2)
            
            # Calculate phase angle
            if amplitude < 1e-10:
                phi = 0
            else:
                phi = math.atan2(b_nu, a_nu)
            
            harmonics.append(nu)
            a_coeffs.append(a_nu)
            b_coeffs.append(b_nu)
            amplitudes.append(amplitude)
            phases.append(phi)
            mmf_amplitudes.append(amplitude)
        
        # Calculate percentage of fundamental
        fundamental_amplitude = mmf_amplitudes[0] if len(mmf_amplitudes) > 0 else 1
        if fundamental_amplitude > 1e-10:
            percentages = [(amp / fundamental_amplitude * 100) for amp in mmf_amplitudes]
        else:
            percentages = [0] * len(mmf_amplitudes)
        
        return {
            'harmonics': harmonics,
            'a': a_coeffs,
            'b': b_coeffs,
            'amplitude': amplitudes,
            'phase': phases,
            'mmf_amplitude': mmf_amplitudes,
            'percentage': percentages,
            'fundamental': fundamental_amplitude,
            'phase_analyzed': phase
        }
        
        # Calculate percentage of fundamental
        fundamental_amplitude = mmf_amplitudes[0] if len(mmf_amplitudes) > 0 else 1
        if fundamental_amplitude > 0:
            percentages = [(amp / fundamental_amplitude * 100) for amp in mmf_amplitudes]
        else:
            percentages = [0] * len(mmf_amplitudes)
        
        return {
            'harmonics': harmonics,
            'a': a_coeffs,
            'b': b_coeffs,
            'amplitude': amplitudes,
            'phase': phases,
            'mmf_amplitude': mmf_amplitudes,
            'percentage': percentages,
            'fundamental': fundamental_amplitude,
            'phase_analyzed': phase
        }
    
    def get_harmonic_summary(self, D=1.0, nu_max=50, phase='resultant'):
        """
        Get a formatted summary of the harmonic analysis.
        
        Returns:
        --------
        str : Formatted text summary of harmonic content
        """
        harmonics_data = self.calculate_harmonics(D=D, nu_max=nu_max, phase=phase)
        
        if harmonics_data is None:
            return "No harmonics data available. Please compute MMF first."
        
        summary = []
        summary.append("=" * 80)
        summary.append(f"MMF HARMONIC ANALYSIS - Phase: {harmonics_data['phase_analyzed']}")
        summary.append("=" * 80)
        summary.append(f"Fundamental MMF Amplitude: {harmonics_data['fundamental']:.2f} A-turns")
        summary.append(f"Number of harmonics analyzed: {len(harmonics_data['harmonics'])}")
        summary.append("")
        summary.append("Significant Harmonics (>1% of fundamental):")
        summary.append("-" * 80)
        summary.append(f"{'Order':<8} {'Amplitude':<15} {'% of Fund.':<15} {'Phase (deg)':<15}")
        summary.append("-" * 80)
        
        for i, nu in enumerate(harmonics_data['harmonics']):
            if harmonics_data['percentage'][i] > 1.0:  # Show only harmonics > 1%
                amp = harmonics_data['mmf_amplitude'][i]
                pct = harmonics_data['percentage'][i]
                phase_deg = np.degrees(harmonics_data['phase'][i])
                summary.append(f"{nu:<8} {amp:<15.2f} {pct:<15.2f} {phase_deg:<15.2f}")
        
        summary.append("-" * 80)
        
        # Calculate Total Harmonic Distortion (THD)
        if len(harmonics_data['mmf_amplitude']) > 1:
            fundamental = harmonics_data['mmf_amplitude'][0]
            harmonics_sum = sum([amp**2 for amp in harmonics_data['mmf_amplitude'][1:]])
            thd = np.sqrt(harmonics_sum) / fundamental * 100 if fundamental > 0 else 0
            summary.append(f"Total Harmonic Distortion (THD): {thd:.2f}%")
        
        summary.append("=" * 80)
        
        return "\n".join(summary)

    def create_continuous_profiles_multi(self, phase_mmf_tooth_list):
        """
        Create continuous MMF profiles for multiple phases.
        Returns list of profiles, one per phase.
        """
        resolution = 1000
        angles = np.linspace(0, 360, resolution, endpoint=False)
        tooth_centers = np.array([i * self.lepas for i in range(self.N_slots)])
        
        profiles = []
        for phase_mmf_tooth in phase_mmf_tooth_list:
            profile = np.zeros_like(angles)
            
            for i in range(self.N_slots):
                next_i = (i + 1) % self.N_slots
                tc = tooth_centers[i]
                tooth_start = tc - self.Tooth_arc / 2
                tooth_end = tc + self.Tooth_arc / 2
                next_tooth_start = tooth_centers[next_i] - self.Tooth_arc / 2
                if next_i == 0:
                    next_tooth_start += 360
                
                for idx, angle in enumerate(angles):
                    # Handle wrap-around
                    if tooth_start < 0:
                        if angle >= tooth_start + 360 or angle < tooth_end:
                            profile[idx] = phase_mmf_tooth[i]
                    elif tooth_end > 360:
                        if angle >= tooth_start or angle < tooth_end - 360:
                            profile[idx] = phase_mmf_tooth[i]
                    else:
                        if tooth_start <= angle < tooth_end:
                            profile[idx] = phase_mmf_tooth[i]
                    
                    # Linear interpolation in slot region
                    if tooth_end <= angle < next_tooth_start or (next_i == 0 and angle >= tooth_end):
                        slot_width = next_tooth_start - tooth_end
                        if slot_width > 0:
                            t = (angle - tooth_end) / slot_width
                            profile[idx] = phase_mmf_tooth[i] * (1 - t) + phase_mmf_tooth[next_i] * t
            
            profiles.append(profile)
        
        return profiles

    def calculate_resultant_multi_phase(self, phase_profiles):
        """
        Calculate resultant MMF for m-phase system using proper phase shifts.
        For m phases, phase angle = 2*pi*k/m for phase k
        """
        if not phase_profiles:
            return np.zeros(1000)
        
        resolution = len(phase_profiles[0])
        resultant = np.zeros(resolution)
        
        m = len(phase_profiles)
        # Convert Wt from degrees to radians
        Wt_rad = np.radians(self.Wt)
        
        for k, profile in enumerate(phase_profiles):
            # Phase angle for phase k: 2*pi*k/m
            phase_shift = 2 * np.pi * k / m
            # Current for this phase at time Wt
            current_factor = np.sin(Wt_rad - phase_shift)
            resultant += profile * current_factor
        
        return resultant

