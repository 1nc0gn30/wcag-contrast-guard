"""Tests for wcag_contrast_guard core modules and API."""

from __future__ import annotations

import json
import pytest

from wcag_contrast_guard import (
    Color,
    ColorblindType,
    calculate_contrast_ratio,
    evaluate_wcag,
    evaluate_apca,
    simulate_colorblindness,
    simulate_all_deficiencies,
    remediate_contrast,
    scan_css_string,
    audit_palette,
    list_palettes,
    get_palette,
    get_platform_info,
)
from wcag_contrast_guard.color_math import (
    parse_color,
    delta_e_ciede2000,
    color_distance,
    rgb_to_hsl,
    hsl_to_rgb,
    rgb_to_lab,
    lab_to_rgb,
    blend_alpha,
)
from wcag_contrast_guard.mcp_server import handle_jsonrpc_request, PROTOCOL_VERSION, SERVER_NAME
from wcag_contrast_guard.cli import main


# -------------------------------------------------------------------------
# Test Color Math & Parsing
# -------------------------------------------------------------------------
def test_parse_color_hex():
    c = parse_color("#1a73e8")
    assert c.r == 26
    assert c.g == 115
    assert c.b == 232
    assert c.a == 1.0


def test_parse_color_rgb():
    c = parse_color("rgb(255, 0, 128)")
    assert c.r == 255
    assert c.g == 0
    assert c.b == 128


def test_parse_color_named():
    white = parse_color("white")
    assert white.r == 255 and white.g == 255 and white.b == 255
    black = parse_color("black")
    assert black.r == 0 and black.g == 0 and black.b == 0


def test_color_luminance():
    white = parse_color("#ffffff")
    black = parse_color("#000000")
    assert pytest.approx(white.luminance, 0.001) == 1.0
    assert pytest.approx(black.luminance, 0.001) == 0.0


def test_ciede2000_zero_for_same():
    c1 = parse_color("#1a73e8")
    c2 = parse_color("#1a73e8")
    de = color_distance(c1, c2, formula="ciede2000")
    assert de == 0.0


def test_ciede2000_different_colors():
    c1 = parse_color("#ffffff")
    c2 = parse_color("#000000")
    de = color_distance(c1, c2, formula="ciede2000")
    assert de > 50.0


# -------------------------------------------------------------------------
# Test WCAG Evaluation
# -------------------------------------------------------------------------
def test_black_on_white_wcag():
    res = evaluate_wcag("#000000", "#ffffff")
    assert res.ratio >= 21.0
    assert res.aa_normal_pass is True
    assert res.aa_large_pass is True
    assert res.aaa_normal_pass is True
    assert res.aaa_large_pass is True
    assert res.ui_component_pass is True


def test_low_contrast_fails_wcag():
    res = evaluate_wcag("#cccccc", "#ffffff")
    assert res.ratio < 3.0
    assert res.aa_normal_pass is False
    assert res.aa_large_pass is False


# -------------------------------------------------------------------------
# Test APCA Evaluation
# -------------------------------------------------------------------------
def test_apca_black_on_white():
    apca = evaluate_apca("#000000", "#ffffff")
    assert apca.abs_lc >= 100.0
    assert apca.polarity == "dark-on-light"


def test_apca_white_on_black():
    apca = evaluate_apca("#ffffff", "#000000")
    assert apca.abs_lc >= 100.0
    assert apca.polarity == "light-on-dark"


# -------------------------------------------------------------------------
# Test Colorblindness Simulation
# -------------------------------------------------------------------------
def test_simulate_all_deficiencies():
    sims = simulate_all_deficiencies("#1a73e8", "#ffffff")
    assert len(sims) == 8
    for dtype in ColorblindType:
        assert dtype in sims
        assert sims[dtype].simulated_fg is not None
        assert sims[dtype].simulated_bg is not None


# -------------------------------------------------------------------------
# Test Remediation Engine
# -------------------------------------------------------------------------
def test_remediate_low_contrast():
    sug = remediate_contrast("#777777", "#ffffff", target_ratio=4.5, adjust="foreground")
    assert sug.new_ratio >= 4.5
    assert sug.delta_e >= 0.0
    assert sug.suggested_color.hex != ""


# -------------------------------------------------------------------------
# Test CSS Scanner
# -------------------------------------------------------------------------
def test_scan_css_string():
    css = """
    .btn-primary {
        color: #ffffff;
        background-color: #1a73e8;
    }
    .bad-text {
        color: #fbbc05;
        background-color: #ffffff;
    }
    """
    report = scan_css_string(css)
    assert len(report.color_pairs) >= 1
    assert len(report.failing_pairs) >= 1


# -------------------------------------------------------------------------
# Test Catalog Palettes
# -------------------------------------------------------------------------
def test_catalog_palettes():
    pals = list_palettes()
    assert len(pals) >= 3
    audit = audit_palette("google-material-3")
    assert audit.color_count > 0
    assert len(audit.pair_evaluations) > 0


# -------------------------------------------------------------------------
# Test MCP Protocol
# -------------------------------------------------------------------------
def test_mcp_initialize():
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    res = handle_jsonrpc_request(req)
    assert res["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert res["result"]["serverInfo"]["name"] == SERVER_NAME


def test_mcp_tools_list():
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    res = handle_jsonrpc_request(req)
    tools = [t["name"] for t in res["result"]["tools"]]
    assert "wcag_check_contrast" in tools
    assert "wcag_apca_contrast" in tools
    assert "wcag_simulate_colorblindness" in tools
    assert "wcag_suggest_compliant_color" in tools
    assert "wcag_audit_palette" in tools
    assert "wcag_scan_css" in tools


def test_mcp_tool_call_check():
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "wcag_check_contrast",
            "arguments": {"foreground": "#1a73e8", "background": "#ffffff"},
        },
    }
    res = handle_jsonrpc_request(req)
    data = json.loads(res["result"]["content"][0]["text"])
    assert data["ratio"] >= 4.5
    assert data["aa_normal_pass"] is True


# -------------------------------------------------------------------------
# Test CLI Subcommands
# -------------------------------------------------------------------------
def test_cli_check():
    ret = main(["check", "#000000", "#ffffff", "--no-color"])
    assert ret == 0


def test_cli_apca():
    ret = main(["apca", "#000000", "#ffffff", "--no-color"])
    assert ret == 0


def test_cli_simulate():
    ret = main(["simulate", "#1a73e8", "#ffffff", "--no-color"])
    assert ret == 0


def test_cli_suggest():
    ret = main(["suggest", "#777777", "#ffffff", "--no-color"])
    assert ret == 0


def test_cli_diagnostics():
    ret = main(["diagnostics", "--json"])
    assert ret == 0


def test_cli_test():
    ret = main(["test", "--no-color"])
    assert ret == 0


def test_ui_server_and_html():
    from wcag_contrast_guard.ui_server import StudioHTTPRequestHandler
    from pathlib import Path
    
    # Verify public index.html exists and contains rebranded title
    public_html = Path(__file__).resolve().parent.parent / "public" / "index.html"
    assert public_html.exists()
    content = public_html.read_text(encoding="utf-8")
    assert "WCAG Contrast Guard" in content
    assert "influenced by Material 3" in content

