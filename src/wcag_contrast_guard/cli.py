"""Command Line Interface for WCAG Contrast Guard.

Provides subcommands for WCAG & APCA checking, colorblindness simulation,
CIEDE2000 remediation, palette auditing, CSS scanning, MCP stdio server,
and launching the Google Material 3 Studio web application.
100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from wcag_contrast_guard import (
    __author__,
    __license__,
    __version__,
    audit_custom_palette,
    audit_palette,
    calculate_apca,
    calculate_contrast_ratio,
    evaluate_apca,
    evaluate_wcag,
    get_palette,
    get_platform_info,
    list_palettes,
    parse_color,
    read_text_safe,
    remediate_contrast,
    run_stdio_server,
    scan_css_string,
    simulate_all_deficiencies,
    simulate_colorblindness,
)
from wcag_contrast_guard.models import Color, ColorblindType
from wcag_contrast_guard.ui_server import start_server


# ANSI Colors
class AnsiColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"


def _supports_color(no_color_flag: bool = False) -> bool:
    if no_color_flag:
        return False
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def colorize(text: str, color: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{color}{text}{AnsiColor.RESET}"


def cmd_check(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        res = evaluate_wcag(args.foreground, args.background)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
        return 0

    ratio_str = colorize(f"{res.ratio:.2f}:1", AnsiColor.BOLD + (AnsiColor.GREEN if res.aa_normal_pass else AnsiColor.RED), color_ok)
    aa_norm = colorize("PASS", AnsiColor.GREEN, color_ok) if res.aa_normal_pass else colorize("FAIL", AnsiColor.RED, color_ok)
    aa_large = colorize("PASS", AnsiColor.GREEN, color_ok) if res.aa_large_pass else colorize("FAIL", AnsiColor.RED, color_ok)
    aaa_norm = colorize("PASS", AnsiColor.GREEN, color_ok) if res.aaa_normal_pass else colorize("FAIL", AnsiColor.RED, color_ok)
    aaa_large = colorize("PASS", AnsiColor.GREEN, color_ok) if res.aaa_large_pass else colorize("FAIL", AnsiColor.RED, color_ok)

    print(f"\n● WCAG 2.1/2.2 Contrast Evaluation")
    print(f"  Foreground: {res.foreground.hex} (L: {res.foreground.luminance:.4f})")
    print(f"  Background: {res.background.hex} (L: {res.background.luminance:.4f})")
    print(f"  Ratio:      {ratio_str}")
    print(f"  WCAG AA:    Normal Text {aa_norm} (>=4.5) | Large Text {aa_large} (>=3.0)")
    print(f"  WCAG AAA:   Normal Text {aaa_norm} (>=7.0) | Large Text {aaa_large} (>=4.5)")
    print(f"  Summary:    {res.summary()}\n")
    return 0


def cmd_apca(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        res = evaluate_apca(args.foreground, args.background)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
        return 0

    lc_color = AnsiColor.GREEN if res.abs_lc >= 60 else (AnsiColor.YELLOW if res.abs_lc >= 45 else AnsiColor.RED)
    lc_str = colorize(f"{res.lc:+.1f} Lc", AnsiColor.BOLD + lc_color, color_ok)

    print(f"\n● APCA (Advanced Perceptual Contrast Algorithm 0.98G)")
    print(f"  Foreground:       {args.foreground}")
    print(f"  Background:       {args.background}")
    print(f"  Lightness Lc:     {lc_str} (Polarity: {res.polarity})")
    print(f"  Recommended Use:  {res.accessible_use}")
    print(f"  Rating:           {res.rating}")
    print(f"  Min Font (pt):    {res.min_font_size_pt}\n")
    return 0


def cmd_simulate(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        sims = simulate_all_deficiencies(args.foreground, args.background)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps({k.value: v.to_dict() for k, v in sims.items()}, indent=2))
        return 0

    print(f"\n● 8-Deficiency Colorblindness Perception Matrix")
    for dtype, sim in sims.items():
        status = colorize("PASS", AnsiColor.GREEN, color_ok) if sim.is_accessible else colorize("FAIL", AnsiColor.RED, color_ok)
        print(f"  {dtype.value:<16}: {sim.simulated_fg.hex} on {sim.simulated_bg.hex} -> {sim.simulated_ratio:.2f}:1 [{status}]")
    print()
    return 0


def cmd_suggest(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        target = float(args.target_ratio)
        res = remediate_contrast(args.foreground, args.background, target_ratio=target, adjust=args.adjust)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps(res.to_dict(), indent=2))
        return 0

    print(f"\n● CIEDE2000 Minimal Shift Remediation")
    print(f"  Adjusted:        {args.adjust.capitalize()} ({res.original_color.hex})")
    print(f"  Suggested Color: {colorize(res.suggested_color.hex, AnsiColor.BOLD + AnsiColor.CYAN, color_ok)}")
    print(f"  Direction:       {res.direction}")
    print(f"  Target Ratio:    {res.target_ratio:.1f}:1")
    print(f"  New Ratio:       {res.new_ratio:.2f}:1")
    print(f"  ΔE (CIEDE2000):  {res.delta_e:.2f}\n")
    return 0


def cmd_scan(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        p = Path(args.css_file).resolve()
        content = read_text_safe(p) if p.exists() else args.css_file
        report = scan_css_string(content)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error scanning CSS: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"\n● CSS Stylesheet Contrast Scan")
    print(f"  Pairs Evaluated: {report.pairs_count}")
    print(f"  Failing Pairs:   {colorize(str(report.failing_pairs_count), AnsiColor.RED if report.failing_pairs_count > 0 else AnsiColor.GREEN, color_ok)}")
    for f in report.failing_pairs[:10]:
        print(f"  • Selector: {f.get('selector', 'unknown')} | fg: {f.get('foreground')} bg: {f.get('background')} ratio: {f.get('ratio')}")
    if report.failing_pairs_count > 10:
        print(f"  ... and {report.failing_pairs_count - 10} more failing pairs.")
    print()
    return 0


def cmd_palettes(args: argparse.Namespace, color_ok: bool) -> int:
    pals = list_palettes()
    if args.json:
        print(json.dumps(pals, indent=2))
        return 0

    print(f"\n● Built-in Design System Palettes ({len(pals)} available)")
    for p in pals:
        print(f"  • {colorize(p['id'], AnsiColor.BOLD + AnsiColor.CYAN, color_ok):<28} {p.get('name', '')} ({p.get('color_count', 0)} colors)")
    print()
    return 0


def cmd_audit(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        rep = audit_palette(args.palette)
    except Exception as exc:
        sys.stderr.write(colorize(f"Error auditing palette: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if args.json:
        print(json.dumps(rep.to_dict(), indent=2))
        return 0

    score_color = AnsiColor.GREEN if rep.overall_compliance_score >= 80 else (AnsiColor.YELLOW if rep.overall_compliance_score >= 50 else AnsiColor.RED)
    score_str = colorize(f"{rep.overall_compliance_score:.1f}%", AnsiColor.BOLD + score_color, color_ok)

    print(f"\n● Palette Accessibility Audit: '{rep.palette_name}'")
    print(f"  Total Colors:       {rep.color_count}")
    print(f"  Evaluated Pairs:    {len(rep.pair_evaluations)}")
    print(f"  Compliance Score:   {score_str}")
    print(f"  Failing Pairs:      {rep.failing_pairs_count}\n")
    return 0


def cmd_harmonic(args: argparse.Namespace, color_ok: bool) -> int:
    try:
        from .harmonic_palette import generate_harmonic_palette
        seed = getattr(args, "seed", None) or "#1a73e8"
        res = generate_harmonic_palette(
            seed_color=seed,
            harmony_type=getattr(args, "harmony", "analogous"),
            mode=getattr(args, "mode", "light"),
            count=getattr(args, "count", None),
            guarantee_wcag_aa=not getattr(args, "no_guarantee", False),
        )
    except Exception as exc:
        sys.stderr.write(colorize(f"Error generating harmonic palette: {exc}\n", AnsiColor.RED, color_ok))
        return 1

    if getattr(args, "json", False):
        print(json.dumps(res.to_dict(), indent=2))
        return 0

    if getattr(args, "css", False):
        print(res.css_variables)
        return 0

    if getattr(args, "svg", None):
        from .compat import atomic_write_text
        atomic_write_text(args.svg, res.svg_palette)
        print(f"Saved SVG swatch sheet to: {args.svg}")
        return 0

    print(f"\n● Accessible Harmonic Palette Matrix")
    print(f"  Seed Color:      {colorize(res.seed_color.hex, AnsiColor.BOLD + AnsiColor.CYAN, color_ok)}")
    print(f"  Harmony Type:    {res.harmony_type.title()}")
    print(f"  Mode:            {res.mode.title()}")
    print(f"  Total Colors:    {len(res.colors)}")
    print(f"  Matrix Cells:    {res.total_matrix_cells} ({res.compliant_aa_cells} AA compliant)")
    print(f"  Guaranteed AA:   {'YES' if res.guaranteed_compliant else 'NO'}\n")
    print("  Color Roles:")
    for role, col in res.colors.items():
        print(f"    • {role:16s} : {col.hex.upper()} (lum: {col.luminance:.4f})")
    print()
    return 0


def cmd_serve(args: argparse.Namespace, color_ok: bool) -> int:
    port = getattr(args, "port", 8080)
    print(colorize(f"Starting Google WCAG Studio Web UI on port {port}...", AnsiColor.CYAN, color_ok))
    start_server(port=port, open_browser=not getattr(args, "no_browser", False), block=True)
    return 0


def cmd_mcp(args: argparse.Namespace, color_ok: bool) -> int:
    run_stdio_server()
    return 0


def cmd_diagnostics(args: argparse.Namespace, color_ok: bool) -> int:
    pinfo = get_platform_info()
    diag = {
        "wcag_contrast_guard": {
            "version": __version__,
            "author": __author__,
            "license": __license__,
            "mcp_protocol_version": "2024-11-05",
        },
        "python_environment": {
            "python_version": pinfo.python_version,
            "executable": sys.executable,
            "platform": sys.platform,
        },
        "operating_system": {
            "os_name": pinfo.system,
            "architecture": platform.machine(),
            "is_windows": pinfo.is_windows,
            "is_macos": pinfo.is_macos,
            "is_linux": pinfo.is_linux,
        },
    }

    if args.json:
        print(json.dumps(diag, indent=2))
        return 0

    print(f"\n● WCAG Contrast Guard Diagnostics")
    print(f"  Version:   v{__version__} ({__license__})")
    print(f"  Python:    {pinfo.python_version}")
    print(f"  OS:        {pinfo.system} ({platform.machine()})\n")
    return 0


def cmd_test(args: argparse.Namespace, color_ok: bool) -> int:
    print(colorize("Running internal verification self-test...", AnsiColor.CYAN, color_ok))
    r = evaluate_wcag("#000000", "#ffffff")
    assert r.ratio >= 20.0, "Black on white must have ratio >= 20"
    apca = evaluate_apca("#000000", "#ffffff")
    assert apca.abs_lc >= 100.0, "APCA Black on white must be >= 100 Lc"
    sims = simulate_all_deficiencies("#1a73e8", "#ffffff")
    assert len(sims) == 8, "Must simulate 8 deficiencies"
    from .harmonic_palette import generate_harmonic_palette
    pal = generate_harmonic_palette("#1a73e8", harmony_type="analogous", mode="light")
    assert len(pal.colors) >= 5, "Harmonic palette must have >= 5 colors"
    assert pal.guaranteed_compliant is True, "Harmonic palette must be compliant"
    print(colorize("✔ All internal checks passed!", AnsiColor.BRIGHT_GREEN, color_ok))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parent_parser.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose output")
    parent_parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    parser = argparse.ArgumentParser(
        prog="wcag-guard",
        description="Universal WCAG 2.2 & APCA Color Contrast Engine, Colorblindness Simulator & Remediation Studio.",
        parents=[parent_parser],
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # 1. check
    p_check = subparsers.add_parser("check", parents=[parent_parser], help="Evaluate WCAG contrast between two colors")
    p_check.add_argument("foreground", help="Foreground color (#hex, rgb, hsl, name)")
    p_check.add_argument("background", help="Background color (#hex, rgb, hsl, name)")
    p_check.add_argument("--json", action="store_true", help="Output JSON format")

    # 1b. harmonic / matrix / palette
    p_harm = subparsers.add_parser("harmonic", aliases=["palette", "matrix"], parents=[parent_parser], help="Generate accessible N-color harmonic palette matrix")
    p_harm.add_argument("seed", nargs="?", default="#1a73e8", help="Seed or brand anchor color (default: #1a73e8)")
    p_harm.add_argument("--harmony", default="analogous", choices=["analogous", "complementary", "split_complementary", "triadic", "tetradic", "monochromatic", "tonal"], help="Color harmony scheme")
    p_harm.add_argument("--mode", default="light", choices=["light", "dark", "auto"], help="Theme mode")
    p_harm.add_argument("--count", type=int, default=None, help="Specific number of colors (default: 10 semantic roles)")
    p_harm.add_argument("--no-guarantee", action="store_true", help="Disable automatic contrast solving")
    p_harm.add_argument("--css", action="store_true", help="Output CSS custom properties")
    p_harm.add_argument("--svg", help="Save visual SVG swatch and matrix sheet to file")
    p_harm.add_argument("--json", action="store_true", help="Output JSON format")

    # 2. apca
    p_apca = subparsers.add_parser("apca", parents=[parent_parser], help="Calculate APCA perceptual lightness contrast")
    p_apca.add_argument("foreground", help="Foreground color")
    p_apca.add_argument("background", help="Background color")
    p_apca.add_argument("--json", action="store_true", help="Output JSON format")

    # 3. simulate
    p_sim = subparsers.add_parser("simulate", parents=[parent_parser], help="Simulate color vision deficiencies")
    p_sim.add_argument("foreground", help="Foreground color")
    p_sim.add_argument("background", help="Background color")
    p_sim.add_argument("--json", action="store_true", help="Output JSON format")

    # 4. suggest / fix
    p_sug = subparsers.add_parser("suggest", parents=[parent_parser], help="Find closest compliant color with minimal ΔE")
    p_sug.add_argument("foreground", help="Foreground color")
    p_sug.add_argument("background", help="Background color")
    p_sug.add_argument("--target-ratio", default=4.5, type=float, help="Target ratio (default: 4.5)")
    p_sug.add_argument("--adjust", choices=["foreground", "background"], default="foreground", help="Which color to adjust")
    p_sug.add_argument("--json", action="store_true", help="Output JSON format")

    # 5. scan
    p_scan = subparsers.add_parser("scan", parents=[parent_parser], help="Scan CSS file or text for color contrast violations")
    p_scan.add_argument("css_file", help="Path to CSS file or raw CSS string")
    p_scan.add_argument("--json", action="store_true", help="Output JSON format")

    # 6. palettes
    p_pal = subparsers.add_parser("palettes", parents=[parent_parser], help="List available design system palettes")
    p_pal.add_argument("--json", action="store_true", help="Output JSON format")

    # 7. audit
    p_aud = subparsers.add_parser("audit", parents=[parent_parser], help="Audit a palette for accessibility")
    p_aud.add_argument("palette", help="Palette ID or JSON color map")
    p_aud.add_argument("--json", action="store_true", help="Output JSON format")

    # 8. serve
    p_srv = subparsers.add_parser("serve", parents=[parent_parser], help="Launch Google Material 3 Studio Web App")
    p_srv.add_argument("-p", "--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    p_srv.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")

    # 9. mcp
    subparsers.add_parser("mcp", parents=[parent_parser], help="Run Model Context Protocol stdio server")

    # 10. diagnostics / doctor
    p_diag = subparsers.add_parser("diagnostics", parents=[parent_parser], help="System environment telemetry")
    p_diag.add_argument("--json", action="store_true", help="Output JSON format")

    # 11. test
    subparsers.add_parser("test", parents=[parent_parser], help="Run internal self-verification suite")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    color_ok = _supports_color(getattr(args, "no_color", False))

    subcmd = getattr(args, "subcommand", None)
    if subcmd == "check":
        return cmd_check(args, color_ok)
    elif subcmd in ("harmonic", "palette", "matrix"):
        return cmd_harmonic(args, color_ok)
    elif subcmd == "apca":
        return cmd_apca(args, color_ok)
    elif subcmd == "simulate":
        return cmd_simulate(args, color_ok)
    elif subcmd in ("suggest", "fix"):
        return cmd_suggest(args, color_ok)
    elif subcmd == "scan":
        return cmd_scan(args, color_ok)
    elif subcmd == "palettes":
        return cmd_palettes(args, color_ok)
    elif subcmd == "audit":
        return cmd_audit(args, color_ok)
    elif subcmd == "serve":
        return cmd_serve(args, color_ok)
    elif subcmd == "mcp":
        return cmd_mcp(args, color_ok)
    elif subcmd in ("diagnostics", "doctor"):
        return cmd_diagnostics(args, color_ok)
    elif subcmd == "test":
        return cmd_test(args, color_ok)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
