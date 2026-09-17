"""Advanced Perceptual Contrast Algorithm (APCA-W3 0.98G) evaluation engine.

Implements the modern perceptual contrast algorithm designed for WCAG 3.0 / Silver,
accounting for human spatial frequency vision, non-linear human lightness perception,
text polarity (dark-on-light vs light-on-dark), and dynamic font size requirements.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple, Union

from wcag_contrast_guard.color_math import blend_alpha, parse_color
from wcag_contrast_guard.models import APCAResult, Color

# -------------------------------------------------------------------------
# APCA 0.98G Standard Constants
# -------------------------------------------------------------------------
# Coefficients for sRGB to Y (luminance)
R_COEFF = 0.2126729
G_COEFF = 0.7151522
B_COEFF = 0.0721750

# Power-law TRC
MAIN_TRC = 2.4

# Normal polarity (Dark text on Light background - BoW)
NORM_BG = 0.56
NORM_TXT = 0.57

# Reverse polarity (Light text on Dark background - WoB)
REV_BG = 0.65
REV_TXT = 0.62

# Clamping and scaling constants
BLK_THRS = 0.022
BLK_CLMP = 1.414
SCALE_BOW = 1.14
SCALE_WOB = 1.14
LO_BOW_OFFSET = 0.027
LO_WOB_OFFSET = 0.027
DELTA_Y_MIN = 0.0005
LO_CLIP = 0.1


def _srgb_to_apca_y(color: Color) -> float:
    """Calculate clamped APCA perceptual Y luminance with soft black clamp.

    Args:
        color: Opaque or composited Color.

    Returns:
        float: Clamped APCA Y luminance in [0.0, 1.0].
    """
    r_lin = (color.r / 255.0) ** MAIN_TRC
    g_lin = (color.g / 255.0) ** MAIN_TRC
    b_lin = (color.b / 255.0) ** MAIN_TRC

    y = r_lin * R_COEFF + g_lin * G_COEFF + b_lin * B_COEFF

    # Soft black clamp
    if y < BLK_THRS:
        y += (BLK_THRS - y) ** BLK_CLMP

    return y


def calculate_apca_lc(
    fg: Union[str, Color],
    bg: Union[str, Color],
) -> float:
    """Calculate the APCA Lightness Contrast (Lc) value between text and background.

    Positive Lc indicates Dark text on Light background (BoW).
    Negative Lc indicates Light text on Dark background (WoB).

    Args:
        fg: Foreground (text) color representation.
        bg: Background color representation.

    Returns:
        float: Lc score in the approximate range [-108.0, 108.0].
    """
    fg_col = parse_color(fg) if not isinstance(fg, Color) else fg
    bg_col = parse_color(bg) if not isinstance(bg, Color) else bg

    # Blend foreground over background if semi-transparent
    if not fg_col.is_opaque:
        fg_effective = blend_alpha(fg_col, bg_col)
    else:
        fg_effective = fg_col

    y_txt = _srgb_to_apca_y(fg_effective)
    y_bg = _srgb_to_apca_y(bg_col)

    # Near-zero luminance differential cutoff
    if abs(y_bg - y_txt) < DELTA_Y_MIN:
        return 0.0

    if y_bg > y_txt:
        # Dark text on Light background (BoW)
        s_bg = y_bg ** NORM_BG
        s_txt = y_txt ** NORM_TXT
        s_diff = s_bg - s_txt
        c_val = s_diff * SCALE_BOW
        if c_val < LO_CLIP:
            lc = 0.0
        else:
            lc = (c_val - LO_BOW_OFFSET) * 100.0
    else:
        # Light text on Dark background (WoB)
        s_bg = y_bg ** REV_BG
        s_txt = y_txt ** REV_TXT
        s_diff = s_bg - s_txt
        c_val = s_diff * SCALE_WOB
        if -c_val < LO_CLIP:
            lc = 0.0
        else:
            lc = (c_val + LO_WOB_OFFSET) * 100.0

    return round(lc, 4)


def _get_min_font_sizes(abs_lc: float) -> Dict[int, float]:
    """Retrieve minimum recommended font sizes (in pt) for weights 100-900 based on APCA Lc."""
    if abs_lc >= 90.0:
        return {
            100: 36.0, 200: 24.0, 300: 18.0, 400: 14.0,
            500: 13.0, 600: 12.0, 700: 12.0, 800: 11.0, 900: 11.0,
        }
    elif abs_lc >= 75.0:
        return {
            100: 48.0, 200: 32.0, 300: 21.0, 400: 16.0,
            500: 15.0, 600: 14.0, 700: 14.0, 800: 13.0, 900: 13.0,
        }
    elif abs_lc >= 60.0:
        return {
            100: 60.0, 200: 42.0, 300: 28.0, 400: 20.0,
            500: 18.0, 600: 16.0, 700: 16.0, 800: 15.0, 900: 15.0,
        }
    elif abs_lc >= 45.0:
        return {
            100: 72.0, 200: 54.0, 300: 36.0, 400: 24.0,
            500: 22.0, 600: 20.0, 700: 18.0, 800: 18.0, 900: 18.0,
        }
    elif abs_lc >= 30.0:
        return {
            100: float("inf"), 200: float("inf"), 300: 60.0, 400: 40.0,
            500: 36.0, 600: 32.0, 700: 28.0, 800: 26.0, 900: 24.0,
        }
    else:
        return {w: float("inf") for w in range(100, 1000, 100)}


def evaluate_apca(
    fg: Union[str, Color],
    bg: Union[str, Color],
) -> APCAResult:
    """Evaluate color pair contrast using the APCA-W3 0.98G standard.

    Args:
        fg: Foreground / text color.
        bg: Background color.

    Returns:
        APCAResult: Full APCA analysis with Lc, polarity, font thresholds, and ratings.
    """
    lc = calculate_apca_lc(fg, bg)
    abs_lc = abs(lc)

    if lc > 0.0:
        polarity = "dark-on-light"
    elif lc < 0.0:
        polarity = "light-on-dark"
    else:
        polarity = "none"

    font_sizes = _get_min_font_sizes(abs_lc)

    if abs_lc >= 90.0:
        accessible_use = "Body Text (Fluent reading, all weights >=14pt/400)"
        rating = "Pass (Preferred Body)"
    elif abs_lc >= 75.0:
        accessible_use = "Body Text (Standard reading, >=16pt/400 or >=14pt/700)"
        rating = "Pass (Minimum Body)"
    elif abs_lc >= 60.0:
        accessible_use = "Content Text / Sub-fluent (Headings, large text >=20pt/400)"
        rating = "Pass (Content / Large)"
    elif abs_lc >= 45.0:
        accessible_use = "Large Display Text / Headlines (>=24pt/400 or >=18pt/700)"
        rating = "Pass (Headlines Only)"
    elif abs_lc >= 30.0:
        accessible_use = "Non-text / UI Icons / Spot readable elements"
        rating = "Pass (Non-text / Icons)"
    else:
        accessible_use = "Forbidden / Inaccessible for reading"
        rating = "Fail (Inaccessible)"

    return APCAResult(
        lc=round(lc, 2),
        polarity=polarity,
        min_font_size_pt=font_sizes,
        accessible_use=accessible_use,
        rating=rating,
    )
