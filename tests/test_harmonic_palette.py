"""Comprehensive test suite for Accessible Harmonic Color Palette Matrix Generator.

Tests 100% pure Python standard library capabilities across platforms.
"""

import json
import pytest
from wcag_contrast_guard.models import Color, HarmonicPaletteResult
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio
from wcag_contrast_guard.harmonic_palette import (
    generate_harmonic_palette,
    build_contrast_matrix,
    export_palette_css,
    export_palette_tailwind,
    export_palette_design_tokens,
    export_palette_svg,
)
from wcag_contrast_guard.mcp_server import handle_jsonrpc_request
from wcag_contrast_guard.cli import main as cli_main


def test_harmonic_palette_light_mode_default():
    """Test generating standard 10-role semantic palette in light mode."""
    res = generate_harmonic_palette("#1a73e8", harmony_type="analogous", mode="light")
    assert isinstance(res, HarmonicPaletteResult)
    assert res.mode == "light"
    assert res.guaranteed_compliant is True
    assert len(res.colors) == 11

    # Verify essential AA contrast requirements
    bg = res.colors["background"]
    assert calculate_contrast_ratio(res.colors["text_primary"], bg) >= 4.5
    assert calculate_contrast_ratio(res.colors["text_muted"], bg) >= 4.5
    assert calculate_contrast_ratio(res.colors["outline"], bg) >= 3.0
    assert calculate_contrast_ratio(res.colors["on_primary"], res.colors["primary"]) >= 4.5
    assert calculate_contrast_ratio(res.colors["on_secondary"], res.colors["secondary"]) >= 4.5


def test_harmonic_palette_dark_mode():
    """Test generating palette in dark mode with dark background and light text."""
    res = generate_harmonic_palette("#3b82f6", harmony_type="triadic", mode="dark")
    assert res.mode == "dark"
    assert res.guaranteed_compliant is True

    bg = res.colors["background"]
    assert bg.luminance < 0.1  # Must be dark
    assert calculate_contrast_ratio(res.colors["text_primary"], bg) >= 4.5
    assert calculate_contrast_ratio(res.colors["on_primary"], res.colors["primary"]) >= 4.5


def test_harmonic_palette_all_harmonies():
    """Test all supported harmony calculations produce valid colors."""
    harmonies = [
        "analogous",
        "complementary",
        "split_complementary",
        "triadic",
        "tetradic",
        "monochromatic",
        "tonal",
    ]
    for harm in harmonies:
        res = generate_harmonic_palette("#e11d48", harmony_type=harm, mode="light")
        assert len(res.colors) >= 5
        assert res.guaranteed_compliant is True
        assert res.total_matrix_cells == len(res.colors) * len(res.colors)


def test_harmonic_palette_custom_count():
    """Test generating a specific N-color sequence (e.g. N=6)."""
    res = generate_harmonic_palette("#059669", harmony_type="analogous", count=6)
    assert len(res.colors) == 6
    assert "color_1" in res.colors
    assert "color_6" in res.colors
    assert len(res.matrix) == 6
    assert len(res.matrix[0]) == 6


def test_contrast_matrix_structure_and_symmetry():
    """Test N x N contrast matrix values and diagonal self-comparison."""
    res = generate_harmonic_palette("#6366f1", count=4)
    matrix = res.matrix
    assert len(matrix) == 4

    # Diagonal must be 1.0 (color compared to itself)
    for i in range(4):
        assert abs(matrix[i][i].ratio - 1.0) < 0.05
        assert matrix[i][i].aa_normal_pass is False

    # Symmetry: ratio(A, B) == ratio(B, A)
    for i in range(4):
        for j in range(4):
            assert abs(matrix[i][j].ratio - matrix[j][i].ratio) < 0.01


def test_export_css_and_tailwind_and_tokens():
    """Test CSS variables, Tailwind JSON, and DTCG design tokens export."""
    res = generate_harmonic_palette("#0284c7")
    
    # CSS
    css = export_palette_css(res.colors)
    assert ":root {" in css
    assert "--color-primary: #" in css
    assert "--color-background: #" in css

    # Tailwind
    tw_str = export_palette_tailwind(res.colors)
    tw_data = json.loads(tw_str)
    assert "theme" in tw_data
    assert "primary" in tw_data["theme"]["extend"]["colors"]

    # Design Tokens DTCG
    tokens_str = export_palette_design_tokens(res.colors)
    tokens = json.loads(tokens_str)
    assert "$version" in tokens
    assert "primary" in tokens["color"]
    assert "$value" in tokens["color"]["primary"]


def test_export_svg_palette():
    """Test SVG swatch sheet generation."""
    res = generate_harmonic_palette("#8b5cf6", mode="dark")
    svg = export_palette_svg(res)
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert "Contrast Ratio Matrix" in svg
    assert "#8b5cf6" in svg.lower()


def test_mcp_generate_harmonic_palette_tool():
    """Test MCP tool call for harmonic palette generator."""
    req = {
        "jsonrpc": "2.0",
        "id": "test-harm-1",
        "method": "tools/call",
        "params": {
            "name": "wcag_generate_harmonic_palette",
            "arguments": {
                "seed_color": "#d97706",
                "harmony_type": "complementary",
                "mode": "light",
            },
        },
    }
    res = handle_jsonrpc_request(req)
    assert res.get("error") is None
    payload = json.loads(res["result"]["content"][0]["text"])
    assert payload["harmony_type"] == "complementary"
    assert "colors" in payload
    assert "matrix" in payload
    assert payload["guaranteed_compliant"] is True


def test_cli_harmonic_subcommand(capsys):
    """Test CLI subcommand harmonic with JSON and CSS output."""
    # JSON test
    cli_main(["harmonic", "#10b981", "--harmony", "triadic", "--json"])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["harmony_type"] == "triadic"
    assert "colors" in data

    # CSS test
    cli_main(["harmonic", "#10b981", "--css"])
    captured_css = capsys.readouterr()
    assert "--color-primary:" in captured_css.out
