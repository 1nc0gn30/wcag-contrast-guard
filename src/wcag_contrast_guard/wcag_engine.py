"""WCAG 2.1 and WCAG 2.2 contrast ratio evaluation engine.

Implements official W3C formulas for relative luminance, contrast ratio,
and conformance grading for AA and AAA levels (normal text, large text,
and UI components/graphical objects).
"""

from __future__ import annotations

from typing import List, Optional, Union

from wcag_contrast_guard.color_math import blend_alpha, get_relative_luminance, parse_color
from wcag_contrast_guard.models import Color, WCAGLevel, WCAGResult


def calculate_contrast_ratio(
    fg: Union[str, Color],
    bg: Union[str, Color],
) -> float:
    """Calculate the WCAG 2.1 / 2.2 contrast ratio between two colors.

    If the foreground color has transparency (alpha < 1.0), it is automatically
    composited over the background color before computing relative luminance.

    Formula:
        Ratio = (L1 + 0.05) / (L2 + 0.05)
        where L1 is the lighter relative luminance and L2 is the darker.

    Args:
        fg: Foreground color representation (Hex, RGB, HSL, name, or Color).
        bg: Background color representation (Hex, RGB, HSL, name, or Color).

    Returns:
        float: Calculated contrast ratio in the range [1.0, 21.0].
    """
    fg_col = parse_color(fg) if not isinstance(fg, Color) else fg
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg

    # Blend foreground over background if foreground has alpha
    if not fg_col.is_opaque:
        fg_effective = blend_alpha(fg_col, bg_col)
    else:
        fg_effective = fg_col

    lum_fg = get_relative_luminance(fg_effective)
    lum_bg = get_relative_luminance(bg_col)

    l1 = max(lum_fg, lum_bg)
    l2 = min(lum_fg, lum_bg)

    ratio = (l1 + 0.05) / (l2 + 0.05)
    return round(ratio, 4)


def evaluate_wcag(
    fg: Union[str, Color],
    bg: Union[str, Color],
    target_level: Optional[Union[str, WCAGLevel]] = None,
) -> WCAGResult:
    """Perform a full WCAG 2.1/2.2 accessibility conformance audit on a color pair.

    Args:
        fg: Foreground color.
        bg: Background color.
        target_level: Optional target level for documentation/evaluation.

    Returns:
        WCAGResult: Complete evaluation with pass/fail breakdown across all tiers.
    """
    fg_col = parse_color(fg) if not isinstance(fg, Color) else fg
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg

    ratio = calculate_contrast_ratio(fg_col, bg_col)

    # Threshold checks
    aa_normal = ratio >= 4.5
    aa_large = ratio >= 3.0
    aaa_normal = ratio >= 7.0
    aaa_large = ratio >= 4.5
    ui_component = ratio >= 3.0

    ratio_str = f"{ratio:.2f}:1"

    return WCAGResult(
        ratio=round(ratio, 2),
        ratio_str=ratio_str,
        aa_normal_pass=aa_normal,
        aa_large_pass=aa_large,
        aaa_normal_pass=aaa_normal,
        aaa_large_pass=aaa_large,
        ui_component_pass=ui_component,
        foreground=fg_col,
        background=bg_col,
    )


def is_aa_compliant(
    fg: Union[str, Color],
    bg: Union[str, Color],
    is_large_text: bool = False,
) -> bool:
    """Check if color pair satisfies WCAG Level AA requirements.

    Args:
        fg: Foreground color.
        bg: Background color.
        is_large_text: If True, uses 3.0:1 threshold (>=18pt or >=14pt bold), else 4.5:1.

    Returns:
        bool: True if compliant.
    """
    ratio = calculate_contrast_ratio(fg, bg)
    return ratio >= (3.0 if is_large_text else 4.5)


def is_aaa_compliant(
    fg: Union[str, Color],
    bg: Union[str, Color],
    is_large_text: bool = False,
) -> bool:
    """Check if color pair satisfies WCAG Level AAA requirements.

    Args:
        fg: Foreground color.
        bg: Background color.
        is_large_text: If True, uses 4.5:1 threshold (>=18pt or >=14pt bold), else 7.0:1.

    Returns:
        bool: True if compliant.
    """
    ratio = calculate_contrast_ratio(fg, bg)
    return ratio >= (4.5 if is_large_text else 7.0)


def is_ui_component_compliant(
    fg: Union[str, Color],
    bg: Union[str, Color],
) -> bool:
    """Check if color pair satisfies WCAG 2.1 Success Criterion 1.4.11 for UI components.

    Threshold: >= 3.0:1 for graphical objects, icons, and interactive element boundaries.

    Args:
        fg: Foreground / border / icon color.
        bg: Adjacent background color.

    Returns:
        bool: True if ratio >= 3.0.
    """
    ratio = calculate_contrast_ratio(fg, bg)
    return ratio >= 3.0


def get_wcag_levels_passed(
    fg: Union[str, Color],
    bg: Union[str, Color],
) -> List[WCAGLevel]:
    """Retrieve list of all WCAG levels satisfied by the color pair.

    Args:
        fg: Foreground color.
        bg: Background color.

    Returns:
        List[WCAGLevel]: List of satisfied levels.
    """
    result = evaluate_wcag(fg, bg)
    levels: List[WCAGLevel] = []

    if result.aa_normal_pass:
        levels.append(WCAGLevel.AA_NORMAL)
    if result.aa_large_pass:
        levels.append(WCAGLevel.AA_LARGE)
    if result.aaa_normal_pass:
        levels.append(WCAGLevel.AAA_NORMAL)
    if result.aaa_large_pass:
        levels.append(WCAGLevel.AAA_LARGE)
    if result.ui_component_pass:
        levels.append(WCAGLevel.UI_COMPONENT)

    return levels


def check_contrast(
    fg: Union[str, Color],
    bg: Union[str, Color],
    level: Union[str, WCAGLevel] = WCAGLevel.AA_NORMAL,
) -> bool:
    """Quick boolean check if a pair meets a specific level.

    Args:
        fg: Foreground color.
        bg: Background color.
        level: WCAGLevel enum or string ("AA_NORMAL", "AA_LARGE", "AAA_NORMAL", "AAA_LARGE", "UI_COMPONENT").

    Returns:
        bool: True if target level is met.
    """
    if isinstance(level, str):
        level_enum = WCAGLevel(level)
    else:
        level_enum = level

    result = evaluate_wcag(fg, bg)
    return result.passes(level_enum)
