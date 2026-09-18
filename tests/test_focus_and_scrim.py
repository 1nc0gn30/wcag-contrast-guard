"""Unit tests for WCAG 2.2 Focus Appearance, Target Size & Scrim Solvers."""

import json
from unittest.mock import patch
import pytest

from wcag_contrast_guard.focus_and_target_evaluator import (
    FocusAppearanceSpec,
    FocusAppearanceResult,
    TargetSizeSpec,
    TargetSizeResult,
    evaluate_focus_appearance,
    evaluate_target_size,
)
from wcag_contrast_guard.scrim_and_overlay_solver import (
    ScrimSolution,
    ImageTextAuditResult,
    audit_text_over_image,
    composite_color_stack,
    solve_scrim,
)
from wcag_contrast_guard.mcp_server import handle_jsonrpc_request
from wcag_contrast_guard.cli import main as cli_main


# ============================================================================
# Focus Appearance Tests (WCAG 2.2 SC 2.4.11 & 2.4.13)
# ============================================================================

def test_focus_appearance_standard_passing_aa():
    # 2px blue focus outline around 120x40 button on white background
    spec = FocusAppearanceSpec(
        element_width=120,
        element_height=40,
        focus_color="#1a73e8",
        background_color="#ffffff",
        indicator_thickness=2.0,
        style="outline",
    )
    res = evaluate_focus_appearance(spec)
    assert res.passes_aa is True
    assert res.contrast_against_bg >= 3.0
    assert res.indicator_area_px2 >= res.min_required_area_aa_px2
    assert len(res.warnings) == 0

    d = res.to_dict()
    assert d["passes_aa"] is True
    assert "contrast_against_bg" in d


def test_focus_appearance_low_contrast_fails():
    # Very faint gray focus ring on white
    spec = FocusAppearanceSpec(
        element_width=120,
        element_height=40,
        focus_color="#e0e0e0",
        background_color="#ffffff",
        indicator_thickness=2.0,
    )
    res = evaluate_focus_appearance(spec)
    assert res.passes_aa is False
    assert res.contrast_against_bg < 3.0
    assert any("contrast against adjacent background is" in w for w in res.warnings)


def test_focus_appearance_thin_area_fails():
    # Sub-pixel 0.5px thickness does not meet 2px perimeter requirement
    spec = FocusAppearanceSpec(
        element_width=120,
        element_height=40,
        focus_color="#000000",
        background_color="#ffffff",
        indicator_thickness=0.5,
        style="border",
    )
    res = evaluate_focus_appearance(spec)
    assert res.passes_aa is False
    assert res.indicator_area_px2 < res.min_required_area_aa_px2


def test_focus_appearance_background_fill_style():
    # Focused state changes background from white to dark blue
    spec = FocusAppearanceSpec(
        element_width=100,
        element_height=30,
        focus_color="#0d47a1",
        background_color="#ffffff",
        unfocused_color="#ffffff",
        style="background-fill",
    )
    res = evaluate_focus_appearance(spec)
    assert res.passes_aa is True
    assert res.indicator_area_px2 == 3000.0  # 100 * 30


# ============================================================================
# Target Size Tests (WCAG 2.2 SC 2.5.8 & 2.5.5)
# ============================================================================

def test_target_size_44x44_passes_aaa():
    spec = TargetSizeSpec(width_px=48, height_px=48)
    res = evaluate_target_size(spec)
    assert res.passes_aa is True
    assert res.passes_aaa is True
    assert res.area_px2 == 48 * 48
    assert res.min_dimension_px == 48.0


def test_target_size_24x24_passes_aa_only():
    spec = TargetSizeSpec(width_px=24, height_px=24)
    res = evaluate_target_size(spec)
    assert res.passes_aa is True
    assert res.passes_aaa is False
    assert any("Level AAA" in r for r in res.recommendations)


def test_target_size_undersized_with_adequate_spacing():
    # 16x16px icon with 6px spacing satisfies the 24px diameter spacing circle
    spec = TargetSizeSpec(width_px=16, height_px=16, spacing_x_px=6.0, spacing_y_px=6.0)
    res = evaluate_target_size(spec)
    assert res.passes_aa is True
    assert res.spacing_adequate_aa is True


def test_target_size_undersized_without_spacing_fails():
    spec = TargetSizeSpec(width_px=16, height_px=16, spacing_x_px=1.0, spacing_y_px=1.0)
    res = evaluate_target_size(spec)
    assert res.passes_aa is False
    assert res.spacing_adequate_aa is False
    assert len(res.warnings) > 0


def test_target_size_exemptions():
    # Inline text links are exempt
    spec_inline = TargetSizeSpec(width_px=14, height_px=14, is_inline=True)
    res_inline = evaluate_target_size(spec_inline)
    assert res_inline.passes_aa is True
    assert "Inline text link" in (res_inline.exemption_reason or "")

    # Essential presentation
    spec_ess = TargetSizeSpec(width_px=10, height_px=10, is_essential=True)
    res_ess = evaluate_target_size(spec_ess)
    assert res_ess.passes_aa is True
    assert "Essential" in (res_ess.exemption_reason or "")


# ============================================================================
# Scrim & Overlay Solver Tests
# ============================================================================

def test_composite_color_stack():
    # Pure black (#000000) base + pure white at 50% opacity -> mid gray ~128
    res = composite_color_stack(["#000000", "rgba(255, 255, 255, 0.5)"])
    assert 120 <= res.r <= 136
    assert 120 <= res.g <= 136
    assert 120 <= res.b <= 136


def test_solve_scrim_for_white_text_over_bright_background():
    # White text needs a dark scrim to be readable over white backgrounds
    sol = solve_scrim(text_color="#ffffff", target_contrast=4.5)
    assert sol.is_compliant is True
    assert sol.scrim_base_color == "#000000"
    assert 0.40 <= sol.min_opacity <= 0.80
    assert sol.worst_case_contrast_after >= 4.5
    assert "linear-gradient" in sol.css_gradient
    assert "backdrop-filter" in sol.css_frosted_glass


def test_solve_scrim_for_dark_text_over_dark_background():
    # Dark text needs a light scrim
    sol = solve_scrim(text_color="#111827", target_contrast=4.5)
    assert sol.is_compliant is True
    assert sol.scrim_base_color == "#ffffff"
    assert 0.40 <= sol.min_opacity <= 0.80
    assert sol.worst_case_contrast_after >= 4.5


def test_solve_scrim_already_compliant():
    # Black text with a dark scrim over black background?
    # If text is white and we ask for contrast over pure black background:
    sol = solve_scrim(text_color="#ffffff", target_contrast=4.5, scrim_base_color="#ffffff")
    assert sol.is_compliant is True


def test_audit_text_over_image():
    # White text is NOT safe without an overlay because image could have white spots
    res = audit_text_over_image("#ffffff", target_contrast=4.5)
    assert res.is_safe_without_scrim is False
    assert res.worst_case_contrast < 1.1  # White on white is 1:1
    assert res.best_case_contrast >= 20.0  # White on black is 21:1
    assert res.recommended_scrim_mode == "dark_scrim"
    assert res.suggested_scrim is not None
    assert res.suggested_scrim.is_compliant is True


# ============================================================================
# MCP Tool Tests
# ============================================================================

def test_mcp_focus_appearance_tool():
    req = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "wcag_evaluate_focus_appearance",
            "arguments": {
                "element_width": 100,
                "element_height": 36,
                "focus_color": "#1a73e8",
                "background_color": "#ffffff",
                "indicator_thickness": 2,
            }
        }
    }
    res = handle_jsonrpc_request(req)
    assert res is not None
    assert res["result"]["isError"] is False
    payload = json.loads(res["result"]["content"][0]["text"])
    assert payload["passes_aa"] is True
    assert payload["contrast_against_bg"] >= 3.0


def test_mcp_target_size_tool():
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "wcag_evaluate_target_size",
            "arguments": {
                "width_px": 44,
                "height_px": 44,
            }
        }
    }
    res = handle_jsonrpc_request(req)
    assert res is not None
    assert res["result"]["isError"] is False
    payload = json.loads(res["result"]["content"][0]["text"])
    assert payload["passes_aa"] is True
    assert payload["passes_aaa"] is True


def test_mcp_scrim_overlay_tool():
    req = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "wcag_solve_scrim_overlay",
            "arguments": {
                "text_color": "#ffffff",
                "target_contrast": 4.5,
            }
        }
    }
    res = handle_jsonrpc_request(req)
    assert res is not None
    assert res["result"]["isError"] is False
    payload = json.loads(res["result"]["content"][0]["text"])
    assert payload["is_compliant"] is True
    assert payload["min_opacity"] > 0


# ============================================================================
# CLI Command Tests
# ============================================================================

def test_cli_focus_command(capsys):
    rc = cli_main(["focus", "--focus", "#1a73e8", "--background", "#ffffff", "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["passes_aa"] is True


def test_cli_target_command(capsys):
    rc = cli_main(["target", "--width", "48", "--height", "48", "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["passes_aaa"] is True


def test_cli_scrim_command(capsys):
    rc = cli_main(["scrim", "#ffffff", "--target-ratio", "4.5", "--json"])
    assert rc == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["is_compliant"] is True
    assert "effective_scrim_rgba" in data
