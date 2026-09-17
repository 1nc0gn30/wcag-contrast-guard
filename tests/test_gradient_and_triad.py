"""Unit tests for CSS gradient contrast analyzer and accessible triad solver."""

import pytest
from wcag_contrast_guard import (
    Color,
    GradientContrastReport,
    TriadHarmonyResult,
    evaluate_gradient_contrast,
    solve_accessible_triad,
)


def test_gradient_contrast_white_text_on_dark_gradient():
    # Gradient from black to dark navy
    stops = ["#000000", "#0a192f"]
    report = evaluate_gradient_contrast("#ffffff", stops, sample_count=5)

    assert isinstance(report, GradientContrastReport)
    assert report.min_ratio >= 10.0
    assert report.aa_normal_pass is True
    assert report.aa_large_pass is True
    assert report.aaa_normal_pass is True
    assert len(report.sample_ratios) == 5
    d = report.to_dict()
    assert "min_ratio" in d
    assert "stops" in d
    assert len(d["stops"]) == 2


def test_gradient_contrast_insufficient_text():
    # Gradient going from white to light gray: white text will fail
    stops = ["#ffffff", "#e0e0e0"]
    report = evaluate_gradient_contrast("#ffffff", stops, sample_count=7)

    assert report.min_ratio < 2.0
    assert report.aa_normal_pass is False
    assert report.worst_stop_index == 0  # #ffffff against #ffffff is 1.0


def test_gradient_contrast_requires_at_least_two_stops():
    with pytest.raises(ValueError, match="at least 2 stop colors"):
        evaluate_gradient_contrast("#ffffff", ["#000000"])


def test_solve_accessible_triad_light_mode():
    base_brand = "#1a73e8"  # Google blue
    result = solve_accessible_triad(base_brand, mode="light", target_text_ratio=4.5)

    assert isinstance(result, TriadHarmonyResult)
    assert result.is_accessible is True
    assert result.fg_bg_ratio >= 4.5
    assert result.accent_bg_ratio >= 3.0
    assert result.background.hex == "#ffffff"
    d = result.to_dict()
    assert "background" in d
    assert "accent" in d


def test_solve_accessible_triad_dark_mode():
    base_brand = "#ff7043"  # Coral orange
    result = solve_accessible_triad(base_brand, mode="dark", target_text_ratio=4.5)

    assert isinstance(result, TriadHarmonyResult)
    assert result.is_accessible is True
    assert result.fg_bg_ratio >= 4.5
    assert result.accent_bg_ratio >= 3.0
    # Background should be a dark surface
    assert result.background.luminance < 0.2
