"""Color vision deficiency (CVD) simulation engine.

Simulates 8 deficiency types (Protanopia, Protanomaly, Deuteranopia, Deuteranomaly,
Tritanopia, Tritanomaly, Achromatopsia, Achromatomaly) using physiologically accurate
transformation matrices in linear RGB space.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Union

from wcag_contrast_guard.color_math import (
    blend_alpha,
    get_relative_luminance,
    linear_to_srgb,
    parse_color,
    srgb_to_linear,
)
from wcag_contrast_guard.models import (
    Color,
    ColorblindSimulationResult,
    ColorblindType,
    WCAGResult,
)
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio

# -------------------------------------------------------------------------
# Transformation Matrices in Linear RGB Space (Full 1.0 Severity)
# -------------------------------------------------------------------------
SIMULATION_MATRICES: Dict[ColorblindType, Tuple[Tuple[float, float, float], ...]] = {
    ColorblindType.PROTANOPIA: (
        (0.56667, 0.43333, 0.00000),
        (0.55833, 0.44167, 0.00000),
        (0.00000, 0.24167, 0.75833),
    ),
    ColorblindType.PROTANOMALY: (
        (0.81667, 0.18333, 0.00000),
        (0.33333, 0.66667, 0.00000),
        (0.00000, 0.12500, 0.87500),
    ),
    ColorblindType.DEUTERANOPIA: (
        (0.62500, 0.37500, 0.00000),
        (0.70000, 0.30000, 0.00000),
        (0.00000, 0.30000, 0.70000),
    ),
    ColorblindType.DEUTERANOMALY: (
        (0.80000, 0.20000, 0.00000),
        (0.25833, 0.74167, 0.00000),
        (0.00000, 0.14167, 0.85833),
    ),
    ColorblindType.TRITANOPIA: (
        (0.95000, 0.05000, 0.00000),
        (0.00000, 0.43333, 0.56667),
        (0.00000, 0.47500, 0.52500),
    ),
    ColorblindType.TRITANOMALY: (
        (0.96667, 0.03333, 0.00000),
        (0.00000, 0.73333, 0.26667),
        (0.00000, 0.18333, 0.81667),
    ),
    ColorblindType.ACHROMATOPSIA: (
        (0.212656, 0.715158, 0.072186),
        (0.212656, 0.715158, 0.072186),
        (0.212656, 0.715158, 0.072186),
    ),
    ColorblindType.ACHROMATOMALY: (
        (0.618000, 0.320000, 0.062000),
        (0.163000, 0.775000, 0.062000),
        (0.163000, 0.320000, 0.516000),
    ),
}

IDENTITY_MATRIX: Tuple[Tuple[float, float, float], ...] = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


def _interpolate_matrix(
    base_mat: Tuple[Tuple[float, float, float], ...],
    severity: float,
) -> Tuple[Tuple[float, float, float], ...]:
    """Interpolate between Identity matrix and deficiency matrix based on severity [0.0, 1.0]."""
    s = max(0.0, min(1.0, severity))
    res: List[Tuple[float, float, float]] = []
    for row_idx in range(3):
        row = (
            (1.0 - s) * IDENTITY_MATRIX[row_idx][0] + s * base_mat[row_idx][0],
            (1.0 - s) * IDENTITY_MATRIX[row_idx][1] + s * base_mat[row_idx][1],
            (1.0 - s) * IDENTITY_MATRIX[row_idx][2] + s * base_mat[row_idx][2],
        )
        res.append(row)
    return (res[0], res[1], res[2])


def simulate_colorblind(
    color: Union[str, Color],
    deficiency: Union[str, ColorblindType],
    severity: float = 1.0,
) -> Color:
    """Simulate how a color is perceived under a color vision deficiency.

    Args:
        color: Input color representation.
        deficiency: ColorblindType enum or string (e.g. 'protanopia', 'deuteranopia').
        severity: Severity factor from 0.0 (normal vision) to 1.0 (full deficiency).

    Returns:
        Color: Simulated color as perceived.
    """
    col = parse_color(color) if not isinstance(color, Color) else color
    def_type = ColorblindType(deficiency) if isinstance(deficiency, str) else deficiency

    target_mat = SIMULATION_MATRICES.get(def_type, IDENTITY_MATRIX)
    if severity < 0.999:
        mat = _interpolate_matrix(target_mat, severity)
    else:
        mat = target_mat

    # Convert to Linear RGB
    r_lin = srgb_to_linear(col.r / 255.0)
    g_lin = srgb_to_linear(col.g / 255.0)
    b_lin = srgb_to_linear(col.b / 255.0)

    # Matrix multiplication
    r_sim_lin = mat[0][0] * r_lin + mat[0][1] * g_lin + mat[0][2] * b_lin
    g_sim_lin = mat[1][0] * r_lin + mat[1][1] * g_lin + mat[1][2] * b_lin
    b_sim_lin = mat[2][0] * r_lin + mat[2][1] * g_lin + mat[2][2] * b_lin

    # Gamma compression back to sRGB [0, 255]
    r_sim = int(round(linear_to_srgb(r_sim_lin) * 255.0))
    g_sim = int(round(linear_to_srgb(g_sim_lin) * 255.0))
    b_sim = int(round(linear_to_srgb(b_sim_lin) * 255.0))

    return Color(
        r=max(0, min(255, r_sim)),
        g=max(0, min(255, g_sim)),
        b=max(0, min(255, b_sim)),
        a=col.a,
    )


def simulate_pair(
    fg: Union[str, Color],
    bg: Union[str, Color],
    deficiency: Union[str, ColorblindType],
    severity: float = 1.0,
) -> ColorblindSimulationResult:
    """Simulate a foreground/background pair and determine post-simulation accessibility.

    Args:
        fg: Foreground color.
        bg: Background color.
        deficiency: Color vision deficiency type.
        severity: Severity factor in [0.0, 1.0].

    Returns:
        ColorblindSimulationResult: Simulated pair and post-simulation ratio & pass status.
    """
    fg_col = parse_color(fg) if not isinstance(fg, Color) else fg
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg
    def_type = ColorblindType(deficiency) if isinstance(deficiency, str) else deficiency

    sim_fg = simulate_colorblind(fg_col, def_type, severity=severity)
    sim_bg = simulate_colorblind(bg_col, def_type, severity=severity)

    ratio = calculate_contrast_ratio(sim_fg, sim_bg)
    is_accessible = ratio >= 4.5

    return ColorblindSimulationResult(
        deficiency=def_type,
        simulated_fg=sim_fg,
        simulated_bg=sim_bg,
        simulated_ratio=round(ratio, 2),
        is_accessible=is_accessible,
    )


def simulate_all_deficiencies(
    fg: Union[str, Color],
    bg: Union[str, Color],
    severity: float = 1.0,
) -> Dict[ColorblindType, ColorblindSimulationResult]:
    """Run simulations across all 8 deficiency types for a color pair.

    Args:
        fg: Foreground color.
        bg: Background color.
        severity: Deficiency severity.

    Returns:
        Dict[ColorblindType, ColorblindSimulationResult]: Results for all deficiencies.
    """
    results: Dict[ColorblindType, ColorblindSimulationResult] = {}
    for def_type in ColorblindType:
        results[def_type] = simulate_pair(fg, bg, def_type, severity=severity)
    return results


# Alias for backward compatibility
simulate_colorblindness = simulate_pair
