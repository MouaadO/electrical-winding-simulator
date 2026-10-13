from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, QPlainTextEdit
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np


def setup_voltage_checker_tab(main_window):
    main_window.voltage_tab = VoltageFromWindingTab(main_window)
    layout = QVBoxLayout()
    layout.addWidget(main_window.voltage_tab)
    main_window.tab_voltage.setLayout(layout)


class VoltageFromWindingTab(QWidget):
    """
    Computes the m-phase induced EMF phasors directly from the current
    winding connection matrix and slot/pole configuration. Results are
    normalized (relative units) to evaluate balance and phase spacing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.num_phases = 3  # Default, will be updated from winding
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header / actions
        header = QHBoxLayout()
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { font-size: 14px; }")
        recompute_btn = QPushButton("Recompute from Winding")
        recompute_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 5px 15px; }")
        recompute_btn.clicked.connect(self.recompute_from_winding)
        header.addWidget(self.info_label)
        header.addStretch()
        header.addWidget(recompute_btn)
        layout.addLayout(header)

        # Summary
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignLeft)
        self.summary_label.setStyleSheet("QLabel { font-size: 14px; }")
        layout.addWidget(self.summary_label)

        # Main content: Calculations on left, Drawing on right
        content_layout = QHBoxLayout()
        
        # Left side: Detailed calculations
        self.details_group = QGroupBox("Calculation Details")
        self.details_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; }")
        details_layout = QVBoxLayout(self.details_group)
        self.details_text = QPlainTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("QPlainTextEdit { background-color: #1e1e1e; color: #dddddd; font-family: Consolas, monospace; font-size: 13px; }")
        details_layout.addWidget(self.details_text)
        content_layout.addWidget(self.details_group)

        # Right side: Phasor plot
        plot_group = QGroupBox("EMF Phasor Diagram")
        plot_group.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; }")
        plot_layout = QVBoxLayout(plot_group)
        self.canvas_phasor = FigureCanvas(Figure(figsize=(6, 5)))
        self.ax_phasor = self.canvas_phasor.figure.add_subplot(111)
        plot_layout.addWidget(self.canvas_phasor)
        content_layout.addWidget(plot_group)

        layout.addLayout(content_layout)

        # Initial compute
        self.recompute_from_winding()

    @staticmethod
    def _wrap_angle_deg(a):
        w = (a + 180.0) % 360.0 - 180.0
        return 180.0 if np.isclose(w, -180.0) else w

    def _phasors_from_matrix(self, M, p_pairs, is_double_layer=None):
        """
        Build fundamental EMF phasors per phase from slot assignment matrix.
        E_phase ∝ sum s_n * exp(j * θ_e(n)), where θ_e(n) = 360 * p_pairs * n / Q.
        """
        rows, Q = M.shape
        
        # Determine if double layer: use explicit parameter if provided, otherwise infer
        if is_double_layer is None:
            # Fallback: assume double layer if even number of rows
            is_double_layer = (rows % 2 == 0)
        
        # Collapse double-layer rows if needed
        phase_arrays = []
        if is_double_layer:
            m = rows // 2  # Number of phases for double layer
            for i in range(m):
                phase_arrays.append(M[i] + M[m + i])
        else:  # Single layer
            m = rows  # Number of phases for single layer
            for i in range(m):
                phase_arrays.append(M[i])

        n = np.arange(Q)
        theta_deg = (360.0 * p_pairs * n) / Q
        theta = np.deg2rad(theta_deg)
        ejth = np.exp(1j * theta)

        # Compute phasor for each phase
        phasors = [np.sum(phase_array * ejth) for phase_array in phase_arrays]
        return phasors

    def _adjust_phase_A_signs_q_four_thirds(self, M, slots, p_pairs):
        """
        If q ≈ 4/3, adjust Phase A signs so that:
        - Ea keeps its original angle (phase untouched) approximately
        - |Ea| matches the target magnitude (ideally equal to |Eb| and |Ec|)
        - Only Phase A signs are changed; magnitudes per slot (0/1/2) preserved
        - Works for single and double layer matrices

        Strategy: greedy flip of slot signs based on projections onto Ea angle
        to reduce parallel magnitude error and orthogonal component simultaneously.
        """
        try:
            rows, Q = M.shape
            actual_poles = int(getattr(self.parent, 'poles_spin').value()) * 2
            spp = slots / actual_poles
            q_val = spp / 3.0
            # Apply only when q is very close to 4/3
            if not np.isclose(q_val, 4.0/3.0, atol=1e-6):
                return M

            # Compute current Ea angle
            Ea, Eb, Ec = self._phasors_from_matrix(M, p_pairs, is_double_layer=None)
            phi = np.angle(Ea)

            # Electrical angle per slot
            n = np.arange(Q)
            theta = np.deg2rad((360.0 * p_pairs * n) / Q)
            # Build magnitude per slot for Phase A (collapsed if double layer)
            if rows == 6:
                A_top = M[0].copy()
                A_bot = M[3].copy()
                A_mag = np.abs(A_top + A_bot).astype(int)
            else:
                A_mag = np.abs(M[0]).astype(int)

            # Compute target magnitude for Ea: aim to equalize with B/C
            mag_Eb, mag_Ec = np.abs(Eb), np.abs(Ec)
            if np.isclose(mag_Eb, mag_Ec, rtol=1e-3, atol=1e-6):
                M_target = float((mag_Eb + mag_Ec) / 2.0)
            else:
                M_target = float((np.abs(Ea) + mag_Eb + mag_Ec) / 3.0)

            # Per-slot projections relative to Ea angle (angle may change; magnitude goal only)
            d = theta - phi
            p = A_mag * np.cos(d)  # parallel component

            # Initial sign choice: align to positive projection
            x = np.zeros(Q, dtype=int)
            for k in range(Q):
                x[k] = 0 if A_mag[k] == 0 else (1 if p[k] >= 0 else -1)

            S_par = float(np.sum(x * p))
            tol_par = max(1e-6, 0.005 * max(1.0, M_target))

            # Greedy magnitude matching: flip slots to move S_par toward M_target
            # Prefer flipping smallest |p[k]| when reducing, largest when increasing
            max_iters = Q * 3
            it = 0
            while it < max_iters and abs(S_par - M_target) > tol_par:
                if S_par > M_target:
                    # Reduce sum: flip a currently positive contributor with smallest |p|
                    candidates = [k for k in range(Q) if A_mag[k] != 0 and x[k] == 1 and p[k] > 0]
                    if not candidates:
                        break
                    k_sel = min(candidates, key=lambda k: abs(p[k]))
                    S_par -= 2.0 * p[k_sel]
                    x[k_sel] = -1
                else:
                    # Increase sum: flip a currently negative contributor with largest |p|
                    candidates = [k for k in range(Q) if A_mag[k] != 0 and x[k] == -1 and p[k] < 0]
                    if not candidates:
                        break
                    k_sel = max(candidates, key=lambda k: abs(p[k]))
                    S_par += 2.0 * abs(p[k_sel])
                    x[k_sel] = 1
                it += 1

            # Build adjusted matrix with chosen signs
            M_new = M.copy()
            if rows == 6:
                for k in range(Q):
                    if A_mag[k] == 0:
                        continue
                    desired_sign = int(x[k])
                    # If both layers contribute (mag=2), set both signs equal
                    if A_mag[k] == 2:
                        M_new[0][k] = desired_sign
                        M_new[3][k] = desired_sign
                    else:
                        # Only the non-zero layer gets the sign
                        if A_top[k] != 0:
                            M_new[0][k] = desired_sign
                        if A_bot[k] != 0:
                            M_new[3][k] = desired_sign
            else:
                for k in range(Q):
                    if A_mag[k] == 0:
                        continue
                    M_new[0][k] = int(x[k])

            return M_new
        except Exception:
            return M

    def _balance_real_slots_signs(self, M, p_pairs, slots):
        """
        For slots where the electrical angle has zero imaginary contribution
        (sin(theta) ≈ 0 → theta ≈ 0°, 180°), rearrange signs so the per-phase
        sum over those slots is ≈ 0. This reduces real-axis bias and helps
        push phasors toward 120° spacing.

        Preserves magnitudes (0/1/2) and only flips signs for those slots.
        Works for single and double-layer matrices.
        """
        try:
            rows, Q = M.shape
            # Electrical angle per slot
            n = np.arange(Q)
            theta = np.deg2rad((360.0 * p_pairs * n) / Q)
            real_idx = np.where(np.isclose(np.sin(theta), 0.0, atol=1e-9))[0]
            if len(real_idx) == 0:
                return M

            M_new = M.copy()

            def balance_phase(layer_top_idx, layer_bot_idx=None):
                if layer_bot_idx is None:
                    # Single layer
                    mags = np.abs(M[layer_top_idx]).astype(int)
                    idxs = [k for k in real_idx if mags[k] != 0]
                    if not idxs:
                        return
                    # Greedy near-zero sum assignment based on magnitudes
                    # Sort by descending magnitude for better balancing
                    idxs_sorted = sorted(idxs, key=lambda k: mags[k], reverse=True)
                    S = 0
                    for k in idxs_sorted:
                        s = -1 if S >= 0 else 1
                        M_new[layer_top_idx][k] = s
                        S += s * mags[k]
                    return
                else:
                    # Double layer
                    mags_top = np.abs(M[layer_top_idx]).astype(int)
                    mags_bot = np.abs(M[layer_bot_idx]).astype(int)
                    idxs_info = []
                    for k in real_idx:
                        mt, mb = mags_top[k], mags_bot[k]
                        m = mt + mb
                        if m == 0:
                            continue
                        idxs_info.append((k, m, mt, mb))
                    if not idxs_info:
                        return
                    # Sort by descending total magnitude
                    idxs_info.sort(key=lambda t: t[1], reverse=True)
                    S = 0
                    for k, m, mt, mb in idxs_info:
                        s = -1 if S >= 0 else 1
                        if m == 2:
                            M_new[layer_top_idx][k] = s
                            M_new[layer_bot_idx][k] = s
                        else:
                            if mt == 1:
                                M_new[layer_top_idx][k] = s
                            if mb == 1:
                                M_new[layer_bot_idx][k] = s
                        S += s * m

            # Only balance Phase A, keep B and C intact
            if rows == 6:
                balance_phase(0, 3)
            else:
                balance_phase(0)

            return M_new
        except Exception:
            return M

    def _balance_phase_A_real_slots(self, M, p_pairs):
        """
        Balance only Phase A signs on slots where sin(theta)≈0 so that the
        sum of contributions over these slots is ≈ 0. Does not modify B/C.
        """
        rows, Q = M.shape
        n = np.arange(Q)
        theta = np.deg2rad((360.0 * p_pairs * n) / Q)
        real_idx = np.where(np.isclose(np.sin(theta), 0.0, atol=1e-9))[0]
        # cos sign for real-angle slots (±1)
        cos_sign = np.sign(np.cos(theta))
        if len(real_idx) == 0:
            return M

        M_new = M.copy()

        if rows == 6:
            A_top = M[0].copy()
            A_bot = M[3].copy()
            mags_top = np.abs(A_top).astype(int)
            mags_bot = np.abs(A_bot).astype(int)
            entries = []
            for k in real_idx:
                mt, mb = mags_top[k], mags_bot[k]
                m = mt + mb
                if m == 0:
                    continue
                entries.append((k, m, mt, mb, int(cos_sign[k]) if cos_sign[k] != 0 else 1))
            if not entries:
                return M
            entries.sort(key=lambda t: t[1], reverse=True)
            S = 0
            for k, m, mt, mb, csgn in entries:
                # choose t_k to reduce |S|: t_k in {±1}
                t = -1 if S >= 0 else 1
                s = t * csgn  # actual phase sign to apply
                if m == 2:
                    M_new[0][k] = s
                    M_new[3][k] = s
                else:
                    if mt == 1:
                        M_new[0][k] = s
                    if mb == 1:
                        M_new[3][k] = s
                S += t * m
        else:
            mags = np.abs(M[0]).astype(int)
            idxs = [k for k in real_idx if mags[k] != 0]
            if not idxs:
                return M
            idxs.sort(key=lambda k: mags[k], reverse=True)
            S = 0
            for k in idxs:
                t = -1 if S >= 0 else 1
                csgn = int(cos_sign[k]) if cos_sign[k] != 0 else 1
                s = t * csgn
                M_new[0][k] = s
                S += t * mags[k]

        return M_new

    def _balance_phase_A_imag_slots(self, M, p_pairs):
        """
        Balance only Phase A signs on slots where cos(theta)≈0 (θ≈90°, 270°)
        so that the sum of imaginary contributions over these slots is ≈ 0.
        Does not modify B/C; preserves per-slot magnitudes and double-layer.
        """
        rows, Q = M.shape
        n = np.arange(Q)
        theta = np.deg2rad((360.0 * p_pairs * n) / Q)
        imag_idx = np.where(np.isclose(np.cos(theta), 0.0, atol=1e-9))[0]
        if len(imag_idx) == 0:
            return M

        # sin sign for imaginary-angle slots (±1)
        sin_sign = np.sign(np.sin(theta))

        M_new = M.copy()

        if rows == 6:
            A_top = M[0].copy()
            A_bot = M[3].copy()
            mags_top = np.abs(A_top).astype(int)
            mags_bot = np.abs(A_bot).astype(int)
            entries = []
            for k in imag_idx:
                mt, mb = mags_top[k], mags_bot[k]
                m = mt + mb
                if m == 0:
                    continue
                entries.append((k, m, mt, mb, int(sin_sign[k]) if sin_sign[k] != 0 else 1))
            if not entries:
                return M
            entries.sort(key=lambda t: t[1], reverse=True)
            S = 0
            for k, m, mt, mb, sgn in entries:
                t = -1 if S >= 0 else 1
                s = t * sgn
                if m == 2:
                    M_new[0][k] = s
                    M_new[3][k] = s
                else:
                    if mt == 1:
                        M_new[0][k] = s
                    if mb == 1:
                        M_new[3][k] = s
                S += t * m
        else:
            mags = np.abs(M[0]).astype(int)
            idxs = [k for k in imag_idx if mags[k] != 0]
            if not idxs:
                return M
            idxs.sort(key=lambda k: mags[k], reverse=True)
            S = 0
            for k in idxs:
                t = -1 if S >= 0 else 1
                sgn = int(sin_sign[k]) if sin_sign[k] != 0 else 1
                s = t * sgn
                M_new[0][k] = s
                S += t * mags[k]

        return M_new

    def recompute_from_winding(self):
        # Gather winding data from main window
        mw = self.parent
        
        # Get number of phases
        phases = int(getattr(mw, 'phases_spin', None).value()) if hasattr(mw, 'phases_spin') else 3
        self.num_phases = phases
        
        # Get matrix from stator drawing instead of connection_tab
        matrix = None
        is_double_layer = False
        if hasattr(mw, 'stator_drawing') and mw.stator_drawing.winding_obj:
            is_double_layer = mw.stator_drawing.is_double_layer
            if is_double_layer:
                matrix = mw.stator_drawing.get_double_layer_matrix()
            else:
                matrices = mw.stator_drawing.winding_obj.get_slot_matrices(normalize=True)
                matrix = np.array(matrices) if matrices else None
        
        if matrix is None:
            self.info_label.setText("No winding matrix yet. Change parameters to generate winding.")
            return

        Q = int(matrix.shape[1])
        p_pairs = int(getattr(mw, 'poles_spin').value())  # pair of poles

        # Special handling for q ≈ 4/3: balance signs at real-angle slots per phase
        slots = int(getattr(self.parent, 'slots_spin').value())
        actual_poles = 2 * int(getattr(self.parent, 'poles_spin').value())
        q_val = (slots / actual_poles) / phases
        note = ""
        if np.isclose(q_val, 4.0/3.0, atol=1e-6):
            # Balance only Phase A over real and imaginary angle slots (analysis-only)
            m1 = self._balance_phase_A_real_slots(matrix, p_pairs)
            m2 = self._balance_phase_A_imag_slots(m1, p_pairs)
            balanced_matrix = m2
            if balanced_matrix is not matrix:
                # Use adjusted copy for phasor analysis only
                matrix_for_analysis = balanced_matrix
                # Sanity check: ensure B and C are unchanged in the adjusted copy
                try:
                    rows = matrix.shape[0]
                    bc_unchanged = True
                    if rows == 6:
                        bc_unchanged &= np.array_equal(matrix[1], balanced_matrix[1]) and np.array_equal(matrix[4], balanced_matrix[4])
                        bc_unchanged &= np.array_equal(matrix[2], balanced_matrix[2]) and np.array_equal(matrix[5], balanced_matrix[5])
                    else:
                        bc_unchanged &= np.array_equal(matrix[1], balanced_matrix[1]) and np.array_equal(matrix[2], balanced_matrix[2])
                    note = " (Phase A real+imag slots balanced for analysis; B/C untouched)" if bc_unchanged else " (Warning: B/C changed in adjusted copy)"
                except Exception:
                    note = " (Phase A real+imag slots balanced for analysis)"
            else:
                matrix_for_analysis = matrix
        else:
            matrix_for_analysis = matrix

        # For 3-phase, do not auto-swap B and C; keep original sequence
        if phases == 3:
            phasors_test = self._phasors_from_matrix(matrix_for_analysis, p_pairs, is_double_layer)
            Ea_test, Eb_test, Ec_test = phasors_test[0], phasors_test[1], phasors_test[2]
            a = np.exp(1j * 2 * np.pi / 3)
            a2 = a ** 2
            V1_test = (Ea_test + a * Eb_test + a2 * Ec_test) / 3.0
            V2_test = (Ea_test + a2 * Eb_test + a * Ec_test) / 3.0
            # If negative sequence is detected, preserve as-is and just annotate
            if np.abs(V2_test) > np.abs(V1_test) and np.abs(V2_test) > 1e-6:
                note += " (Negative sequence detected; B and C not swapped)"

        phasors = self._phasors_from_matrix(matrix_for_analysis, p_pairs, is_double_layer)

        # Verify phasor count matches expected phases
        if len(phasors) != phases:
            self.info_label.setText(f"Error: Expected {phases} phasors but got {len(phasors)}. Regenerate winding.")
            return

        # Magnitudes and angles for all phases
        mags = np.array([np.abs(p) for p in phasors])
        angs = np.array([np.rad2deg(np.angle(p)) for p in phasors])

        mean_mag = float(np.mean(mags)) if np.any(mags) else 0.0
        dev_pct = 100.0 * np.abs(mags - mean_mag) / (mean_mag if mean_mag != 0 else 1.0)
        max_dev = float(np.max(dev_pct)) if mean_mag != 0 else 0.0

        # Relative phase spacing (should be 360°/m between adjacent phases)
        expected_spacing = 360.0 / phases
        phase_diffs = []
        phase_errs = []
        for i in range(phases):
            next_i = (i + 1) % phases
            diff = self._wrap_angle_deg(angs[next_i] - angs[i])
            phase_diffs.append(diff)
            # Error from expected spacing
            err = min(abs(diff - expected_spacing), abs(diff + expected_spacing))
            phase_errs.append(err)
        phase_errs = np.array(phase_errs)

        # Skip symmetrical components calculation per request (no V0/V1/V2/VUF)

        # Info and summary
        self.info_label.setText(f"Phases: {phases} | Slots: {Q} | Pair of poles: {p_pairs}{note}")
        
        # Check balance criteria
        mag_ok = max_dev <= 5.0
        phase_ok = np.max(phase_errs) <= 2.0
        verdict_ok = mag_ok and phase_ok
        color = "green" if verdict_ok else "red"
        verdict_text = "OK (balanced)" if verdict_ok else "IMBALANCED"

        # Generate phase names
        phase_names = [chr(65 + i) for i in range(phases)]
        
        # Magnitude summary
        mag_str = ", ".join([f"{phase_names[i]}={mags[i]:.3f}" for i in range(phases)])
        mag_summary = f"Magnitudes (rel): {mag_str}; mean={mean_mag:.3f}, max dev={max_dev:.2f}%"
        
        # Phase spacing summary
        diff_str = ", ".join([f"{phase_names[i]}-{phase_names[(i+1)%phases]}={phase_diffs[i]:.2f}°" for i in range(phases)])
        phase_summary = f"Phase diffs: {diff_str}; max err to {expected_spacing:.1f}°={np.max(phase_errs):.2f}°"
        
        summary = [mag_summary, phase_summary]
        
        # No symmetrical components section
        
        summary.append(f"Verdict: <b><span style='color:{color}'>{verdict_text}</span></b>")
        self.summary_label.setText("\n".join(summary))

        # Plot phasors (normalized to mean magnitude for readability)
        scale = mean_mag if mean_mag > 0 else 1.0
        normalized_phasors = [p/scale for p in phasors]
        self._plot_phasors_multi(normalized_phasors, phase_names)

        # Details text
        details = []
        details.append(f"{phases}‑Phase EMF from Winding")
        details.append("--------------------------------")
        details.append(f"m (phases) = {phases}")
        details.append(f"Q (slots) = {Q}")
        details.append(f"p (pair of poles) = {p_pairs}")
        
        # Winding factor calculations (fundamental)
        try:
            slots = int(getattr(self.parent, 'slots_spin').value())
            p_pairs_ui = int(getattr(self.parent, 'poles_spin').value())
            m_phases = phases
            actual_poles = 2 * p_pairs_ui
            spp = slots / actual_poles  # slots per pole
            q_val = spp / m_phases      # slots per pole per phase
            alpha_deg = 180.0 / spp     # electrical angle between adjacent slots
            # Coil span in slots
            if getattr(self.parent, 'single_layer').isChecked():
                coil_span_slots = int(round(slots / actual_poles))
            else:
                coil_span_slots = int(getattr(self.parent, 'span_spin').value())
            gamma_deg = coil_span_slots * alpha_deg  # coil pitch (electrical)
            # Pitch factor (fundamental): kp = sin(gamma/2)
            kp = np.sin(np.deg2rad(gamma_deg/2.0))
            # Distribution factor formula (integer q): kd = sin(q*alpha/2)/(q*sin(alpha/2))
            kd_formula = None
            if q_val > 1e-9:
                kd_formula = np.sin(np.deg2rad(q_val*alpha_deg/2.0)) / (q_val * np.sin(np.deg2rad(alpha_deg/2.0)))
            # Empirical winding factor from phasor sum per phase
            A_coll, B_coll, C_coll = (matrix[0] + matrix[3], matrix[1] + matrix[4], matrix[2] + matrix[5]) if matrix.shape[0] == 6 else (matrix[0], matrix[1], matrix[2])
            NA = np.sum(np.abs(A_coll))
            NB = np.sum(np.abs(B_coll))
            NC = np.sum(np.abs(C_coll))
            kwA = (np.abs(Ea) / NA) if NA > 0 else 0.0
            kwB = (np.abs(Eb) / NB) if NB > 0 else 0.0
            kwC = (np.abs(Ec) / NC) if NC > 0 else 0.0
            kw_emp = float(np.mean([kwA, kwB, kwC]))
            # Derive kd_emp = kw_emp / kp (if kp>0)
            kd_emp = (kw_emp / kp) if kp > 1e-9 else 0.0
        except Exception as e:
            kp = kd_emp = kw_emp = None
            alpha_deg = q_val = gamma_deg = None
            kd_formula = None
        
        details.append("")
        details.append("Winding factor (fundamental)")
        details.append("  α = electrical slot angle = 180° / (Q / (2p)) = 360°·p / Q")
        if alpha_deg is not None:
            details.append(f"  α = {alpha_deg:.6f}°")
        if gamma_deg is not None:
            details.append(f"  Coil span = {coil_span_slots} slots → γ = {gamma_deg:.6f}°")
        if q_val is not None:
            details.append(f"  q = slots per pole per phase = {q_val:.6f}")
        if kp is not None:
            details.append(f"  Pitch factor kp = sin(γ/2) = {kp:.6f}")
        if kd_formula is not None:
            details.append(f"  Distribution factor kd(formula) = sin(q·α/2) / [q·sin(α/2)] = {kd_formula:.6f}")
        if kw_emp is not None:
            details.append(f"  Empirical kw (from phasor sum) = mean(|E|)/N_series_phase ≈ {kw_emp:.6f}")
        if kp is not None and kd_emp is not None:
            details.append(f"  Derived kd(emp) = kw_emp / kp ≈ {kd_emp:.6f}")
        if kd_formula is not None and kd_emp is not None:
            details.append(f"  Check: kd(emp) vs kd(formula) → Δ = {abs(kd_emp - kd_formula):.6e}")
        details.append("")
        details.append("Formulae:")
        details.append("  θ_e(n) = 360° · p · n / Q")
        details.append("  E_phase ∝ Σ s_n · e^{j θ_e(n)}  (n = 0..Q-1)")
        if phases == 3:
            details.append("  a = e^{j 120°}")
            details.append("  V0 = (Ea + Eb + Ec) / 3")
            details.append("  V1 = (Ea + a·Eb + a²·Ec) / 3  (positive sequence)")
            details.append("  V2 = (Ea + a²·Eb + a·Ec) / 3  (negative sequence)")
        details.append("")

        def cfmt(z):
            return f"{z.real:.6f} + j{z.imag:.6f}"
        def polfmt(z):
            return f"|{np.abs(z):.6f}| ∠ {np.rad2deg(np.angle(z)):.3f}°"

        details.append("Computed phasors (relative units):")
        for i, phase_name in enumerate(phase_names):
            details.append(f"  E{phase_name} = {cfmt(phasors[i])}  (polar: {polfmt(phasors[i])})")
        
        # Sum of EMFs closure
        Esum = sum(phasors)
        details.append(f"  EMF sum: {'+'.join(['E'+p for p in phase_names])} = {cfmt(Esum)}  |sum|={np.abs(Esum):.6e}")
        details.append("")
        details.append("Phase differences (deg):")
        for i in range(phases):
            next_i = (i + 1) % phases
            details.append(f"  {phase_names[i]}{phase_names[next_i]} = {phase_diffs[i]:.6f}; error to {expected_spacing:.1f}° = {phase_errs[i]:.6f}")
        
        # No symmetrical components details (removed)

        # Explicit slot-sum used to compute E for each phase
        details.append("")
        details.append("Slot contributions (only non-zero slots):")
        # Build slot sign arrays (collapse double layer if needed) from analysis matrix
        rows = matrix_for_analysis.shape[0]
        m = rows // 2 if rows % 2 == 0 else rows
        
        phase_arrays = []
        if rows == 2 * m:  # Double layer
            for i in range(m):
                phase_arrays.append(matrix_for_analysis[i] + matrix_for_analysis[m + i])
        else:  # Single layer
            for i in range(m):
                phase_arrays.append(matrix_for_analysis[i])
        
        # Electrical angles per slot
        theta_deg = (360.0 * p_pairs * np.arange(Q)) / Q
        theta = np.deg2rad(theta_deg)
        ejth = np.exp(1j * theta)

        def contrib_lines(name, signs, E_sum):
            lines = [f"  Phase {name}:"]
            for n in range(Q):
                s = int(signs[n])
                if s == 0:
                    continue
                term = s * ejth[n]
                lines.append(f"    slot {n+1:>2}: s={s:+d} · e^(j{theta_deg[n]:.3f}°) = {cfmt(term)}")
            lines.append(f"    Σ = {cfmt(E_sum)}  (polar: {polfmt(E_sum)})")
            return lines

        for i, phase_name in enumerate(phase_names):
            details.extend(contrib_lines(phase_name, phase_arrays[i], phasors[i]))

        self.details_text.setPlainText("\n".join(details))

    def _plot_phasors_multi(self, phasors, phase_names):
        """Plot phasors for any number of phases"""
        self.ax_phasor.clear()
        max_r = max([np.abs(p) for p in phasors]) if phasors else 1.0
        lim = 1.2 * (max_r if max_r > 0 else 1.0)
        self.ax_phasor.set_xlim(-lim, lim)
        self.ax_phasor.set_ylim(-lim, lim)
        self.ax_phasor.axhline(0, color='#888888', linewidth=1)
        self.ax_phasor.axvline(0, color='#888888', linewidth=1)
        self.ax_phasor.set_aspect('equal', adjustable='box')
        self.ax_phasor.set_title(f'{len(phasors)}-Phase Winding EMF Phasors (normalized)')

        # Color palette for phases
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'cyan', 
                 'magenta', 'brown', 'pink', 'olive', 'navy', 'teal']

        def draw_vec(z, color, label):
            if np.abs(z) < 1e-9:
                return
            self.ax_phasor.annotate('', xy=(z.real, z.imag), xytext=(0, 0),
                                   arrowprops=dict(arrowstyle='->', color=color, lw=2))
            ang = np.angle(z)
            r = np.abs(z)
            offset_r = r * 1.15
            x_txt = offset_r * np.cos(ang)
            y_txt = offset_r * np.sin(ang)
            self.ax_phasor.text(x_txt, y_txt, label, color=color, fontsize=12, weight='bold',
                               ha='center', va='center')

        for i, (phasor, phase_name) in enumerate(zip(phasors, phase_names)):
            color = colors[i % len(colors)]
            draw_vec(phasor, color, f'E{phase_name}')

        self.ax_phasor.grid(True, alpha=0.3)
        self.canvas_phasor.draw()

    def _plot_phasors(self, Va_c, Vb_c, Vc_c):
        """Legacy 3-phase plotting function"""
        self._plot_phasors_multi([Va_c, Vb_c, Vc_c], ['A', 'B', 'C'])
