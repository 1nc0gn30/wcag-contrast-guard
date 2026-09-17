"""Built-in catalog of 10+ popular design system color palettes and audit utilities.

Includes:
- Google Material 3 (Material You)
- Tailwind CSS 3
- GitHub Primer
- Apple Human Interface Guidelines (HIG)
- Radix Colors
- IBM Carbon
- Dracula Theme
- Solarized (Dark & Light)
- Nord
- One Dark
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from wcag_contrast_guard.color_math import parse_color
from wcag_contrast_guard.models import Color, PaletteAuditReport
from wcag_contrast_guard.remediation import remediate_contrast
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio, evaluate_wcag

# -------------------------------------------------------------------------
# Design System Palettes Dictionary
# -------------------------------------------------------------------------
PALETTES: Dict[str, Dict[str, str]] = {
    "google-material-3": {
        "primary": "#6750A4",
        "on-primary": "#FFFFFF",
        "primary-container": "#EADDFF",
        "on-primary-container": "#21005D",
        "secondary": "#625B71",
        "on-secondary": "#FFFFFF",
        "secondary-container": "#E8DEF8",
        "on-secondary-container": "#1D192B",
        "tertiary": "#7D5260",
        "on-tertiary": "#FFFFFF",
        "tertiary-container": "#FFD8E4",
        "on-tertiary-container": "#31111D",
        "error": "#B3261E",
        "on-error": "#FFFFFF",
        "error-container": "#F9DEDC",
        "on-error-container": "#410E0B",
        "background": "#FFFBFE",
        "on-background": "#1C1B1F",
        "surface": "#FFFBFE",
        "on-surface": "#1C1B1F",
        "surface-variant": "#E7E0EC",
        "on-surface-variant": "#49454F",
        "outline": "#79747E",
        "outline-variant": "#CAC4D0",
        "inverse-surface": "#313033",
        "inverse-on-surface": "#F4EFF4",
        "inverse-primary": "#D0BCFF",
    },
    "tailwind-css-3": {
        "slate-50": "#f8fafc",
        "slate-100": "#f1f5f9",
        "slate-200": "#e2e8f0",
        "slate-300": "#cbd5e1",
        "slate-400": "#94a3b8",
        "slate-500": "#64748b",
        "slate-600": "#475569",
        "slate-700": "#334155",
        "slate-800": "#1e293b",
        "slate-900": "#0f172a",
        "slate-950": "#020617",
        "gray-50": "#f9fafb",
        "gray-500": "#6b7280",
        "gray-900": "#111827",
        "red-50": "#fef2f2",
        "red-500": "#ef4444",
        "red-600": "#dc2626",
        "red-900": "#7f1d1d",
        "blue-50": "#eff6ff",
        "blue-500": "#3b82f6",
        "blue-600": "#2563eb",
        "blue-900": "#1e3a8a",
        "emerald-50": "#ecfdf5",
        "emerald-500": "#10b981",
        "emerald-600": "#059669",
        "emerald-900": "#064e3b",
        "amber-50": "#fffbeb",
        "amber-500": "#f59e0b",
        "amber-600": "#d97706",
        "amber-900": "#78350f",
        "violet-50": "#f5f3ff",
        "violet-500": "#8b5cf6",
        "violet-600": "#7c3aed",
        "violet-900": "#4c1d95",
    },
    "github-primer": {
        "canvas-default": "#ffffff",
        "canvas-subtle": "#f6f8fa",
        "canvas-inset": "#f6f8fa",
        "fg-default": "#1f2328",
        "fg-muted": "#656d76",
        "fg-subtle": "#6e7781",
        "fg-on-emphasis": "#ffffff",
        "accent-fg": "#0969da",
        "accent-emphasis": "#0969da",
        "accent-muted": "#ddf4ff",
        "success-fg": "#1a7f37",
        "success-emphasis": "#1f883d",
        "attention-fg": "#9a6700",
        "attention-emphasis": "#9a6700",
        "danger-fg": "#d1242f",
        "danger-emphasis": "#cf222e",
        "done-fg": "#8250df",
        "done-emphasis": "#8250df",
        "border-default": "#d0d7de",
        "border-muted": "#d8dee4",
    },
    "apple-hig": {
        "system-red": "#ff3b30",
        "system-orange": "#ff9500",
        "system-yellow": "#ffcc00",
        "system-green": "#34c759",
        "system-mint": "#00c7be",
        "system-teal": "#30b0c7",
        "system-cyan": "#32ade6",
        "system-blue": "#007aff",
        "system-indigo": "#5856d6",
        "system-purple": "#af52de",
        "system-pink": "#ff2d55",
        "system-brown": "#a2845e",
        "system-gray": "#8e8e93",
        "system-gray2": "#aeaeb2",
        "system-gray3": "#c7c7cc",
        "system-gray4": "#d1d1d6",
        "system-gray5": "#e5e5ea",
        "system-gray6": "#f2f2f7",
        "label": "#000000",
        "secondary-label": "#3c3c43",
        "system-background": "#ffffff",
        "secondary-system-background": "#f2f2f7",
    },
    "radix-colors": {
        "slate-1": "#fbfcfd",
        "slate-2": "#f7f9fa",
        "slate-3": "#edf0f2",
        "slate-6": "#ced2d6",
        "slate-9": "#889096",
        "slate-11": "#60646c",
        "slate-12": "#11181c",
        "blue-1": "#fbfdff",
        "blue-2": "#f5faff",
        "blue-3": "#e6f4fe",
        "blue-9": "#0090ff",
        "blue-11": "#006adc",
        "blue-12": "#00254d",
        "green-1": "#fbfeef",
        "green-3": "#e6fbe8",
        "green-9": "#30a46c",
        "green-11": "#18794e",
        "green-12": "#153226",
        "red-1": "#fffcfc",
        "red-3": "#ffedea",
        "red-9": "#e5484d",
        "red-11": "#cd2b31",
        "red-12": "#381316",
        "amber-1": "#fefdfb",
        "amber-3": "#fff7c2",
        "amber-9": "#ffc53d",
        "amber-11": "#ad5700",
        "amber-12": "#4e2009",
    },
    "ibm-carbon": {
        "white": "#ffffff",
        "gray-10": "#f4f4f4",
        "gray-20": "#e0e0e0",
        "gray-30": "#c6c6c6",
        "gray-40": "#a8a8a8",
        "gray-50": "#8d8d8d",
        "gray-60": "#6f6f6f",
        "gray-70": "#525252",
        "gray-80": "#393939",
        "gray-90": "#262626",
        "gray-100": "#161616",
        "blue-60": "#0f62fe",
        "blue-70": "#0043ce",
        "blue-80": "#002d9c",
        "text-primary-light": "#161616",
        "text-secondary-light": "#525252",
        "text-primary-dark": "#f4f4f4",
        "text-secondary-dark": "#c6c6c6",
        "background-light": "#ffffff",
        "background-dark": "#161616",
    },
    "dracula": {
        "background": "#282a36",
        "current-line": "#44475a",
        "selection": "#44475a",
        "foreground": "#f8f8f2",
        "comment": "#6272a4",
        "cyan": "#8be9fd",
        "green": "#50fa7b",
        "orange": "#ffb86c",
        "pink": "#ff79c6",
        "purple": "#bd93f9",
        "red": "#ff5555",
        "yellow": "#f1fa8c",
    },
    "solarized": {
        "base03": "#002b36",
        "base02": "#073642",
        "base01": "#586e75",
        "base00": "#657b83",
        "base0": "#839496",
        "base1": "#93a1a1",
        "base2": "#eee8d5",
        "base3": "#fdf6e3",
        "yellow": "#b58900",
        "orange": "#cb4b16",
        "red": "#dc322f",
        "magenta": "#d33682",
        "violet": "#6c71c4",
        "blue": "#268bd2",
        "cyan": "#2aa198",
        "green": "#859900",
    },
    "nord": {
        "nord0": "#2e3440",
        "nord1": "#3b4252",
        "nord2": "#434c5e",
        "nord3": "#4c566a",
        "nord4": "#d8dee9",
        "nord5": "#e5e9f0",
        "nord6": "#eceff4",
        "nord7": "#8fbcbb",
        "nord8": "#88c0d0",
        "nord9": "#81a1c1",
        "nord10": "#5e81ac",
        "nord11": "#bf616a",
        "nord12": "#d08770",
        "nord13": "#ebcb8b",
        "nord14": "#a3be8c",
        "nord15": "#b48ead",
    },
    "one-dark": {
        "background": "#282c34",
        "foreground": "#abb2bf",
        "red": "#e06c75",
        "green": "#98c379",
        "yellow": "#e5c07b",
        "blue": "#61afef",
        "purple": "#c678dd",
        "cyan": "#56b6c2",
        "comment": "#5c6370",
        "selection": "#3e4451",
        "gutter": "#4b5263",
    },
}

# Aliases for flexible lookup
_PALETTE_ALIASES: Dict[str, str] = {
    "material": "google-material-3",
    "material3": "google-material-3",
    "material-3": "google-material-3",
    "google-material": "google-material-3",
    "tailwind": "tailwind-css-3",
    "tailwind3": "tailwind-css-3",
    "tailwindcss": "tailwind-css-3",
    "primer": "github-primer",
    "github": "github-primer",
    "apple": "apple-hig",
    "hig": "apple-hig",
    "radix": "radix-colors",
    "radix-ui": "radix-colors",
    "carbon": "ibm-carbon",
    "ibm": "ibm-carbon",
    "dracula-theme": "dracula",
    "solarized-dark": "solarized",
    "solarized-light": "solarized",
    "onedark": "one-dark",
    "atom-one-dark": "one-dark",
}

# Standard semantic pair configurations per palette for auditing
_PALETTE_DEFAULT_PAIRS: Dict[str, List[Tuple[str, str]]] = {
    "google-material-3": [
        ("on-primary", "primary"),
        ("on-primary-container", "primary-container"),
        ("on-secondary", "secondary"),
        ("on-secondary-container", "secondary-container"),
        ("on-tertiary", "tertiary"),
        ("on-tertiary-container", "tertiary-container"),
        ("on-error", "error"),
        ("on-error-container", "error-container"),
        ("on-background", "background"),
        ("on-surface", "surface"),
        ("on-surface-variant", "surface-variant"),
        ("inverse-on-surface", "inverse-surface"),
        ("primary", "background"),
        ("outline", "surface"),
    ],
    "github-primer": [
        ("fg-default", "canvas-default"),
        ("fg-muted", "canvas-default"),
        ("fg-subtle", "canvas-default"),
        ("fg-on-emphasis", "accent-emphasis"),
        ("accent-fg", "canvas-default"),
        ("success-fg", "canvas-default"),
        ("danger-fg", "canvas-default"),
        ("attention-fg", "canvas-default"),
        ("done-fg", "canvas-default"),
        ("fg-default", "canvas-subtle"),
        ("border-default", "canvas-default"),
    ],
    "dracula": [
        ("foreground", "background"),
        ("comment", "background"),
        ("cyan", "background"),
        ("green", "background"),
        ("orange", "background"),
        ("pink", "background"),
        ("purple", "background"),
        ("red", "background"),
        ("yellow", "background"),
    ],
    "solarized": [
        ("base0", "base03"),
        ("base1", "base03"),
        ("yellow", "base03"),
        ("orange", "base03"),
        ("blue", "base03"),
        ("cyan", "base03"),
        ("green", "base03"),
        ("base00", "base3"),
        ("base01", "base3"),
        ("blue", "base3"),
        ("magenta", "base3"),
    ],
    "nord": [
        ("nord4", "nord0"),
        ("nord5", "nord0"),
        ("nord6", "nord0"),
        ("nord8", "nord0"),
        ("nord9", "nord0"),
        ("nord7", "nord0"),
        ("nord12", "nord0"),
        ("nord13", "nord0"),
        ("nord14", "nord0"),
    ],
    "one-dark": [
        ("foreground", "background"),
        ("red", "background"),
        ("green", "background"),
        ("yellow", "background"),
        ("blue", "background"),
        ("purple", "background"),
        ("cyan", "background"),
        ("comment", "background"),
    ],
}


def _resolve_palette_key(name: str) -> str:
    """Normalize palette identifier."""
    key = name.strip().lower().replace(" ", "-").replace("_", "-")
    if key in PALETTES:
        return key
    if key in _PALETTE_ALIASES:
        return _PALETTE_ALIASES[key]
    raise KeyError(f"Palette '{name}' not found. Available palettes: {list_palettes()}")


def list_palettes() -> List[str]:
    """List names of all supported design system palettes.

    Returns:
        List[str]: Palette identifiers.
    """
    return sorted(list(PALETTES.keys()))


def get_palette(name: str) -> Dict[str, str]:
    """Retrieve color dictionary mapping names to hex strings for a palette.

    Args:
        name: Name of palette (e.g. 'google-material-3', 'tailwind', 'dracula').

    Returns:
        Dict[str, str]: Color names mapped to hex colors.
    """
    key = _resolve_palette_key(name)
    return dict(PALETTES[key])


def get_palette_colors(name: str) -> Dict[str, Color]:
    """Retrieve color dictionary with parsed Color model objects.

    Args:
        name: Name of palette.

    Returns:
        Dict[str, Color]: Color names mapped to parsed Color instances.
    """
    pal = get_palette(name)
    return {k: parse_color(v) for k, v in pal.items()}


def audit_custom_palette(
    palette_name: str,
    colors: Dict[str, str],
    pairs: Optional[List[Tuple[str, str]]] = None,
    min_ratio: float = 4.5,
) -> PaletteAuditReport:
    """Run an accessibility and contrast compliance audit on any custom color palette.

    Args:
        palette_name: Title of the palette.
        colors: Dict mapping color keys to hex/color strings.
        pairs: Optional list of (fg_key, bg_key) tuples to evaluate. If omitted,
               tests all sensible foreground against dark/light background combinations.
        min_ratio: Minimum passing contrast ratio threshold (default 4.5 for AA).

    Returns:
        PaletteAuditReport: Full audit breakdown with scores, failing pairs, and remediation suggestions.
    """
    parsed_colors = {k: parse_color(v) for k, v in colors.items()}

    # If pairs not explicitly provided, build default evaluation set
    eval_pairs: List[Tuple[str, str]] = []
    if pairs:
        eval_pairs = pairs
    else:
        # Find light/dark background candidates
        keys = list(colors.keys())
        bg_candidates = [k for k in keys if "bg" in k.lower() or "background" in k.lower() or "canvas" in k.lower() or "surface" in k.lower()]
        if not bg_candidates:
            bg_candidates = [keys[0]]

        for fg_k in keys:
            for bg_k in bg_candidates:
                if fg_k != bg_k:
                    eval_pairs.append((fg_k, bg_k))

    pair_evals: List[Dict[str, Any]] = []
    failing_count = 0
    recommendations: List[str] = []

    for fg_key, bg_key in eval_pairs:
        if fg_key not in parsed_colors or bg_key not in parsed_colors:
            continue

        fg_col = parsed_colors[fg_key]
        bg_col = parsed_colors[bg_key]

        wcag_res = evaluate_wcag(fg_col, bg_col)
        passes = wcag_res.ratio >= min_ratio

        if not passes:
            failing_count += 1
            # Generate remediation suggestion
            sugg = remediate_contrast(fg_col, bg_col, target_ratio=min_ratio, adjust="foreground")
            rec = (
                f"Pair '{fg_key}' on '{bg_key}' has contrast {wcag_res.ratio_str} (fails {min_ratio}:1). "
                f"Suggested '{fg_key}': {sugg.suggested_color.hex} (ΔE00: {sugg.delta_e:.2f}, {sugg.direction}ed, new ratio: {sugg.new_ratio:.2f}:1)"
            )
            recommendations.append(rec)

        pair_evals.append({
            "fg_name": fg_key,
            "bg_name": bg_key,
            "fg_hex": fg_col.hex,
            "bg_hex": bg_col.hex,
            "ratio": wcag_res.ratio,
            "ratio_str": wcag_res.ratio_str,
            "passes_target": passes,
            "aa_normal_pass": wcag_res.aa_normal_pass,
            "aa_large_pass": wcag_res.aa_large_pass,
            "aaa_normal_pass": wcag_res.aaa_normal_pass,
            "ui_component_pass": wcag_res.ui_component_pass,
        })

    total_evaluated = len(pair_evals)
    score = ((total_evaluated - failing_count) / total_evaluated * 100.0) if total_evaluated > 0 else 100.0

    return PaletteAuditReport(
        palette_name=palette_name,
        color_count=len(colors),
        pair_evaluations=pair_evals,
        overall_compliance_score=round(score, 1),
        failing_pairs_count=failing_count,
        recommendations=recommendations,
    )


def audit_palette(
    name: str,
    min_ratio: float = 4.5,
) -> PaletteAuditReport:
    """Audit one of the built-in design system palettes.

    Args:
        name: Name or alias of the palette.
        min_ratio: Minimum ratio threshold (default 4.5).

    Returns:
        PaletteAuditReport: Audit report.
    """
    key = _resolve_palette_key(name)
    colors = get_palette(key)
    pairs = _PALETTE_DEFAULT_PAIRS.get(key)
    return audit_custom_palette(
        palette_name=key,
        colors=colors,
        pairs=pairs,
        min_ratio=min_ratio,
    )
