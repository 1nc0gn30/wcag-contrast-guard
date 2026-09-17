"""wcag-contrast-guard: Universal WCAG 2.2 & APCA Perceptual Color Contrast Engine.

Provides WCAG 2.1/2.2 and APCA perceptual contrast evaluation, 8-deficiency
color vision deficiency simulation, automated CIEDE2000 Delta-E remediation,
design system palette audits, CSS scanner, Model Context Protocol (MCP) server,
and Google Material 3 Studio web application.

Pure Python standard library (zero external runtime dependencies).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Package Metadata
__version__ = "0.1.0"
__author__ = "Google WCAG Studio Engineering Team"
__license__ = "MIT"

# Domain Models
from wcag_contrast_guard.models import (
    APCAResult,
    Color,
    ColorblindSimulationResult,
    ColorblindType,
    GradientContrastReport,
    PaletteAuditReport,
    RemediationSuggestion,
    TriadHarmonyResult,
    ContrastMatrixCell,
    HarmonicPaletteResult,
    WCAGLevel,
    WCAGResult,
)

# Color Math & Parsing
from wcag_contrast_guard.color_math import (
    NAMED_CSS_COLORS,
    blend_alpha,
    color_distance,
    delta_e_76,
    delta_e_ciede2000,
    get_relative_luminance,
    hsl_to_rgb,
    lab_to_rgb,
    lab_to_xyz,
    linear_to_srgb,
    parse_color,
    rgb_to_hsl,
    rgb_to_lab,
    rgb_to_xyz,
    srgb_to_linear,
    xyz_to_lab,
    xyz_to_rgb,
)

# WCAG Evaluation
from wcag_contrast_guard.wcag_engine import (
    calculate_contrast_ratio,
    check_contrast,
    evaluate_gradient_contrast,
    evaluate_wcag,
    get_wcag_levels_passed,
    is_aa_compliant,
    is_aaa_compliant,
    is_ui_component_compliant,
)

# APCA Evaluation
from wcag_contrast_guard.apca_engine import (
    calculate_apca_lc,
    evaluate_apca,
)

# Colorblind Simulation
from wcag_contrast_guard.colorblind_sim import (
    simulate_all_deficiencies,
    simulate_colorblind,
    simulate_pair,
)

# Remediation Engine
from wcag_contrast_guard.remediation import (
    find_best_contrast_match,
    remediate_contrast,
    solve_accessible_triad,
    suggest_accessible_palette,
)

# Harmonic Palette Generator
from wcag_contrast_guard.harmonic_palette import (
    build_contrast_matrix,
    export_palette_css,
    export_palette_design_tokens,
    export_palette_svg,
    export_palette_tailwind,
    generate_harmonic_palette,
)

# Catalog & Palettes
from wcag_contrast_guard.catalog import (
    PALETTES,
    audit_custom_palette,
    audit_palette,
    get_palette,
    get_palette_colors,
    list_palettes,
)

# CSS Scanner
from wcag_contrast_guard.css_scanner import (
    CSSColorPair,
    CSSRule,
    CSSScanResult,
    extract_css_colors,
    resolve_css_variables,
    scan_css_file,
    scan_css_string,
    scan_html_inline_styles,
)

# Cross-platform Compatibility
from wcag_contrast_guard.compat import (
    PlatformInfo,
    atomic_write_bytes,
    atomic_write_text,
    get_platform_info,
    normalize_path,
    read_json_safe,
    read_text_safe,
    safe_delete_dir,
    safe_delete_file,
    write_json_safe,
)

# MCP Server
from wcag_contrast_guard.mcp_server import (
    handle_jsonrpc_request,
    process_request,
    run_stdio_server,
)


# -------------------------------------------------------------------------
# Friendly Public API Wrappers & Aliases
# -------------------------------------------------------------------------

def calculate_apca(
    foreground: Union[str, Color],
    background: Union[str, Color],
) -> APCAResult:
    """Calculate APCA perceptual contrast (Lc) and font requirements.

    Args:
        foreground: Text / foreground color representation.
        background: Background color representation.

    Returns:
        APCAResult: APCA evaluation with Lc value, polarity, and font thresholds.
    """
    return evaluate_apca(foreground, background)


def simulate_colorblindness(
    foreground: Union[str, Color],
    background: Union[str, Color],
    deficiency: Union[str, ColorblindType] = "all",
    severity: float = 1.0,
) -> Union[ColorblindSimulationResult, Dict[ColorblindType, ColorblindSimulationResult]]:
    """Simulate a color pair across color vision deficiencies.

    Args:
        foreground: Foreground color.
        background: Background color.
        deficiency: Deficiency type (e.g. 'protanopia', 'deuteranopia') or 'all' (default).
        severity: Deficiency severity [0.0 to 1.0] (default 1.0).

    Returns:
        ColorblindSimulationResult or Dict mapping all deficiency types to results.
    """
    if isinstance(deficiency, str) and deficiency.lower() == "all":
        return simulate_all_deficiencies(foreground, background, severity=severity)
    return simulate_pair(foreground, background, deficiency=deficiency, severity=severity)


def suggest_remediation(
    foreground: Union[str, Color],
    background: Union[str, Color],
    target_ratio: float = 4.5,
    adjust: str = "foreground",
) -> RemediationSuggestion:
    """Find closest accessible color satisfying target contrast with minimal Delta-E shift.

    Args:
        foreground: Foreground color.
        background: Background color.
        target_ratio: Required WCAG contrast ratio (default 4.5).
        adjust: Which color to adjust ('foreground'/'fg', 'background'/'bg', or 'both').

    Returns:
        RemediationSuggestion: Optimal color recommendation with Delta-E and direction.
    """
    return remediate_contrast(foreground, background, target_ratio=target_ratio, adjust=adjust)


def scan_css_colors(
    css_content_or_path: Union[str, Path],
    default_bg: str = "#ffffff",
) -> CSSScanResult:
    """Extract color declarations and audit contrast pairs from CSS content or file path.

    Args:
        css_content_or_path: Raw CSS stylesheet string or filesystem Path to a .css file.
        default_bg: Fallback background color (default '#ffffff').

    Returns:
        CSSScanResult: Discovered variables, rules, and evaluated color pairs.
    """
    path_obj = Path(str(css_content_or_path))
    if path_obj.is_file():
        return scan_css_file(path_obj, default_bg=default_bg)
    return scan_css_string(str(css_content_or_path), default_bg=default_bg)


__all__ = [
    # Metadata
    "__version__",
    "__author__",
    "__license__",
    # Domain Models & Enums
    "Color",
    "WCAGLevel",
    "WCAGResult",
    "APCAResult",
    "ColorblindType",
    "ColorblindSimulationResult",
    "RemediationSuggestion",
    "PaletteAuditReport",
    "GradientContrastReport",
    "TriadHarmonyResult",
    "ContrastMatrixCell",
    "HarmonicPaletteResult",
    "PlatformInfo",
    "CSSRule",
    "CSSColorPair",
    "CSSScanResult",
    # Core Algorithms & Functions
    "parse_color",
    "get_relative_luminance",
    "calculate_contrast_ratio",
    "evaluate_wcag",
    "evaluate_gradient_contrast",
    "check_contrast",
    "is_aa_compliant",
    "is_aaa_compliant",
    "is_ui_component_compliant",
    "get_wcag_levels_passed",
    "calculate_apca_lc",
    "evaluate_apca",
    "calculate_apca",
    "simulate_colorblind",
    "simulate_pair",
    "simulate_all_deficiencies",
    "simulate_colorblindness",
    "remediate_contrast",
    "suggest_remediation",
    "suggest_accessible_palette",
    "solve_accessible_triad",
    "generate_harmonic_palette",
    "build_contrast_matrix",
    "export_palette_css",
    "export_palette_tailwind",
    "export_palette_design_tokens",
    "export_palette_svg",
    "find_best_contrast_match",
    "color_distance",
    "delta_e_ciede2000",
    "delta_e_76",
    "blend_alpha",
    # Palettes & Catalog
    "PALETTES",
    "list_palettes",
    "get_palette",
    "get_palette_colors",
    "audit_palette",
    "audit_custom_palette",
    # CSS Scanner
    "scan_css_colors",
    "scan_css_string",
    "scan_css_file",
    "scan_html_inline_styles",
    "extract_css_colors",
    "resolve_css_variables",
    # MCP Protocol & Server
    "handle_jsonrpc_request",
    "process_request",
    "run_stdio_server",
]
