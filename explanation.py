from fractions import Fraction
import math

def gcd(a, b):
    """Calculate greatest common divisor"""
    if b == 0:
        return a
    return gcd(b, a % b)

def check_winding_feasibility(slots, poles, phases=3):
    """Check winding feasibility using koil's logic"""
    q = Fraction(slots, (phases * poles))
    messages = []
    feasible = True
    single_layer_feasible = False
    
    m = phases  # number of phases
    p = poles // 2  # pole pairs
    Q = slots
    
    # Compute machine periodicity
    t = gcd(Q, p)
    
    # Main feasibility check (from koil)
    if int(Q / (m * t)) != float(Q / (m * t)):
        messages.append(f"- Q/(m*t) = {Q}/{m}*{t} = {Q/(m*t):.3f} must be an integer for balanced winding")
        feasible = False
    elif (gcd(m, 2) == 2) and (gcd(int(Q / (m * t)), 2) != 2):
        messages.append(f"- Configuration doesn't allow balanced {m}-phase winding with even phase count")
        feasible = False
    else:
        # Winding is feasible, now check single layer feasibility
        if gcd(Q, 2) != 2:  # Q is odd
            single_layer_feasible = False
        else:  # Q is even
            if gcd(int(Q / t), 2) != 2:  # Q/t is odd
                if (t % 2) != 0:  # t is odd
                    single_layer_feasible = False
                else:  # t is even
                    single_layer_feasible = True
            else:  # Q/t is even
                if gcd(int(Q / (2 * t)), 2) == 2:  # Q/(2t) is even
                    single_layer_feasible = True
                else:  # Q/(2t) is odd
                    single_layer_feasible = True
    
    # Additional checks
    if float(q) < 0.25:
        messages.append("- Slots per pole per phase too low (q < 0.25)")
        feasible = False
    
    if not feasible:
        single_layer_feasible = False
    
    return feasible, messages, q, single_layer_feasible

def calculate_winding_factors(slots, poles, coil_span, phases=3):
    # q = slots per pole per phase, poles = total poles
    q = Fraction(slots, (phases * poles))
    q_val = float(q)
    # Electrical slot angle (fundamental) in radians: α = π·P/Q
    alpha = math.pi * poles / slots
    # Distribution factor (fundamental): kd = sin(q·α/2) / [q·sin(α/2)]
    kd = (math.sin(q_val * alpha / 2) / (q_val * math.sin(alpha / 2))) if q_val > 0 else 0.0
    # Coil pitch (electrical) γ = coil_span (in slots) · α
    coil_angle = coil_span * alpha
    # Pitch factor: kp = sin(γ/2)
    kp = math.sin(coil_angle / 2)
    # Skew factor: ks = sin(σ/2)/(σ/2); without skew, σ=0 → ks=1
    ks = 1.0
    kw = kd * kp * ks

    return {
        'distribution': kd,
        'pitch': kp,
        'skew': ks,
        'total': kw
    }

def predict_performance(slots, poles, kw):
    frequency = 50
    speed = (frequency * 60 * 2) / poles
    cogging_assessment = "Low" if Fraction(slots, poles).denominator > 1 else "Moderate"
    torque_ripple = "Low" if slots > (poles * 6) else "Moderate"

    return {
        'sync_speed': speed,
        'cogging': cogging_assessment,
        'torque_ripple': torque_ripple
    }

def generate_winding_explanation(slots, poles, coil_span, is_double_layer, q, single_layer_feasible=True, phases=3):
    winding_factors = calculate_winding_factors(slots, poles, coil_span, phases)
    performance = predict_performance(slots, poles, winding_factors['total'])
    explanation = []
    
    # Add single layer feasibility info
    if not is_double_layer and not single_layer_feasible:
        explanation.append("⚠ WARNING: Single layer winding not feasible for this configuration!\n")

    explanation.append("1. BASIC CONFIGURATION")
    explanation.append(f"• Number of slots (Q): {slots}")
    explanation.append(f"• Number of poles (P): {poles}")
    explanation.append(f"• Number of phases (m): {phases}")
    explanation.append(f"• Number of pole pairs (p): {poles // 2}")
    
    # Calculate and display machine periodicity
    pole_pairs = poles // 2
    t = gcd(slots, pole_pairs)
    slots_per_phase_period = slots / (phases * t)
    explanation.append(f"• Machine periodicity (t): {t}")
    explanation.append(f"  → t = gcd(Q, p) = gcd({slots}, {pole_pairs}) = {t}")
    explanation.append(f"  → Pattern repeats {t} time(s) around stator")
    explanation.append(f"• Slots per phase per period: Q/(m·t) = {slots}/({phases}·{t}) = {slots_per_phase_period:.3f}")
    if slots_per_phase_period != int(slots_per_phase_period):
        explanation.append(f"  ⚠ NOT an integer → Winding not feasible!")
    
    # Calculate theoretical pole pitch and determine pitch type
    theoretical_pole_pitch = slots / (2 * pole_pairs)
    explanation.append(f"• Theoretical pole pitch: Q/(2p) = {slots}/(2·{pole_pairs}) = {theoretical_pole_pitch:.2f} slots")
    explanation.append(f"• Actual coil span: {coil_span} slots")
    
    # Determine pitch type
    if coil_span == int(theoretical_pole_pitch):
        pitch_type = "Full pitch"
        pitch_description = "coil span = pole pitch → Maximum fundamental winding factor"
    elif coil_span < theoretical_pole_pitch:
        pitch_type = "Short pitch (chorded)"
        pitch_description = f"coil span < pole pitch → Better harmonic reduction"
    else:
        pitch_type = "Long pitch"
        pitch_description = f"coil span > pole pitch → Not recommended"
    
    explanation.append(f"• Pitch type: {pitch_type}")
    explanation.append(f"  → {pitch_description}")
    explanation.append(f"• Winding type: {'Double layer' if is_double_layer else 'Single layer'}")
    
    # Single layer feasibility explanation
    explanation.append(f"\n• Single Layer Feasibility Check:")
    if slots % 2 != 0:
        explanation.append(f"  → Q is odd ({slots}) → Single layer NOT feasible")
        explanation.append(f"  → Reason: Single layer requires even number of slots")
    else:
        explanation.append(f"  → Q is even ({slots}) ✓")
        qt = slots / t
        if qt % 2 != 0:  # Q/t is odd
            explanation.append(f"  → Q/t = {slots}/{t} = {qt:.1f} (odd)")
            if t % 2 != 0:  # t is odd
                explanation.append(f"  → t is odd ({t}) → Single layer NOT feasible")
                explanation.append(f"  → Reason: Q/t odd AND t odd makes balancing impossible")
            else:  # t is even
                explanation.append(f"  → t is even ({t}) → Single layer FEASIBLE ✓")
        else:  # Q/t is even
            explanation.append(f"  → Q/t = {slots}/{t} = {int(qt)} (even) → Single layer FEASIBLE ✓")
    
    if single_layer_feasible:
        explanation.append(f"  → Result: Single layer winding IS feasible for this configuration")
    else:
        explanation.append(f"  → Result: Single layer winding NOT feasible - use double layer")
    explanation.append("")

    explanation.append("2. TECHNICAL PARAMETERS")
    explanation.append(f"• Slots per pole (S/P): {slots / poles:.2f}")
    explanation.append(f"• Slots per pole per phase (q): {q}")
    # Electrical slot angle α (fundamental) = 180° · P / Q = 360° · (P/2) / Q
    explanation.append(f"• Electrical angle between slots: {180 * poles / slots:.1f}°")
    if is_double_layer:
        explanation.append(f"• Coil pitch: {(coil_span / slots) * 100:.1f}% of pole pitch\n")

    explanation.append("3. WINDING FACTORS")
    explanation.append(f"• Distribution factor (kd): {winding_factors['distribution']:.3f}")
    explanation.append(f"• Pitch factor (kp): {winding_factors['pitch']:.3f}")
    explanation.append(f"• Skew factor (ks): {winding_factors['skew']:.3f}")
    explanation.append(f"• Total winding factor (kw): {winding_factors['total']:.3f}\n")

    explanation.append("4. ELECTROMAGNETIC PERFORMANCE")
    explanation.append(f"• Synchronous speed: {performance['sync_speed']} RPM")
    explanation.append(f"• Expected cogging torque: {performance['cogging']}")
    explanation.append(f"• Expected torque ripple: {performance['torque_ripple']}")
    if q.denominator > 1:
        explanation.append("• Fractional slot benefits:")
        explanation.append("  - Reduced cogging torque")
        explanation.append("  - Better fault tolerance")
        explanation.append("  - Shorter end windings\n")

    explanation.append("5. HARMONIC CHARACTERISTICS")
    if is_double_layer:
        explanation.append("• Double layer advantages:")
        explanation.append("  - Better harmonic reduction")
        explanation.append("  - Lower MMF harmonics")
    else:
        explanation.append("• Single layer characteristics:")
        explanation.append("  - Stronger fundamental")
        explanation.append("  - Higher harmonic content")
    if q.denominator > 1:
        explanation.append("• Sub-harmonics present due to fractional slots")
        explanation.append(f"• Working harmonics: 1, {poles - 2}, {poles + 2}\n")

    explanation.append("6. PRACTICAL CONSTRUCTION CONSIDERATIONS")
    explanation.append("Advantages:")
    if is_double_layer:
        explanation.append("• Better slot filling possibility")
        explanation.append("• Shorter end windings")
        explanation.append("• Better cooling potential")
    else:
        explanation.append("• Simpler to manufacture")
        explanation.append("• Better insulation between phases")
        explanation.append("• Higher reliability")

    explanation.append("\nChallenges:")
    if slots > 48:
        explanation.append("• High slot count may be difficult to manufacture")
    if q.denominator > 1:
        explanation.append("• More complex winding pattern")
    if is_double_layer and coil_span > slots / poles:
        explanation.append("• Long end windings may increase copper loss")

    explanation.append("\nRecommendations:")
    if is_double_layer:
        explanation.append(f"• Optimal coil span: {int(slots / poles)} slots")
    explanation.append(f"• Slot fill factor target: {0.4 if is_double_layer else 0.45}")
    explanation.append(f"• Recommended slot opening: {0.25 if slots > 36 else 0.3} × tooth pitch")

    return "\n".join(explanation)
