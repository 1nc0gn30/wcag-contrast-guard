"""Pure Python color space parser, converter, colorimetry, and perceptual distance library.

Supports:
- Parsing Hex (3, 4, 6, 8 digits), RGB/RGBA, HSL/HSLA, and 148 standard CSS named colors.
- Conversions between sRGB, Linear RGB, CIE XYZ (D65 illuminant), CIE L*a*b*, and CIE L*C*h*.
- Relative luminance computation (WCAG 2.1 standard formula).
- Color difference metrics: Euclidean CIE ΔE76 and CIEDE2000 (ΔE00).
- Alpha compositing / Porter-Duff source-over blending over background colors.
- Zero external dependencies (pure Python standard library).
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Optional, Sequence, Tuple, Union

from wcag_contrast_guard.models import Color

# -------------------------------------------------------------------------
# 148 Standard CSS Color Names Mapping to Hex
# -------------------------------------------------------------------------
NAMED_CSS_COLORS: Dict[str, str] = {
    "aliceblue": "#f0f8ff",
    "antiquewhite": "#faebd7",
    "aqua": "#00ffff",
    "aquamarine": "#7fffd4",
    "azure": "#f0ffff",
    "beige": "#f5f5dc",
    "bisque": "#ffe4c4",
    "black": "#000000",
    "blanchedalmond": "#ffebcd",
    "blue": "#0000ff",
    "blueviolet": "#8a2be2",
    "brown": "#a52a2a",
    "burlywood": "#deb887",
    "cadetblue": "#5f9ea0",
    "chartreuse": "#7fff00",
    "chocolate": "#d2691e",
    "coral": "#ff7f50",
    "cornflowerblue": "#6495ed",
    "cornsilk": "#fff8dc",
    "crimson": "#dc143c",
    "cyan": "#00ffff",
    "darkblue": "#00008b",
    "darkcyan": "#008b8b",
    "darkgoldenrod": "#b8860b",
    "darkgray": "#a9a9a9",
    "darkgreen": "#006400",
    "darkgrey": "#a9a9a9",
    "darkkhaki": "#bdb76b",
    "darkmagenta": "#8b008b",
    "darkolivegreen": "#556b2f",
    "darkorange": "#ff8c00",
    "darkorchid": "#9932cc",
    "darkred": "#8b0000",
    "darksalmon": "#e9967a",
    "darkseagreen": "#8fbc8f",
    "darkslateblue": "#483d8b",
    "darkslategray": "#2f4f4f",
    "darkslategrey": "#2f4f4f",
    "darkturquoise": "#00ced1",
    "darkviolet": "#9400d3",
    "deeppink": "#ff1493",
    "deepskyblue": "#00bfff",
    "dimgray": "#696969",
    "dimgrey": "#696969",
    "dodgerblue": "#1e90ff",
    "firebrick": "#b22222",
    "floralwhite": "#fffaf0",
    "forestgreen": "#228b22",
    "fuchsia": "#ff00ff",
    "gainsboro": "#dcdcdc",
    "ghostwhite": "#f8f8ff",
    "gold": "#ffd700",
    "goldenrod": "#daa520",
    "gray": "#808080",
    "green": "#008000",
    "greenyellow": "#adff2f",
    "grey": "#808080",
    "honeydew": "#f0fff0",
    "hotpink": "#ff69b4",
    "indianred": "#cd5c5c",
    "indigo": "#4b0082",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "lavender": "#e6e6fa",
    "lavenderblush": "#fff0f5",
    "lawngreen": "#7cfc00",
    "lemonchiffon": "#fffacd",
    "lightblue": "#add8e6",
    "lightcoral": "#f08080",
    "lightcyan": "#e0ffff",
    "lightgoldenrodyellow": "#fafad2",
    "lightgray": "#d3d3d3",
    "lightgreen": "#90ee90",
    "lightgrey": "#d3d3d3",
    "lightpink": "#ffb6c1",
    "lightsalmon": "#ffa07a",
    "lightseagreen": "#20b2aa",
    "lightskyblue": "#87cefa",
    "lightslategray": "#778899",
    "lightslategrey": "#778899",
    "lightsteelblue": "#b0c4de",
    "lightyellow": "#ffffe0",
    "lime": "#00ff00",
    "limegreen": "#32cd32",
    "linen": "#faf0e6",
    "magenta": "#ff00ff",
    "maroon": "#800000",
    "mediumaquamarine": "#66cdaa",
    "mediumblue": "#0000cd",
    "mediumorchid": "#ba55d3",
    "mediumpurple": "#9370db",
    "mediumseagreen": "#3cb371",
    "mediumslateblue": "#7b68ee",
    "mediumspringgreen": "#00fa9a",
    "mediumturquoise": "#48d1cc",
    "mediumvioletred": "#c71585",
    "midnightblue": "#191970",
    "mintcream": "#f5fffa",
    "mistyrose": "#ffe4e1",
    "moccasin": "#ffe4b5",
    "navajowhite": "#ffdead",
    "navy": "#000080",
    "oldlace": "#fdf5e6",
    "olive": "#808000",
    "olivedrab": "#6b8e23",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "orchid": "#da70d6",
    "palegoldenrod": "#eee8aa",
    "palegreen": "#98fb98",
    "paleturquoise": "#afeeee",
    "palevioletred": "#db7093",
    "papayawhip": "#ffefd5",
    "peachpuff": "#ffdab9",
    "peru": "#cd853f",
    "pink": "#ffc0cb",
    "plum": "#dda0dd",
    "powderblue": "#b0e0e6",
    "purple": "#800080",
    "rebeccapurple": "#663399",
    "red": "#ff0000",
    "rosybrown": "#bc8f8f",
    "royalblue": "#4169e1",
    "saddlebrown": "#8b4513",
    "salmon": "#fa8072",
    "sandybrown": "#f4a460",
    "seagreen": "#2e8b57",
    "seashell": "#fff5ee",
    "sienna": "#a0522d",
    "silver": "#c0c0c0",
    "skyblue": "#87ceeb",
    "slateblue": "#6a5acd",
    "slategray": "#708090",
    "slategrey": "#708090",
    "snow": "#fffafa",
    "springgreen": "#00ff7f",
    "steelblue": "#4682b4",
    "tan": "#d2b48c",
    "teal": "#008080",
    "thistle": "#d8bfd8",
    "tomato": "#ff6347",
    "transparent": "#00000000",
    "turquoise": "#40e0d0",
    "violet": "#ee82ee",
    "wheat": "#f5deb3",
    "white": "#ffffff",
    "whitesmoke": "#f5f5f5",
    "yellow": "#ffff00",
    "yellowgreen": "#9acd32",
}

# Reference white D65 in 2-degree observer CIE XYZ (normalized Y=1.0)
D65_XYZ_REF = (0.95047, 1.00000, 1.08883)


# -------------------------------------------------------------------------
# Parsing Routines
# -------------------------------------------------------------------------

_HEX_REGEX = re.compile(r"^#?([0-9a-fA-F]{3,8})$")
_RGB_REGEX = re.compile(
    r"^rgba?\s*\(\s*([\d\.]+%?)\s*[, ]\s*([\d\.]+%?)\s*[, ]\s*([\d\.]+%?)(?:\s*[,/]\s*([\d\.]+%?))?\s*\)$",
    re.IGNORECASE,
)
_HSL_REGEX = re.compile(
    r"^hsla?\s*\(\s*([\d\.]+(?:deg|rad|turn|grad)?)\s*[, ]\s*([\d\.]+%?)\s*[, ]\s*([\d\.]+%?)(?:\s*[,/]\s*([\d\.]+%?))?\s*\)$",
    re.IGNORECASE,
)


def _parse_channel_value(val_str: str, max_val: float = 255.0) -> float:
    """Parse a channel number or percentage string into a float."""
    v = val_str.strip()
    if v.endswith("%"):
        return (float(v[:-1]) / 100.0) * max_val
    return float(v)


def _parse_alpha_value(val_str: Optional[str]) -> float:
    """Parse an alpha component string into [0.0, 1.0]."""
    if val_str is None:
        return 1.0
    v = val_str.strip()
    if v.endswith("%"):
        return max(0.0, min(1.0, float(v[:-1]) / 100.0))
    return max(0.0, min(1.0, float(v)))


def _parse_hue_angle(val_str: str) -> float:
    """Parse hue value with optional units (deg, rad, turn, grad) into degrees [0, 360)."""
    v = val_str.strip().lower()
    if v.endswith("deg"):
        deg = float(v[:-3])
    elif v.endswith("rad"):
        deg = float(v[:-3]) * (180.0 / math.pi)
    elif v.endswith("turn"):
        deg = float(v[:-4]) * 360.0
    elif v.endswith("grad"):
        deg = float(v[:-4]) * 0.9
    else:
        deg = float(v)
    return deg % 360.0


def parse_color(value: Union[str, Tuple, List, Dict[str, Any], Color]) -> Color:
    """Parse any color representation into a strongly-typed Color model.

    Supports:
    - `Color` instance (returns as-is or cloned)
    - Hex strings: `#rgb`, `#rgba`, `#rrggbb`, `#rrggbbaa`, or without `#`
    - RGB/RGBA strings: `rgb(255, 0, 0)`, `rgba(255, 0, 0, 0.8)`, `rgb(100% 0% 0% / 0.5)`
    - HSL/HSLA strings: `hsl(210, 100%, 50%)`, `hsla(210deg, 100%, 50%, 0.5)`
    - Named CSS colors: `red`, `rebeccapurple`, `dodgerblue`, etc.
    - Tuples / Lists: `(r, g, b)`, `(r, g, b, a)`
    - Dictionaries: `{'r': 255, 'g': 0, 'b': 0}`, `{'hex': '#ff0000'}`, etc.

    Args:
        value: Input color representation.

    Returns:
        Color: Initialized and validated Color dataclass instance.

    Raises:
        ValueError: If input format is invalid or cannot be parsed.
    """
    if isinstance(value, Color):
        return Color(r=value.r, g=value.g, b=value.b, a=value.a)

    if isinstance(value, (tuple, list)):
        if len(value) == 3:
            return Color(r=int(value[0]), g=int(value[1]), b=int(value[2]), a=1.0)
        elif len(value) == 4:
            return Color(r=int(value[0]), g=int(value[1]), b=int(value[2]), a=float(value[3]))
        raise ValueError(f"Color sequence must have 3 or 4 elements, got {len(value)}")

    if isinstance(value, dict):
        if "r" in value and "g" in value and "b" in value:
            return Color(
                r=int(value["r"]),
                g=int(value["g"]),
                b=int(value["b"]),
                a=float(value.get("a", 1.0)),
            )
        if "hex" in value:
            return parse_color(value["hex"])
        raise ValueError(f"Invalid color dictionary: {value}")

    if not isinstance(value, str):
        raise ValueError(f"Unsupported color type: {type(value)}")

    raw = value.strip().lower()

    # Named CSS colors
    if raw in NAMED_CSS_COLORS:
        return parse_color(NAMED_CSS_COLORS[raw])

    # RGB / RGBA match
    rgb_match = _RGB_REGEX.match(raw)
    if rgb_match:
        r_str, g_str, b_str, a_str = rgb_match.groups()
        r = _parse_channel_value(r_str, 255.0)
        g = _parse_channel_value(g_str, 255.0)
        b = _parse_channel_value(b_str, 255.0)
        a = _parse_alpha_value(a_str)
        return Color(r=int(round(r)), g=int(round(g)), b=int(round(b)), a=a)

    # HSL / HSLA match
    hsl_match = _HSL_REGEX.match(raw)
    if hsl_match:
        h_str, s_str, l_str, a_str = hsl_match.groups()
        h = _parse_hue_angle(h_str)
        s = _parse_channel_value(s_str, 100.0)
        l = _parse_channel_value(l_str, 100.0)
        a = _parse_alpha_value(a_str)
        r, g, b = hsl_to_rgb(h, s, l)
        return Color(r=r, g=g, b=b, a=a, hsl=(round(h, 2), round(s, 2), round(l, 2)))

    # Hex match
    hex_match = _HEX_REGEX.match(raw)
    if hex_match:
        hex_digits = hex_match.group(1)
        if len(hex_digits) == 3:  # #rgb
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16)
            b = int(hex_digits[2] * 2, 16)
            return Color(r=r, g=g, b=b, a=1.0)
        elif len(hex_digits) == 4:  # #rgba
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16)
            b = int(hex_digits[2] * 2, 16)
            a = int(hex_digits[3] * 2, 16) / 255.0
            return Color(r=r, g=g, b=b, a=a)
        elif len(hex_digits) == 6:  # #rrggbb
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
            return Color(r=r, g=g, b=b, a=1.0)
        elif len(hex_digits) == 8:  # #rrggbbaa
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
            a = int(hex_digits[6:8], 16) / 255.0
            return Color(r=r, g=g, b=b, a=a)

    raise ValueError(f"Unable to parse color format: '{value}'")


# -------------------------------------------------------------------------
# sRGB & HSL Conversions
# -------------------------------------------------------------------------

def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB channels [0, 255] to HSL (Hue [0, 360), Saturation [0, 100], Lightness [0, 100]).

    Args:
        r: Red channel integer [0, 255].
        g: Green channel integer [0, 255].
        b: Blue channel integer [0, 255].

    Returns:
        Tuple[float, float, float]: (H, S, L).
    """
    r_n = r / 255.0
    g_n = g / 255.0
    b_n = b / 255.0

    c_max = max(r_n, g_n, b_n)
    c_min = min(r_n, g_n, b_n)
    delta = c_max - c_min

    l = (c_max + c_min) / 2.0

    if delta == 0.0:
        h = 0.0
        s = 0.0
    else:
        s = delta / (1.0 - abs(2.0 * l - 1.0)) if l not in (0.0, 1.0) else 0.0
        if c_max == r_n:
            h = 60.0 * (((g_n - b_n) / delta) % 6.0)
        elif c_max == g_n:
            h = 60.0 * (((b_n - r_n) / delta) + 2.0)
        else:
            h = 60.0 * (((r_n - g_n) / delta) + 4.0)

    return (round(h % 360.0, 2), round(s * 100.0, 2), round(l * 100.0, 2))


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL values to sRGB integers [0, 255].

    Args:
        h: Hue in degrees [0, 360).
        s: Saturation in percent [0, 100].
        l: Lightness in percent [0, 100].

    Returns:
        Tuple[int, int, int]: (r, g, b).
    """
    h_deg = h % 360.0
    s_norm = max(0.0, min(100.0, s)) / 100.0
    l_norm = max(0.0, min(100.0, l)) / 100.0

    c = (1.0 - abs(2.0 * l_norm - 1.0)) * s_norm
    x = c * (1.0 - abs((h_deg / 60.0) % 2.0 - 1.0))
    m = l_norm - c / 2.0

    if 0.0 <= h_deg < 60.0:
        r_p, g_p, b_p = c, x, 0.0
    elif 60.0 <= h_deg < 120.0:
        r_p, g_p, b_p = x, c, 0.0
    elif 120.0 <= h_deg < 180.0:
        r_p, g_p, b_p = 0.0, c, x
    elif 180.0 <= h_deg < 240.0:
        r_p, g_p, b_p = 0.0, x, c
    elif 240.0 <= h_deg < 300.0:
        r_p, g_p, b_p = x, 0.0, c
    else:
        r_p, g_p, b_p = c, 0.0, x

    r = max(0, min(255, int(round((r_p + m) * 255.0))))
    g = max(0, min(255, int(round((g_p + m) * 255.0))))
    b = max(0, min(255, int(round((b_p + m) * 255.0))))
    return (r, g, b)


# -------------------------------------------------------------------------
# Gamma Expansion & Relative Luminance
# -------------------------------------------------------------------------

def srgb_to_linear(c_srgb: float) -> float:
    """Convert sRGB channel in [0.0, 1.0] to Linear RGB using IEC 61966-2-1 standard.

    Args:
        c_srgb: Normalized sRGB channel float in [0.0, 1.0].

    Returns:
        float: Linearized channel value in [0.0, 1.0].
    """
    c = max(0.0, min(1.0, c_srgb))
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c_linear: float) -> float:
    """Convert Linear RGB channel to normalized sRGB in [0.0, 1.0].

    Args:
        c_linear: Linear channel value in [0.0, 1.0].

    Returns:
        float: Gamma-compressed sRGB channel value in [0.0, 1.0].
    """
    c = max(0.0, min(1.0, c_linear))
    if c <= 0.0031308:
        val = c * 12.92
    else:
        val = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return max(0.0, min(1.0, val))


def get_relative_luminance(color: Union[str, Color, Tuple[int, int, int]]) -> float:
    """Calculate WCAG 2.1 relative luminance for an sRGB color.

    Formula:
        L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin

    Args:
        color: Input color representation.

    Returns:
        float: Relative luminance in [0.0, 1.0].
    """
    c = parse_color(color) if not isinstance(color, Color) else color
    r_lin = srgb_to_linear(c.r / 255.0)
    g_lin = srgb_to_linear(c.g / 255.0)
    b_lin = srgb_to_linear(c.b / 255.0)
    return round(0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin, 6)


# -------------------------------------------------------------------------
# CIE XYZ, CIE L*a*b*, and CIE L*C*h* Conversions
# -------------------------------------------------------------------------

def rgb_to_xyz(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert sRGB channels [0, 255] to CIE XYZ (D65 illuminant, Y normalized to 1.0).

    Args:
        r: Red channel [0, 255].
        g: Green channel [0, 255].
        b: Blue channel [0, 255].

    Returns:
        Tuple[float, float, float]: (X, Y, Z).
    """
    r_lin = srgb_to_linear(r / 255.0)
    g_lin = srgb_to_linear(g / 255.0)
    b_lin = srgb_to_linear(b / 255.0)

    # Standard sRGB D65 transformation matrix
    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    return (x, y, z)


def xyz_to_rgb(x: float, y: float, z: float) -> Tuple[int, int, int]:
    """Convert CIE XYZ (D65 illuminant) to sRGB integers [0, 255].

    Args:
        x: X component.
        y: Y component.
        z: Z component.

    Returns:
        Tuple[int, int, int]: (r, g, b).
    """
    # Inverse standard sRGB D65 transformation matrix
    r_lin = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g_lin = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    b_lin = x * 0.0556434 + y * -0.2040259 + z * 1.0572252

    r = int(round(linear_to_srgb(r_lin) * 255.0))
    g = int(round(linear_to_srgb(g_lin) * 255.0))
    b = int(round(linear_to_srgb(b_lin) * 255.0))

    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _lab_f(t: float) -> float:
    """CIE standard non-linear transformation function."""
    delta = 6.0 / 29.0
    if t > delta ** 3:
        return t ** (1.0 / 3.0)
    return (t / (3.0 * delta ** 2)) + (4.0 / 29.0)


def _lab_f_inv(t: float) -> float:
    """Inverse of CIE standard non-linear transformation function."""
    delta = 6.0 / 29.0
    if t > delta:
        return t ** 3.0
    return 3.0 * (delta ** 2) * (t - 4.0 / 29.0)


def xyz_to_lab(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Convert CIE XYZ (D65 reference white) to CIE L*a*b*.

    Args:
        x: X component.
        y: Y component.
        z: Z component.

    Returns:
        Tuple[float, float, float]: (L*, a*, b*).
    """
    xn, yn, zn = D65_XYZ_REF
    fx = _lab_f(x / xn)
    fy = _lab_f(y / yn)
    fz = _lab_f(z / zn)

    l_star = 116.0 * fy - 16.0
    a_star = 500.0 * (fx - fy)
    b_star = 200.0 * (fy - fz)

    return (l_star, a_star, b_star)


def lab_to_xyz(l_star: float, a_star: float, b_star: float) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to CIE XYZ (D65 reference white).

    Args:
        l_star: Lightness [0, 100].
        a_star: Green-Red axis.
        b_star: Blue-Yellow axis.

    Returns:
        Tuple[float, float, float]: (X, Y, Z).
    """
    xn, yn, zn = D65_XYZ_REF
    fy = (l_star + 16.0) / 116.0
    fx = fy + (a_star / 500.0)
    fz = fy - (b_star / 200.0)

    x = xn * _lab_f_inv(fx)
    y = yn * _lab_f_inv(fy)
    z = zn * _lab_f_inv(fz)

    return (x, y, z)


def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Direct conversion from sRGB [0, 255] to CIE L*a*b*.

    Args:
        r: Red channel [0, 255].
        g: Green channel [0, 255].
        b: Blue channel [0, 255].

    Returns:
        Tuple[float, float, float]: (L*, a*, b*).
    """
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)


def lab_to_rgb(l_star: float, a_star: float, b_star: float) -> Tuple[int, int, int]:
    """Direct conversion from CIE L*a*b* to clamped sRGB [0, 255].

    Args:
        l_star: Lightness in [0, 100].
        a_star: a* axis.
        b_star: b* axis.

    Returns:
        Tuple[int, int, int]: (r, g, b).
    """
    x, y, z = lab_to_xyz(l_star, a_star, b_star)
    return xyz_to_rgb(x, y, z)


def lab_to_lch(l_star: float, a_star: float, b_star: float) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to cylindrical CIE L*C*h* (Lightness, Chroma, Hue angle degrees).

    Args:
        l_star: L* in [0, 100].
        a_star: a* component.
        b_star: b* component.

    Returns:
        Tuple[float, float, float]: (L*, C*, h°).
    """
    chroma = math.sqrt(a_star ** 2 + b_star ** 2)
    h_rad = math.atan2(b_star, a_star)
    h_deg = math.degrees(h_rad) % 360.0
    return (l_star, chroma, h_deg)


def lch_to_lab(l_star: float, chroma: float, hue_deg: float) -> Tuple[float, float, float]:
    """Convert cylindrical CIE L*C*h* to rectangular CIE L*a*b*.

    Args:
        l_star: Lightness in [0, 100].
        chroma: Chroma >= 0.
        hue_deg: Hue angle in degrees [0, 360).

    Returns:
        Tuple[float, float, float]: (L*, a*, b*).
    """
    h_rad = math.radians(hue_deg)
    a_star = chroma * math.cos(h_rad)
    b_star = chroma * math.sin(h_rad)
    return (l_star, a_star, b_star)


# -------------------------------------------------------------------------
# Color Difference Metrics: CIE ΔE76 and CIEDE2000 (ΔE00)
# -------------------------------------------------------------------------

def delta_e_76(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
) -> float:
    """Calculate CIE ΔE76 Euclidean distance between two colors in Lab space.

    Args:
        lab1: (L1*, a1*, b1*).
        lab2: (L2*, a2*, b2*).

    Returns:
        float: ΔE76 color difference.
    """
    dl = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return math.sqrt(dl * dl + da * da + db * db)


def delta_e_ciede2000(
    lab1: Tuple[float, float, float],
    lab2: Tuple[float, float, float],
    k_l: float = 1.0,
    k_c: float = 1.0,
    k_h: float = 1.0,
) -> float:
    """Calculate CIEDE2000 (ΔE00) perceptual color difference standard.

    Implements the full ISO/CIE 11664-6:2014 / Sharma et al. 2005 formulation.

    Args:
        lab1: (L1*, a1*, b1*) reference color.
        lab2: (L2*, a2*, b2*) comparison color.
        k_l: Lightness parametric weighting factor (default 1.0).
        k_c: Chroma parametric weighting factor (default 1.0).
        k_h: Hue parametric weighting factor (default 1.0).

    Returns:
        float: CIEDE2000 ΔE00 value (perceptual distance).
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.sqrt(a1 * a1 + b1 * b1)
    c2 = math.sqrt(a2 * a2 + b2 * b2)
    c_bar = (c1 + c2) / 2.0

    c_bar_7 = c_bar ** 7
    g = 0.5 * (1.0 - math.sqrt(c_bar_7 / (c_bar_7 + 25.0 ** 7)))

    a1_prime = (1.0 + g) * a1
    a2_prime = (1.0 + g) * a2

    c1_prime = math.sqrt(a1_prime * a1_prime + b1 * b1)
    c2_prime = math.sqrt(a2_prime * a2_prime + b2 * b2)

    # Hue angles in degrees [0, 360)
    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360.0
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360.0

    delta_l_prime = l2 - l1
    delta_c_prime = c2_prime - c1_prime

    # Compute delta h prime
    if c1_prime * c2_prime == 0.0:
        delta_h_prime = 0.0
    elif abs(h2_prime - h1_prime) <= 180.0:
        delta_h_prime = h2_prime - h1_prime
    elif h2_prime - h1_prime > 180.0:
        delta_h_prime = (h2_prime - h1_prime) - 360.0
    else:
        delta_h_prime = (h2_prime - h1_prime) + 360.0

    delta_capital_h_prime = 2.0 * math.sqrt(c1_prime * c2_prime) * math.sin(math.radians(delta_h_prime / 2.0))

    # Average L', C', h'
    l_bar_prime = (l1 + l2) / 2.0
    c_bar_prime = (c1_prime + c2_prime) / 2.0

    if c1_prime * c2_prime == 0.0:
        h_bar_prime = h1_prime + h2_prime
    elif abs(h1_prime - h2_prime) <= 180.0:
        h_bar_prime = (h1_prime + h2_prime) / 2.0
    elif (h1_prime + h2_prime) < 360.0:
        h_bar_prime = (h1_prime + h2_prime + 360.0) / 2.0
    else:
        h_bar_prime = (h1_prime + h2_prime - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_bar_prime - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_bar_prime))
        + 0.32 * math.cos(math.radians(3.0 * h_bar_prime + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_bar_prime - 63.0))
    )

    delta_theta = 30.0 * math.exp(-(((h_bar_prime - 275.0) / 25.0) ** 2))
    c_bar_prime_7 = c_bar_prime ** 7
    r_c = 2.0 * math.sqrt(c_bar_prime_7 / (c_bar_prime_7 + 25.0 ** 7))

    s_l = 1.0 + ((0.015 * ((l_bar_prime - 50.0) ** 2)) / math.sqrt(20.0 + ((l_bar_prime - 50.0) ** 2)))
    s_c = 1.0 + 0.045 * c_bar_prime
    s_h = 1.0 + 0.015 * c_bar_prime * t

    r_t = -math.sin(math.radians(2.0 * delta_theta)) * r_c

    term_l = delta_l_prime / (k_l * s_l)
    term_c = delta_c_prime / (k_c * s_c)
    term_h = delta_capital_h_prime / (k_h * s_h)

    delta_e_sq = (term_l ** 2) + (term_c ** 2) + (term_h ** 2) + (r_t * term_c * term_h)
    return math.sqrt(max(0.0, delta_e_sq))


def color_distance(
    c1: Union[str, Color, Tuple[int, int, int]],
    c2: Union[str, Color, Tuple[int, int, int]],
    formula: str = "ciede2000",
) -> float:
    """Calculate perceptual color difference between two colors.

    Args:
        c1: First color.
        c2: Second color.
        formula: 'ciede2000' or 'ciedeltae00' (default) or 'de76'.

    Returns:
        float: Calculated color difference ΔE.
    """
    col1 = parse_color(c1) if not isinstance(c1, Color) else c1
    col2 = parse_color(c2) if not isinstance(c2, Color) else c2

    lab1 = rgb_to_lab(col1.r, col1.g, col1.b)
    lab2 = rgb_to_lab(col2.r, col2.g, col2.b)

    if formula.lower() in ("de76", "deltae76", "76"):
        return delta_e_76(lab1, lab2)
    return delta_e_ciede2000(lab1, lab2)


# -------------------------------------------------------------------------
# Alpha Blending / Compositing
# -------------------------------------------------------------------------

def blend_alpha(
    foreground: Union[str, Color],
    background: Union[str, Color],
) -> Color:
    """Composite a semi-transparent foreground color over a background color.

    Uses the standard Porter-Duff Source Over alpha compositing formula:
        alpha_out = alpha_fg + alpha_bg * (1 - alpha_fg)
        C_out = (alpha_fg * C_fg + alpha_bg * (1 - alpha_fg) * C_bg) / alpha_out

    Args:
        foreground: Foreground color (may be transparent).
        background: Background color (may be opaque or transparent).

    Returns:
        Color: Composited blended color.
    """
    fg = parse_color(foreground) if not isinstance(foreground, Color) else foreground
    bg = parse_color(background) if not isinstance(background, Color) else background

    if fg.a >= 0.999:
        return Color(r=fg.r, g=fg.g, b=fg.b, a=1.0)

    a_fg = fg.a
    a_bg = bg.a

    a_out = a_fg + a_bg * (1.0 - a_fg)

    if a_out <= 0.0:
        return Color(r=0, g=0, b=0, a=0.0)

    r_out = (fg.r * a_fg + bg.r * a_bg * (1.0 - a_fg)) / a_out
    g_out = (fg.g * a_fg + bg.g * a_bg * (1.0 - a_fg)) / a_out
    b_out = (fg.b * a_fg + bg.b * a_bg * (1.0 - a_fg)) / a_out

    return Color(
        r=int(round(r_out)),
        g=int(round(g_out)),
        b=int(round(b_out)),
        a=min(1.0, a_out),
    )
