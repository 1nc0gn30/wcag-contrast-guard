"""Unified domain models for wcag-contrast-guard.

Defines core color structures, WCAG 2.1/2.2 evaluation results, APCA results,
color vision deficiency simulation structures, remediation suggestions,
and palette audit reports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Color:
    """Represents an RGBA color with derived sRGB, HSL, Hex, and relative luminance.

    Attributes:
        r: Red channel integer in [0, 255].
        g: Green channel integer in [0, 255].
        b: Blue channel integer in [0, 255].
        a: Alpha channel float in [0.0, 1.0] (default 1.0).
        hex: Hex representation string (e.g. '#1a73e8' or '#1a73e8ff').
        hsl: Tuple of (Hue [0, 360), Saturation [0, 100], Lightness [0, 100]).
        luminance: WCAG relative luminance float in [0.0, 1.0].
    """

    r: int
    g: int
    b: int
    a: float = 1.0
    hex: str = ""
    hsl: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    luminance: float = 0.0

    def __post_init__(self) -> None:
        """Ensure channels are clamped and auto-compute missing properties."""
        # Clamp RGBA channels
        object.__setattr__(self, "r", max(0, min(255, int(round(self.r)))))
        object.__setattr__(self, "g", max(0, min(255, int(round(self.g)))))
        object.__setattr__(self, "b", max(0, min(255, int(round(self.b)))))
        object.__setattr__(self, "a", max(0.0, min(1.0, float(self.a))))

        # Auto-compute hex if empty
        if not self.hex:
            if self.a >= 0.999:
                hex_val = f"#{self.r:02x}{self.g:02x}{self.b:02x}"
            else:
                alpha_int = int(round(self.a * 255))
                hex_val = f"#{self.r:02x}{self.g:02x}{self.b:02x}{alpha_int:02x}"
            object.__setattr__(self, "hex", hex_val)

        # Auto-compute HSL if default
        if self.hsl == (0.0, 0.0, 0.0) and (self.r > 0 or self.g > 0 or self.b > 0):
            r_norm = self.r / 255.0
            g_norm = self.g / 255.0
            b_norm = self.b / 255.0
            c_max = max(r_norm, g_norm, b_norm)
            c_min = min(r_norm, g_norm, b_norm)
            delta = c_max - c_min

            lightness = (c_max + c_min) / 2.0
            if delta == 0.0:
                hue = 0.0
                saturation = 0.0
            else:
                saturation = delta / (1.0 - abs(2.0 * lightness - 1.0)) if lightness not in (0.0, 1.0) else 0.0
                if c_max == r_norm:
                    hue = 60.0 * (((g_norm - b_norm) / delta) % 6.0)
                elif c_max == g_norm:
                    hue = 60.0 * (((b_norm - r_norm) / delta) + 2.0)
                else:
                    hue = 60.0 * (((r_norm - g_norm) / delta) + 4.0)

            object.__setattr__(
                self,
                "hsl",
                (round(hue % 360.0, 2), round(saturation * 100.0, 2), round(lightness * 100.0, 2)),
            )

        # Auto-compute relative luminance if not set
        if self.luminance == 0.0 and (self.r > 0 or self.g > 0 or self.b > 0):
            def _to_linear(c: float) -> float:
                v = c / 255.0
                return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

            r_lin = _to_linear(self.r)
            g_lin = _to_linear(self.g)
            b_lin = _to_linear(self.b)
            lum = 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin
            object.__setattr__(self, "luminance", round(lum, 6))

    @property
    def is_opaque(self) -> bool:
        """Check if color is fully opaque (alpha >= 0.999)."""
        return self.a >= 0.999

    def to_rgb_tuple(self) -> Tuple[int, int, int]:
        """Return (r, g, b) tuple."""
        return (self.r, self.g, self.b)

    def to_rgba_tuple(self) -> Tuple[int, int, int, float]:
        """Return (r, g, b, a) tuple."""
        return (self.r, self.g, self.b, self.a)

    def to_hex(self, include_alpha: bool = False) -> str:
        """Return hex formatted string."""
        if include_alpha or not self.is_opaque:
            alpha_int = int(round(self.a * 255))
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}{alpha_int:02x}"
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_css_rgb(self) -> str:
        """Format as CSS rgb() or rgba() string."""
        if self.is_opaque:
            return f"rgb({self.r}, {self.g}, {self.b})"
        return f"rgba({self.r}, {self.g}, {self.b}, {round(self.a, 3)})"

    def to_css_hsl(self) -> str:
        """Format as CSS hsl() or hsla() string."""
        h, s, l = self.hsl
        if self.is_opaque:
            return f"hsl({h:.1f}, {s:.1f}%, {l:.1f}%)"
        return f"hsla({h:.1f}, {s:.1f}%, {l:.1f}%, {round(self.a, 3)})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize color to dictionary."""
        return {
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "a": self.a,
            "hex": self.to_hex(include_alpha=not self.is_opaque),
            "hsl": {
                "h": self.hsl[0],
                "s": self.hsl[1],
                "l": self.hsl[2],
            },
            "luminance": self.luminance,
        }


class WCAGLevel(str, Enum):
    """WCAG 2.1 / 2.2 Conformance Levels and Element Types."""

    AA_LARGE = "AA_LARGE"          # >= 3.0:1 (>=18pt or >=14pt bold)
    AA_NORMAL = "AA_NORMAL"        # >= 4.5:1
    AAA_LARGE = "AAA_LARGE"        # >= 4.5:1
    AAA_NORMAL = "AAA_NORMAL"      # >= 7.0:1
    UI_COMPONENT = "UI_COMPONENT"  # >= 3.0:1 (graphical objects & UI components)


@dataclass
class WCAGResult:
    """Comprehensive WCAG 2.1/2.2 contrast evaluation result.

    Attributes:
        ratio: Numerical contrast ratio (e.g. 4.54).
        ratio_str: Human-readable ratio string (e.g. '4.54:1').
        aa_normal_pass: Pass status for AA Normal text (>= 4.5:1).
        aa_large_pass: Pass status for AA Large text (>= 3.0:1).
        aaa_normal_pass: Pass status for AAA Normal text (>= 7.0:1).
        aaa_large_pass: Pass status for AAA Large text (>= 4.5:1).
        ui_component_pass: Pass status for UI components/graphics (>= 3.0:1).
        foreground: Evaluated foreground color.
        background: Evaluated background color.
    """

    ratio: float
    ratio_str: str
    aa_normal_pass: bool
    aa_large_pass: bool
    aaa_normal_pass: bool
    aaa_large_pass: bool
    ui_component_pass: bool
    foreground: Color
    background: Color

    def passes(self, level: WCAGLevel) -> bool:
        """Check if contrast passes a specific WCAG level requirement."""
        if level == WCAGLevel.AA_NORMAL:
            return self.aa_normal_pass
        elif level == WCAGLevel.AA_LARGE:
            return self.aa_large_pass
        elif level == WCAGLevel.AAA_NORMAL:
            return self.aaa_normal_pass
        elif level == WCAGLevel.AAA_LARGE:
            return self.aaa_large_pass
        elif level == WCAGLevel.UI_COMPONENT:
            return self.ui_component_pass
        return False

    @property
    def highest_grade(self) -> str:
        """Determine highest WCAG level achieved."""
        if self.aaa_normal_pass:
            return "AAA Normal & Large"
        if self.aa_normal_pass:  # which also qualifies for AAA Large
            return "AA Normal & AAA Large"
        if self.aa_large_pass:
            return "AA Large & UI Component"
        return "Fail"

    def summary(self) -> str:
        """Generate human-readable summary of WCAG evaluation."""
        return (
            f"Contrast Ratio: {self.ratio_str} | "
            f"AA Normal: {'PASS' if self.aa_normal_pass else 'FAIL'} | "
            f"AA Large: {'PASS' if self.aa_large_pass else 'FAIL'} | "
            f"AAA Normal: {'PASS' if self.aaa_normal_pass else 'FAIL'} | "
            f"UI Components: {'PASS' if self.ui_component_pass else 'FAIL'}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert WCAGResult to dictionary."""
        return {
            "ratio": self.ratio,
            "ratio_str": self.ratio_str,
            "aa_normal_pass": self.aa_normal_pass,
            "aa_large_pass": self.aa_large_pass,
            "aaa_normal_pass": self.aaa_normal_pass,
            "aaa_large_pass": self.aaa_large_pass,
            "ui_component_pass": self.ui_component_pass,
            "highest_grade": self.highest_grade,
            "foreground": self.foreground.to_dict(),
            "background": self.background.to_dict(),
        }


@dataclass
class APCAResult:
    """Advanced Perceptual Contrast Algorithm (APCA-W3 0.98G) evaluation.

    Attributes:
        lc: Lightness Contrast value (range ~0 to +/- 108).
        polarity: Text polarity ('dark-on-light' vs 'light-on-dark' or 'none').
        min_font_size_pt: Dict mapping font weights (100..900) to minimum pt size.
        accessible_use: Recommended text tier / use case.
        rating: Short classification rating string.
    """

    lc: float
    polarity: str
    min_font_size_pt: Dict[int, float]
    accessible_use: str
    rating: str

    @property
    def abs_lc(self) -> float:
        """Absolute Lightness Contrast value."""
        return abs(self.lc)

    def is_accessible_body(self) -> bool:
        """Check if contrast is sufficient for fluent body text (abs(Lc) >= 75)."""
        return self.abs_lc >= 75.0

    def is_accessible_large(self) -> bool:
        """Check if contrast is sufficient for headers/large text (abs(Lc) >= 45)."""
        return self.abs_lc >= 45.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert APCAResult to dictionary."""
        return {
            "lc": round(self.lc, 2),
            "abs_lc": round(self.abs_lc, 2),
            "polarity": self.polarity,
            "min_font_size_pt": self.min_font_size_pt,
            "accessible_use": self.accessible_use,
            "rating": self.rating,
        }


class ColorblindType(str, Enum):
    """Color vision deficiency classifications."""

    PROTANOPIA = "protanopia"        # Red-blind (L-cone absent)
    PROTANOMALY = "protanomaly"      # Red-weak (L-cone shifted)
    DEUTERANOPIA = "deuteranopia"    # Green-blind (M-cone absent)
    DEUTERANOMALY = "deuteranomaly"  # Green-weak (M-cone shifted)
    TRITANOPIA = "tritanopia"        # Blue-blind (S-cone absent)
    TRITANOMALY = "tritanomaly"      # Blue-weak (S-cone shifted)
    ACHROMATOPSIA = "achromatopsia"  # Complete monochromacy (rod monochromacy)
    ACHROMATOMALY = "achromatomaly"  # Partial monochromacy / cone monochromacy


@dataclass
class ColorblindSimulationResult:
    """Simulation of a color pair under a specific color vision deficiency.

    Attributes:
        deficiency: Type of color vision deficiency simulated.
        simulated_fg: Simulated foreground color as perceived.
        simulated_bg: Simulated background color as perceived.
        simulated_ratio: Contrast ratio under simulation.
        is_accessible: Whether simulated contrast meets AA Normal standard (>= 4.5:1).
    """

    deficiency: ColorblindType
    simulated_fg: Color
    simulated_bg: Color
    simulated_ratio: float
    is_accessible: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation result to dictionary."""
        return {
            "deficiency": self.deficiency.value,
            "simulated_fg": self.simulated_fg.to_dict(),
            "simulated_bg": self.simulated_bg.to_dict(),
            "simulated_ratio": round(self.simulated_ratio, 2),
            "is_accessible": self.is_accessible,
        }


@dataclass
class RemediationSuggestion:
    """Color remediation adjustment recommendation to satisfy target contrast.

    Attributes:
        original_color: The color being adjusted.
        suggested_color: Adjusted accessible color.
        target_ratio: Target WCAG contrast ratio required.
        new_ratio: Contrast ratio achieved with suggested color.
        delta_e: Perceptual color difference (CIEDE2000 ΔE).
        direction: Adjustment direction ('lighten', 'darken', 'none').
    """

    original_color: Color
    suggested_color: Color
    target_ratio: float
    new_ratio: float
    delta_e: float
    direction: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert remediation suggestion to dictionary."""
        return {
            "original_color": self.original_color.to_dict(),
            "suggested_color": self.suggested_color.to_dict(),
            "target_ratio": self.target_ratio,
            "new_ratio": round(self.new_ratio, 2),
            "delta_e": round(self.delta_e, 3),
            "direction": self.direction,
        }


@dataclass
class PaletteAuditReport:
    """Comprehensive accessibility audit report for a color palette.

    Attributes:
        palette_name: Identifier or title of the design palette.
        color_count: Number of unique colors in the palette.
        pair_evaluations: List of evaluations for tested color pairs.
        overall_compliance_score: Percentage score [0.0 - 100.0] of compliant pairs.
        failing_pairs_count: Count of pairs failing target threshold.
        recommendations: Actionable list of remediation recommendations.
    """

    palette_name: str
    color_count: int
    pair_evaluations: List[Dict[str, Any]] = field(default_factory=list)
    overall_compliance_score: float = 0.0
    failing_pairs_count: int = 0
    recommendations: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Summary overview of the palette audit."""
        total_pairs = len(self.pair_evaluations)
        return (
            f"Palette: '{self.palette_name}' | Total Colors: {self.color_count} | "
            f"Evaluated Pairs: {total_pairs} | Score: {self.overall_compliance_score:.1f}% | "
            f"Failing Pairs: {self.failing_pairs_count}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit report to dictionary."""
        return {
            "palette_name": self.palette_name,
            "color_count": self.color_count,
            "overall_compliance_score": round(self.overall_compliance_score, 1),
            "failing_pairs_count": self.failing_pairs_count,
            "recommendations": self.recommendations,
            "pair_evaluations": self.pair_evaluations,
        }


@dataclass
class GradientContrastReport:
    """Report on text contrast readability across a CSS gradient background.

    Attributes:
        fg: Evaluated foreground color.
        stops: Evaluated gradient stop colors.
        min_ratio: Minimum contrast ratio across all sampled points (worst case).
        max_ratio: Maximum contrast ratio across sampled points.
        avg_ratio: Mean contrast ratio across all sampled points.
        worst_stop_index: Index of the sampled stop with the lowest contrast.
        aa_normal_pass: True if worst-case min_ratio >= 4.5.
        aa_large_pass: True if worst-case min_ratio >= 3.0.
        aaa_normal_pass: True if worst-case min_ratio >= 7.0.
        sample_ratios: List of contrast ratios at each sampled interval.
    """

    fg: Color
    stops: List[Color]
    min_ratio: float
    max_ratio: float
    avg_ratio: float
    worst_stop_index: int
    aa_normal_pass: bool
    aa_large_pass: bool
    aaa_normal_pass: bool
    sample_ratios: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fg": self.fg.to_dict(),
            "stops": [s.to_dict() for s in self.stops],
            "min_ratio": round(self.min_ratio, 2),
            "max_ratio": round(self.max_ratio, 2),
            "avg_ratio": round(self.avg_ratio, 2),
            "worst_stop_index": self.worst_stop_index,
            "aa_normal_pass": self.aa_normal_pass,
            "aa_large_pass": self.aa_large_pass,
            "aaa_normal_pass": self.aaa_normal_pass,
            "sample_ratios": [round(r, 2) for r in self.sample_ratios],
        }


@dataclass
class TriadHarmonyResult:
    """Accessible tri-color palette solution (Background, Foreground, Accent).

    Attributes:
        background: Solved background color.
        foreground: Solved foreground body text color.
        accent: Solved interactive/accent UI component color.
        fg_bg_ratio: Contrast ratio between foreground and background.
        accent_bg_ratio: Contrast ratio between accent and background.
        accent_fg_ratio: Contrast ratio between accent and foreground.
        is_accessible: True if all accessibility requirements are met.
    """

    background: Color
    foreground: Color
    accent: Color
    fg_bg_ratio: float
    accent_bg_ratio: float
    accent_fg_ratio: float
    is_accessible: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "background": self.background.to_dict(),
            "foreground": self.foreground.to_dict(),
            "accent": self.accent.to_dict(),
            "fg_bg_ratio": round(self.fg_bg_ratio, 2),
            "accent_bg_ratio": round(self.accent_bg_ratio, 2),
            "accent_fg_ratio": round(self.accent_fg_ratio, 2),
            "is_accessible": self.is_accessible,
        }

