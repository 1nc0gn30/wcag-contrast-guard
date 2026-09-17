"""Pytest configuration and shared fixtures for wcag-contrast-guard."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, List, Tuple

import pytest

# Ensure `src` directory is at the front of sys.path for direct imports
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from wcag_contrast_guard.models import Color


@pytest.fixture
def google_blue() -> Color:
    """Fixture providing Google Material Blue color #1a73e8."""
    return Color(r=26, g=115, b=232, a=1.0, hex="#1a73e8")


@pytest.fixture
def pure_white() -> Color:
    """Fixture providing pure opaque white #ffffff."""
    return Color(r=255, g=255, b=255, a=1.0, hex="#ffffff")


@pytest.fixture
def pure_black() -> Color:
    """Fixture providing pure opaque black #000000."""
    return Color(r=0, g=0, b=0, a=1.0, hex="#000000")


@pytest.fixture
def semi_transparent_black() -> Color:
    """Fixture providing 50% transparent black."""
    return Color(r=0, g=0, b=0, a=0.5, hex="#00000080")


@pytest.fixture
def sample_css_code() -> str:
    """Fixture providing sample CSS stylesheet for scanner testing."""
    return """
    :root {
        --md-primary: #1a73e8;
        --md-bg: #ffffff;
        --md-muted: #70757a;
        --md-accent: var(--md-primary);
    }
    
    body {
        color: var(--md-primary);
        background-color: var(--md-bg);
    }

    .muted-card {
        color: var(--md-muted);
        background: var(--md-bg);
    }

    .fail-badge {
        color: #fbbc05;
        background-color: #ffffff;
    }
    """


@pytest.fixture
def sample_palette_dict() -> Dict[str, str]:
    """Fixture providing test brand palette dict."""
    return {
        "primary": "#1a73e8",
        "secondary": "#34a853",
        "warning": "#fbbc05",
        "danger": "#ea4335",
        "background": "#ffffff",
        "surface": "#f8f9fa",
        "text": "#202124",
    }
