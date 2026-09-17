"""Intelligent color contrast remediation engine.

Automatically calculates the minimal perceptual shift (minimizing CIEDE2000 ΔE)
required to achieve target WCAG contrast ratios (e.g., 4.5:1 for AA or 7.0:1 for AAA).
Supports adjusting foreground, background, or both colors simultaneously.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple, Union

from wcag_contrast_guard.color_math import (
    color_distance,
    delta_e_ciede2000,
    lab_to_rgb,
    parse_color,
    rgb_to_lab,
)
from wcag_contrast_guard.models import Color, RemediationSuggestion
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio


def _find_adjusted_color_1d(
    col_to_adjust: Color,
    fixed_col: Color,
    target_ratio: float,
    direction: str,  # 'lighten' or 'darken'
) -> Optional[Tuple[Color, float, float]]:
    """Binary search along L* axis in CIE L*a*b* space in a specific direction.

    Returns:
        Optional[Tuple[Color, float, float]]: (suggested_color, new_ratio, delta_e) if reachable.
    """
    orig_lab = rgb_to_lab(col_to_adjust.r, col_to_adjust.g, col_to_adjust.b)
    l_orig, a_orig, b_orig = orig_lab

    if direction == "lighten":
        low_l = l_orig
        high_l = 100.0
    else:
        low_l = 0.0
        high_l = l_orig

    # Check boundary at extreme end first
    extreme_l = 100.0 if direction == "lighten" else 0.0
    r_ext, g_ext, b_ext = lab_to_rgb(extreme_l, a_orig, b_orig)
    extreme_col = Color(r=r_ext, g=g_ext, b=b_ext, a=col_to_adjust.a)
    extreme_ratio = calculate_contrast_ratio(extreme_col, fixed_col)

    if extreme_ratio < target_ratio:
        # Cannot reach target ratio even at boundary in this direction
        return None

    # Binary search for the closest L* to original that satisfies target_ratio
    best_col = extreme_col
    best_ratio = extreme_ratio
    best_de = color_distance(col_to_adjust, extreme_col, formula="ciede2000")

    iterations = 24  # High precision
    for _ in range(iterations):
        mid_l = (low_l + high_l) / 2.0
        r_cand, g_cand, b_cand = lab_to_rgb(mid_l, a_orig, b_orig)
        cand_col = Color(r=r_cand, g=g_cand, b=b_cand, a=col_to_adjust.a)
        ratio = calculate_contrast_ratio(cand_col, fixed_col)

        if ratio >= target_ratio:
            best_col = cand_col
            best_ratio = ratio
            best_de = color_distance(col_to_adjust, cand_col, formula="ciede2000")
            if direction == "lighten":
                high_l = mid_l  # Try to find a lower L* closer to original
            else:
                low_l = mid_l   # Try to find a higher L* closer to original
        else:
            if direction == "lighten":
                low_l = mid_l   # Need more lightness
            else:
                high_l = mid_l  # Need more darkness

    return (best_col, best_ratio, best_de)


def remediate_contrast(
    fg: Union[str, Color],
    bg: Union[str, Color],
    target_ratio: float = 4.5,
    adjust: str = "foreground",
    max_delta_e: Optional[float] = None,
) -> RemediationSuggestion:
    """Remediate a color pair to satisfy a target WCAG contrast ratio with minimal ΔE00 shift.

    Args:
        fg: Foreground color.
        bg: Background color.
        target_ratio: Required WCAG contrast ratio (default 4.5 for AA normal).
        adjust: Which color to adjust: 'foreground' (or 'fg'), 'background' (or 'bg'), or 'both'.
        max_delta_e: Optional ceiling for allowed CIEDE2000 shift.

    Returns:
        RemediationSuggestion: Optimal suggested color with ratio, ΔE, and direction.
    """
    fg_col = parse_color(fg) if not isinstance(fg, Color) else fg
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg

    current_ratio = calculate_contrast_ratio(fg_col, bg_col)
    if current_ratio >= target_ratio:
        color_target = fg_col if adjust.lower() in ("foreground", "fg") else bg_col
        return RemediationSuggestion(
            original_color=color_target,
            suggested_color=color_target,
            target_ratio=target_ratio,
            new_ratio=current_ratio,
            delta_e=0.0,
            direction="none",
        )

    adjust_mode = adjust.strip().lower()

    if adjust_mode in ("foreground", "fg"):
        # Test both lighten and darken
        res_light = _find_adjusted_color_1d(fg_col, bg_col, target_ratio, "lighten")
        res_dark = _find_adjusted_color_1d(fg_col, bg_col, target_ratio, "darken")

        candidates = []
        if res_light is not None:
            candidates.append((res_light[0], res_light[1], res_light[2], "lighten"))
        if res_dark is not None:
            candidates.append((res_dark[0], res_dark[1], res_dark[2], "darken"))

        if not candidates:
            # Fallback to white or black (whichever gives higher contrast)
            white = Color(r=255, g=255, b=255)
            black = Color(r=0, g=0, b=0)
            r_white = calculate_contrast_ratio(white, bg_col)
            r_black = calculate_contrast_ratio(black, bg_col)
            if r_white >= r_black:
                chosen, direction, r_val = white, "lighten", r_white
            else:
                chosen, direction, r_val = black, "darken", r_black
            de = color_distance(fg_col, chosen, formula="ciede2000")
            return RemediationSuggestion(
                original_color=fg_col,
                suggested_color=chosen,
                target_ratio=target_ratio,
                new_ratio=r_val,
                delta_e=de,
                direction=direction,
            )

        # Pick candidate with minimum perceptual shift (ΔE00)
        candidates.sort(key=lambda x: x[2])
        best_col, best_ratio, best_de, best_dir = candidates[0]

        return RemediationSuggestion(
            original_color=fg_col,
            suggested_color=best_col,
            target_ratio=target_ratio,
            new_ratio=best_ratio,
            delta_e=best_de,
            direction=best_dir,
        )

    elif adjust_mode in ("background", "bg"):
        # Test both lighten and darken on background against fixed foreground
        res_light = _find_adjusted_color_1d(bg_col, fg_col, target_ratio, "lighten")
        res_dark = _find_adjusted_color_1d(bg_col, fg_col, target_ratio, "darken")

        candidates = []
        if res_light is not None:
            candidates.append((res_light[0], res_light[1], res_light[2], "lighten"))
        if res_dark is not None:
            candidates.append((res_dark[0], res_dark[1], res_dark[2], "darken"))

        if not candidates:
            white = Color(r=255, g=255, b=255)
            black = Color(r=0, g=0, b=0)
            r_white = calculate_contrast_ratio(fg_col, white)
            r_black = calculate_contrast_ratio(fg_col, black)
            if r_white >= r_black:
                chosen, direction, r_val = white, "lighten", r_white
            else:
                chosen, direction, r_val = black, "darken", r_black
            de = color_distance(bg_col, chosen, formula="ciede2000")
            return RemediationSuggestion(
                original_color=bg_col,
                suggested_color=chosen,
                target_ratio=target_ratio,
                new_ratio=r_val,
                delta_e=de,
                direction=direction,
            )

        candidates.sort(key=lambda x: x[2])
        best_col, best_ratio, best_de, best_dir = candidates[0]

        return RemediationSuggestion(
            original_color=bg_col,
            suggested_color=best_col,
            target_ratio=target_ratio,
            new_ratio=best_ratio,
            delta_e=best_de,
            direction=best_dir,
        )

    elif adjust_mode == "both":
        # Adjust foreground while letting background move symmetrically
        # First try foreground-only
        fg_sugg = remediate_contrast(fg_col, bg_col, target_ratio=target_ratio, adjust="foreground")
        bg_sugg = remediate_contrast(fg_col, bg_col, target_ratio=target_ratio, adjust="background")

        if fg_sugg.delta_e <= bg_sugg.delta_e:
            return fg_sugg
        return bg_sugg

    raise ValueError(f"Unknown adjust option '{adjust}'. Expected 'foreground', 'background', or 'both'.")


def suggest_accessible_palette(
    colors: Sequence[Union[str, Color]],
    target_ratio: float = 4.5,
    bg: Union[str, Color] = "#ffffff",
) -> List[RemediationSuggestion]:
    """Audit and remediate a sequence of colors against a shared background.

    Args:
        colors: Sequence of color representations.
        target_ratio: Target contrast ratio.
        bg: Common background color.

    Returns:
        List[RemediationSuggestion]: List of suggestions for each input color.
    """
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg
    suggestions: List[RemediationSuggestion] = []
    for c in colors:
        c_col = parse_color(c) if not isinstance(c, Color) else c
        sugg = remediate_contrast(c_col, bg_col, target_ratio=target_ratio, adjust="foreground")
        suggestions.append(sugg)
    return suggestions


def find_best_contrast_match(
    color: Union[str, Color],
    candidates: Sequence[Union[str, Color]],
    target_ratio: float = 4.5,
) -> Optional[Color]:
    """Find the candidate color that satisfies target_ratio with minimum ΔE to target.

    Args:
        color: Base color.
        candidates: Candidate colors to test against base color.
        target_ratio: Target contrast ratio.

    Returns:
        Optional[Color]: Best compliant candidate or None if none pass.
    """
    base = parse_color(color) if not isinstance(color, Color) else color
    passing: List[Tuple[Color, float]] = []

    for cand in candidates:
        cand_col = parse_color(cand) if not isinstance(cand, Color) else cand
        ratio = calculate_contrast_ratio(base, cand_col)
        if ratio >= target_ratio:
            de = color_distance(base, cand_col, formula="ciede2000")
            passing.append((cand_col, de))

    if not passing:
        return None

    passing.sort(key=lambda x: x[1])
    return passing[0][0]
