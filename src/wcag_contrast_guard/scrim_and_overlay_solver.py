"""Text-Over-Image Scrim & Multi-Layer Alpha Blending Contrast Solver.

Provides mathematical optimization for ensuring WCAG contrast when rendering text
over images, gradients, video backdrops, or stacked translucent layers:
- Multi-layer Porter-Duff alpha compositing engine.
- Worst-case vs best-case contrast analysis across dynamic brightness ranges.
- Bisection solver for minimum scrim opacity alpha ensuring WCAG AA (4.5:1) or AAA (7.0:1).
- Generates copy-paste CSS snippets (solid rgba, linear gradient scrim, frosted glass).

100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from wcag_contrast_guard.color_math import blend_alpha, parse_color
from wcag_contrast_guard.models import Color
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio, evaluate_wcag


@dataclass
class ScrimSolution:
    """Calculated optimal scrim/overlay parameters for text over variable backgrounds."""
    text_color: str
    target_contrast: float
    scrim_base_color: str
    min_opacity: float  # [0.0, 1.0]
    effective_scrim_rgba: str
    worst_case_contrast_before: float
    worst_case_contrast_after: float
    is_compliant: bool
    css_solid: str
    css_gradient: str
    css_frosted_glass: str
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_color": self.text_color,
            "target_contrast": round(self.target_contrast, 2),
            "scrim_base_color": self.scrim_base_color,
            "min_opacity": round(self.min_opacity, 3),
            "effective_scrim_rgba": self.effective_scrim_rgba,
            "worst_case_contrast_before": round(self.worst_case_contrast_before, 2),
            "worst_case_contrast_after": round(self.worst_case_contrast_after, 2),
            "is_compliant": self.is_compliant,
            "css_solid": self.css_solid,
            "css_gradient": self.css_gradient,
            "css_frosted_glass": self.css_frosted_glass,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
        }


@dataclass
class ImageTextAuditResult:
    """Audit result for text placed over an image or variable background."""
    text_color: str
    is_safe_without_scrim: bool
    contrast_against_black: float
    contrast_against_white: float
    contrast_against_midgray: float
    worst_case_contrast: float
    best_case_contrast: float
    recommended_scrim_mode: str  # 'dark_scrim', 'light_scrim'
    suggested_scrim: Optional[ScrimSolution] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "text_color": self.text_color,
            "is_safe_without_scrim": self.is_safe_without_scrim,
            "contrast_against_black": round(self.contrast_against_black, 2),
            "contrast_against_white": round(self.contrast_against_white, 2),
            "contrast_against_midgray": round(self.contrast_against_midgray, 2),
            "worst_case_contrast": round(self.worst_case_contrast, 2),
            "best_case_contrast": round(self.best_case_contrast, 2),
            "recommended_scrim_mode": self.recommended_scrim_mode,
        }
        if self.suggested_scrim:
            res["suggested_scrim"] = self.suggested_scrim.to_dict()
        return res


def composite_color_stack(layers: Sequence[Union[str, Color]]) -> Color:
    """Composite an ordered sequence of color layers (bottom-to-top) using Porter-Duff source over.

    Args:
        layers: Sequence of colors from bottom background (index 0) to top layer.

    Returns:
        Color: Fully blended composite color.
    """
    if not layers:
        return Color(r=255, g=255, b=255, a=1.0)

    bottom = parse_color(layers[0]) if not isinstance(layers[0], Color) else layers[0]
    accum = bottom

    for top in layers[1:]:
        top_c = parse_color(top) if not isinstance(top, Color) else top
        accum = blend_alpha(foreground=top_c, background=accum)

    return accum


def audit_text_over_image(
    text_color: Union[str, Color],
    target_contrast: float = 4.5,
    sample_backgrounds: Optional[Sequence[Union[str, Color]]] = None,
) -> ImageTextAuditResult:
    """Audit text readability over an unpredictable image or variable background."""
    txt = parse_color(text_color) if not isinstance(text_color, Color) else text_color

    black = Color(r=0, g=0, b=0, a=1.0)
    white = Color(r=255, g=255, b=255, a=1.0)
    midgray = Color(r=128, g=128, b=128, a=1.0)

    cr_black = calculate_contrast_ratio(txt, black)
    cr_white = calculate_contrast_ratio(txt, white)
    cr_midgray = calculate_contrast_ratio(txt, midgray)

    all_contrasts = [cr_black, cr_white, cr_midgray]

    if sample_backgrounds:
        for bg in sample_backgrounds:
            bg_c = parse_color(bg) if not isinstance(bg, Color) else bg
            all_contrasts.append(calculate_contrast_ratio(txt, bg_c))

    worst_case = min(all_contrasts)
    best_case = max(all_contrasts)
    is_safe = worst_case >= target_contrast

    # Determine recommended scrim type
    # If text is light (closer to white), a dark scrim is optimal.
    # If text is dark (closer to black), a light scrim is optimal.
    if txt.luminance >= 0.18:
        mode = "dark_scrim"
        scrim_base = "#000000"
    else:
        mode = "light_scrim"
        scrim_base = "#ffffff"

    scrim_sol = solve_scrim(
        text_color=txt,
        target_contrast=target_contrast,
        scrim_base_color=scrim_base,
    )

    return ImageTextAuditResult(
        text_color=txt.hex,
        is_safe_without_scrim=is_safe,
        contrast_against_black=cr_black,
        contrast_against_white=cr_white,
        contrast_against_midgray=cr_midgray,
        worst_case_contrast=worst_case,
        best_case_contrast=best_case,
        recommended_scrim_mode=mode,
        suggested_scrim=scrim_sol,
    )


def solve_scrim(
    text_color: Union[str, Color],
    target_contrast: float = 4.5,
    scrim_base_color: Optional[Union[str, Color]] = None,
    allow_invert: bool = True,
) -> ScrimSolution:
    """Solve for the minimum scrim opacity that guarantees target contrast over all backgrounds.

    Uses binary search bisection over [0.0, 1.0] alpha with Porter-Duff compositing.

    Args:
        text_color: Text color to protect.
        target_contrast: Minimum required WCAG contrast ratio (4.5 for AA, 7.0 for AAA).
        scrim_base_color: Optional explicit scrim color (#000000, #ffffff, or custom theme tint).
        allow_invert: If True and chosen scrim cannot solve contrast, tests inverted scrim.

    Returns:
        ScrimSolution: Contains min_opacity, generated CSS code, and contrast metrics.
    """
    txt = parse_color(text_color) if not isinstance(text_color, Color) else text_color

    # Determine best default scrim base color
    if scrim_base_color is not None:
        base_c = parse_color(scrim_base_color) if not isinstance(scrim_base_color, Color) else scrim_base_color
    else:
        base_c = Color(r=0, g=0, b=0, a=1.0) if txt.luminance >= 0.18 else Color(r=255, g=255, b=255, a=1.0)

    # Worst-case background for this scrim:
    # For a dark scrim (e.g. #000000), the worst-case backdrop is pure white (#ffffff).
    # For a light scrim (e.g. #ffffff), the worst-case backdrop is pure black (#000000).
    worst_bg = Color(r=255, g=255, b=255, a=1.0) if base_c.luminance < 0.5 else Color(r=0, g=0, b=0, a=1.0)

    cr_before = calculate_contrast_ratio(txt, worst_bg)

    # If already compliant without scrim
    if cr_before >= target_contrast:
        rgba_str = f"rgba({base_c.r}, {base_c.g}, {base_c.b}, 0.0)"
        return ScrimSolution(
            text_color=txt.hex,
            target_contrast=target_contrast,
            scrim_base_color=base_c.hex,
            min_opacity=0.0,
            effective_scrim_rgba=rgba_str,
            worst_case_contrast_before=cr_before,
            worst_case_contrast_after=cr_before,
            is_compliant=True,
            css_solid=f"/* No scrim needed: contrast is already {cr_before:.2f}:1 */",
            css_gradient=f"/* No scrim needed */",
            css_frosted_glass=f"/* No scrim needed */",
        )

    # Binary search for min alpha in [0.0, 1.0]
    low = 0.0
    high = 1.0
    best_alpha = 1.0
    achieved_contrast = 1.0

    for _ in range(24):
        mid = (low + high) / 2.0
        scrim_layer = Color(r=base_c.r, g=base_c.g, b=base_c.b, a=mid)
        blended = blend_alpha(foreground=scrim_layer, background=worst_bg)
        cr = calculate_contrast_ratio(txt, blended)

        if cr >= target_contrast:
            best_alpha = mid
            achieved_contrast = cr
            high = mid  # try smaller opacity
        else:
            low = mid

    # Verify if 1.0 achieves compliance
    max_scrim = Color(r=base_c.r, g=base_c.g, b=base_c.b, a=1.0)
    max_blended = blend_alpha(foreground=max_scrim, background=worst_bg)
    max_cr = calculate_contrast_ratio(txt, max_blended)

    warnings: List[str] = []
    recommendations: List[str] = []
    is_compliant = (achieved_contrast >= target_contrast)

    if not is_compliant and max_cr < target_contrast:
        if allow_invert:
            # Swap scrim color (dark to light or vice-versa)
            alt_base = Color(r=255, g=255, b=255, a=1.0) if base_c.luminance < 0.5 else Color(r=0, g=0, b=0, a=1.0)
            return solve_scrim(
                text_color=txt,
                target_contrast=target_contrast,
                scrim_base_color=alt_base,
                allow_invert=False,
            )
        warnings.append(
            f"Even at 100% opacity, scrim base '{base_c.hex}' only reaches {max_cr:.2f}:1 (< {target_contrast}:1 target)."
        )
        recommendations.append("Consider adjusting the text color itself to have higher intrinsic contrast.")

    # Round opacity up slightly to avoid edge-rounding sub-pixel failures
    safe_alpha = min(1.0, math.ceil(best_alpha * 100.0) / 100.0)
    final_scrim = Color(r=base_c.r, g=base_c.g, b=base_c.b, a=safe_alpha)
    final_blended = blend_alpha(foreground=final_scrim, background=worst_bg)
    final_cr = calculate_contrast_ratio(txt, final_blended)

    rgba_str = f"rgba({base_c.r}, {base_c.g}, {base_c.b}, {safe_alpha:.2f})"

    # CSS Snippets
    css_solid = f"background-color: {rgba_str};"
    css_gradient = (
        f"background: linear-gradient(180deg, rgba({base_c.r}, {base_c.g}, {base_c.b}, 0) 0%, "
        f"{rgba_str} 100%);"
    )
    css_frosted = (
        f"background: {rgba_str};\n"
        f"-webkit-backdrop-filter: blur(12px);\n"
        f"backdrop-filter: blur(12px);"
    )

    return ScrimSolution(
        text_color=txt.hex,
        target_contrast=target_contrast,
        scrim_base_color=base_c.hex,
        min_opacity=safe_alpha,
        effective_scrim_rgba=rgba_str,
        worst_case_contrast_before=cr_before,
        worst_case_contrast_after=final_cr,
        is_compliant=(final_cr >= target_contrast),
        css_solid=css_solid,
        css_gradient=css_gradient,
        css_frosted_glass=css_frosted,
        warnings=warnings,
        recommendations=recommendations,
    )
