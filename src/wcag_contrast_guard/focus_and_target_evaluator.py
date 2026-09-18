"""WCAG 2.2 Focus Appearance & Target Size Evaluator.

Evaluates user interface elements against modern W3C WCAG 2.2 standards:
- SC 2.4.11 Focus Appearance (Minimum - Level AA):
  • Focus indicator contrast against adjacent background >= 3.0:1
  • Focus indicator contrast against unfocused state >= 3.0:1
  • Minimum indicator area >= 2px perimeter around bounding box: 4*(W+H) - 16
- SC 2.4.13 Focus Appearance (Enhanced - Level AAA):
  • Contrast ratio >= 4.5:1 against adjacent colors and unfocused state
  • Minimum indicator area >= 4px perimeter or 8px along shortest side
- SC 2.5.8 Target Size (Minimum - Level AA):
  • Minimum 24x24 CSS px bounding box or adequate offset spacing circle
- SC 2.5.5 Target Size (Enhanced - Level AAA):
  • Minimum 44x44 CSS px bounding box

100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from wcag_contrast_guard.color_math import parse_color
from wcag_contrast_guard.models import Color
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio


@dataclass
class FocusAppearanceSpec:
    """Specification of an interactive element and its focus indicator styling."""
    element_width: float
    element_height: float
    focus_color: Union[str, Color]
    background_color: Union[str, Color]
    unfocused_color: Optional[Union[str, Color]] = None
    indicator_thickness: float = 2.0  # CSS pixels
    style: str = "outline"  # 'outline', 'box-shadow', 'border', 'background-fill'
    offset: float = 0.0  # outline-offset in CSS pixels


@dataclass
class FocusAppearanceResult:
    """Evaluation result for WCAG 2.2 SC 2.4.11 & SC 2.4.13 Focus Appearance."""
    passes_aa: bool
    passes_aaa: bool
    contrast_against_bg: float
    contrast_against_unfocused: float
    indicator_area_px2: float
    min_required_area_aa_px2: float
    min_required_area_aaa_px2: float
    thickness_px: float
    style: str
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passes_aa": self.passes_aa,
            "passes_aaa": self.passes_aaa,
            "contrast_against_bg": round(self.contrast_against_bg, 2),
            "contrast_against_unfocused": round(self.contrast_against_unfocused, 2),
            "indicator_area_px2": round(self.indicator_area_px2, 1),
            "min_required_area_aa_px2": round(self.min_required_area_aa_px2, 1),
            "min_required_area_aaa_px2": round(self.min_required_area_aaa_px2, 1),
            "thickness_px": self.thickness_px,
            "style": self.style,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


@dataclass
class TargetSizeSpec:
    """Specification of an interactive touch or pointer target."""
    width_px: float
    height_px: float
    spacing_x_px: float = 0.0  # edge-to-edge spacing to nearest horizontal target
    spacing_y_px: float = 0.0  # edge-to-edge spacing to nearest vertical target
    is_inline: bool = False
    is_essential: bool = False
    is_user_agent_default: bool = False


@dataclass
class TargetSizeResult:
    """Evaluation result for WCAG 2.2 SC 2.5.8 & SC 2.5.5 Target Size."""
    passes_aa: bool
    passes_aaa: bool
    width_px: float
    height_px: float
    area_px2: float
    min_dimension_px: float
    spacing_adequate_aa: bool
    exemption_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passes_aa": self.passes_aa,
            "passes_aaa": self.passes_aaa,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "area_px2": round(self.area_px2, 1),
            "min_dimension_px": round(self.min_dimension_px, 1),
            "spacing_adequate_aa": self.spacing_adequate_aa,
            "exemption_reason": self.exemption_reason,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


def evaluate_focus_appearance(spec: FocusAppearanceSpec) -> FocusAppearanceResult:
    """Evaluate focus indicator against WCAG 2.2 SC 2.4.11 (AA) and SC 2.4.13 (AAA)."""
    f_color = parse_color(spec.focus_color) if not isinstance(spec.focus_color, Color) else spec.focus_color
    b_color = parse_color(spec.background_color) if not isinstance(spec.background_color, Color) else spec.background_color

    unfocused_c = None
    if spec.unfocused_color:
        unfocused_c = parse_color(spec.unfocused_color) if not isinstance(spec.unfocused_color, Color) else spec.unfocused_color

    w = max(1.0, float(spec.element_width))
    h = max(1.0, float(spec.element_height))
    thickness = max(0.1, float(spec.indicator_thickness))
    style = spec.style.lower()

    # Contrast against adjacent background
    contrast_bg = calculate_contrast_ratio(f_color, b_color)

    # Contrast against unfocused state (if given, else default to bg)
    if unfocused_c:
        contrast_unfocused = calculate_contrast_ratio(f_color, unfocused_c)
    else:
        contrast_unfocused = contrast_bg

    # WCAG 2.2 Perimeter Area Calculations
    # SC 2.4.11 AA requires area >= 2px perimeter around unfocused component:
    # 2 * (w * 2 + h * 2) - 16 = 4*(w+h) - 16 (or shortest side 4*min(w,h))
    min_area_aa = max(0.0, 4.0 * (w + h) - 16.0)
    # SC 2.4.13 AAA requires area >= 4px perimeter:
    min_area_aaa = max(0.0, 8.0 * (w + h) - 64.0)

    # Calculate actual indicator area based on style
    if style == "background-fill":
        actual_area = w * h
    elif style in ("outline", "box-shadow", "border"):
        # Outline / ring area
        outer_w = w + 2.0 * (spec.offset + thickness)
        outer_h = h + 2.0 * (spec.offset + thickness)
        inner_w = w + 2.0 * spec.offset
        inner_h = h + 2.0 * spec.offset
        actual_area = max(0.0, (outer_w * outer_h) - (inner_w * inner_h))
    else:
        actual_area = thickness * 2.0 * (w + h)

    # Check passes
    warnings: List[str] = []
    recommendations: List[str] = []

    # AA Checks:
    # 1. Contrast >= 3.0:1 against adjacent background
    # 2. Contrast >= 3.0:1 against unfocused state
    # 3. Area >= min_area_aa (or thickness >= 2.0px full perimeter)
    has_contrast_aa = (contrast_bg >= 3.0) and (contrast_unfocused >= 3.0)
    has_area_aa = (actual_area >= min_area_aa) or (thickness >= 2.0 and style in ("outline", "box-shadow"))
    passes_aa = has_contrast_aa and has_area_aa

    # AAA Checks:
    # 1. Contrast >= 4.5:1 against adjacent background
    # 2. Contrast >= 4.5:1 against unfocused state
    # 3. Area >= min_area_aaa (or thickness >= 4.0px full perimeter)
    has_contrast_aaa = (contrast_bg >= 4.5) and (contrast_unfocused >= 4.5)
    has_area_aaa = (actual_area >= min_area_aaa) or (thickness >= 4.0 and style in ("outline", "box-shadow"))
    passes_aaa = has_contrast_aaa and has_area_aaa

    if contrast_bg < 3.0:
        warnings.append(
            f"Focus indicator contrast against adjacent background is {contrast_bg:.2f}:1 (< 3.0:1 required for WCAG 2.2 AA)."
        )
        recommendations.append(
            f"Increase focus color contrast against '{b_color.hex}' to at least 3.0:1 (e.g. use high-contrast primary/accent hue)."
        )

    if contrast_unfocused < 3.0:
        warnings.append(
            f"Focus indicator contrast against unfocused state is {contrast_unfocused:.2f}:1 (< 3.0:1 required for WCAG 2.2 AA)."
        )
        recommendations.append(
            "Ensure the focused component color change differs clearly from the resting unfocused state."
        )

    if not has_area_aa:
        warnings.append(
            f"Focus indicator area ({actual_area:.1f}px²) does not meet the minimum 2px perimeter requirement ({min_area_aa:.1f}px²)."
        )
        recommendations.append(
            f"Increase outline/border thickness to at least 2px (current: {thickness}px) to satisfy SC 2.4.11 minimum area."
        )

    if passes_aa and not passes_aaa:
        recommendations.append(
            "To reach Level AAA (SC 2.4.13), increase thickness to >= 4px and contrast ratio to >= 4.5:1."
        )

    return FocusAppearanceResult(
        passes_aa=passes_aa,
        passes_aaa=passes_aaa,
        contrast_against_bg=contrast_bg,
        contrast_against_unfocused=contrast_unfocused,
        indicator_area_px2=actual_area,
        min_required_area_aa_px2=min_area_aa,
        min_required_area_aaa_px2=min_area_aaa,
        thickness_px=thickness,
        style=style,
        warnings=warnings,
        recommendations=recommendations,
    )


def evaluate_target_size(spec: TargetSizeSpec) -> TargetSizeResult:
    """Evaluate interactive pointer target size against WCAG 2.2 SC 2.5.8 (AA) & SC 2.5.5 (AAA)."""
    w = max(0.0, float(spec.width_px))
    h = max(0.0, float(spec.height_px))
    min_dim = min(w, h)
    area = w * h

    warnings: List[str] = []
    recommendations: List[str] = []

    # Handle Exemptions
    if spec.is_inline:
        return TargetSizeResult(
            passes_aa=True,
            passes_aaa=True,
            width_px=w,
            height_px=h,
            area_px2=area,
            min_dimension_px=min_dim,
            spacing_adequate_aa=True,
            exemption_reason="Inline text link exemption (WCAG 2.2 SC 2.5.8 Exception)",
        )

    if spec.is_essential:
        return TargetSizeResult(
            passes_aa=True,
            passes_aaa=True,
            width_px=w,
            height_px=h,
            area_px2=area,
            min_dimension_px=min_dim,
            spacing_adequate_aa=True,
            exemption_reason="Essential presentation exemption (e.g., map control pin)",
        )

    if spec.is_user_agent_default:
        return TargetSizeResult(
            passes_aa=True,
            passes_aaa=True,
            width_px=w,
            height_px=h,
            area_px2=area,
            min_dimension_px=min_dim,
            spacing_adequate_aa=True,
            exemption_reason="User agent default control exemption",
        )

    # SC 2.5.8 (AA): At least 24x24 px, OR spacing offset satisfies:
    # 24px diameter circle centered on target does not intersect another target.
    # If target is undersized, spacing around edge must make up the difference:
    # min_dim + 2 * spacing >= 24
    spacing_adequate = False
    if min_dim >= 24.0:
        passes_aa = True
        spacing_adequate = True
    else:
        # Check spacing circle exception:
        # Distance from edge needed = (24 - min_dim) / 2
        needed_spacing = max(0.0, (24.0 - min_dim) / 2.0)
        actual_min_spacing = min(spec.spacing_x_px, spec.spacing_y_px)
        if actual_min_spacing >= needed_spacing:
            passes_aa = True
            spacing_adequate = True
        else:
            passes_aa = False
            spacing_adequate = False
            warnings.append(
                f"Target size is {w:.0f}x{h:.0f}px (< 24x24px required) and edge spacing ({actual_min_spacing:.1f}px) is insufficient (needs >= {needed_spacing:.1f}px)."
            )
            recommendations.append(
                f"Increase target bounding box to at least 24x24 CSS pixels (e.g. min-width: 24px; min-height: 24px) or add padding/margin of >= {needed_spacing:.1f}px."
            )

    # SC 2.5.5 (AAA): At least 44x44 px
    passes_aaa = (w >= 44.0) and (h >= 44.0)
    if not passes_aaa and passes_aa:
        recommendations.append(
            f"To achieve Level AAA (SC 2.5.5), expand touch target bounding box to at least 44x44 CSS pixels (current: {w:.0f}x{h:.0f}px)."
        )

    return TargetSizeResult(
        passes_aa=passes_aa,
        passes_aaa=passes_aaa,
        width_px=w,
        height_px=h,
        area_px2=area,
        min_dimension_px=min_dim,
        spacing_adequate_aa=spacing_adequate,
        warnings=warnings,
        recommendations=recommendations,
    )
