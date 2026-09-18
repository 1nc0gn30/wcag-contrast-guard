# WCAG & APCA Contrast Guard

[![CI](https://github.com/google/wcag-contrast-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/google/wcag-contrast-guard/actions/workflows/ci.yml)
[![Python 3.9–3.13](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-0%20external-success.svg)](https://pypi.org/project/wcag-contrast-guard/)
[![WCAG 2.2 AAA](https://img.shields.io/badge/WCAG-2.2%20AA%20%2F%20AAA-brightgreen.svg)](https://www.w3.org/TR/WCAG22/)
[![APCA 0.98G](https://img.shields.io/badge/APCA-0.98G--4g-blueviolet.svg)](https://www.w3.org/WAI/GL/task-forces/silver/wiki/Visual_Contrast_Subgroup)
[![MCP Protocol 2024-11-05](https://img.shields.io/badge/MCP-JSON--RPC%202.0-orange.svg)](https://modelcontextprotocol.io/)

> **The Universal Color Accessibility & Perceptual Contrast Engine, 8-Deficiency Colorblind Simulator, CIEDE2000 Auto-Remediation Solver, Model Context Protocol (MCP) Server, and Interactive Contrast Studio (design influenced by Material 3 tokens).**

---

## Overview

`wcag-contrast-guard` is a production-grade, zero-external-dependency Python library, CLI, MCP Server, and interactive WCAG Contrast Studio web application (with design influenced by Material 3 tokens) for computing, auditing, simulating, and remediating color contrast across digital interfaces.

It unifies the official **W3C WCAG 2.1 / 2.2** relative luminance specification, the modern **APCA (Advanced Perceptual Contrast Algorithm 0.98G)** for WCAG 3.0 Silver, **Machado 2009 / Brettel 1997 Color Vision Deficiency (CVD)** simulation matrices across 8 conditions, **CIEDE2000 ($\Delta E_{00}$)** perceptual color difference minimization for automated remediation, and native CSS/HTML color pair scanning.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   wcag-contrast-guard                                       │
├───────────────────────────────┬──────────────────────────────┬──────────────────────────────┤
│       WCAG 2.2 Engine         │         APCA Engine          │     Colorblind Simulator     │
│   • Relative Luminance (sRGB) │   • Spatial Frequency (0.98G)│   • 8 Deficiency Types       │
│   • AA / AAA Normal & Large   │   • Polarity (BoW & WoB)     │   • Machado 2009 Matrices    │
│   • SC 1.4.11 UI Components   │   • Weight/Size Lookup Table │   • Post-Sim Contrast Audit  │
├───────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│    Auto-Remediation (ΔE00)    │       CSS/HTML Scanner       │     Design System Catalog    │
│   • CIEDE2000 Delta-E Solver  │   • Var & Custom Property Res│   • Material 3, Tailwind 3   │
│   • Minimal Perceptual Shift  │   • Inline & External Sheets │   • GitHub Primer, Apple HIG │
│   • FG / BG / Dual Balancing  │   • Automatic Pair Matching  │   • Radix, Carbon, Dracula   │
├───────────────────────────────┴──────────────────────────────┴──────────────────────────────┤
│                                 Interfaces & Deliverables                                   │
│   [ CLI: wcag-guard ]   •   [ MCP Server: JSON-RPC ]   •   [ Contrast Guard Web Studio ]    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

1. **Zero External Dependencies**: 100% pure Python standard library (`math`, `re`, `dataclasses`, `enum`, `json`, `http.server`, `urllib`). No NumPy, Pillow, or web frameworks required.
2. **Dual Contrast Algorithms**:
   - **WCAG 2.1 / 2.2**: Relative luminance calculation with gamma correction and alpha compositing.
   - **APCA-W3 0.98G-4g**: Human spatial frequency vision modeling, power-law TRC, soft black clamping, text polarity (Dark on Light vs Light on Dark), and recommended font size $\times$ weight matrix.
3. **8-Deficiency Colorblind Simulator**:
   - Protanopia & Protanomaly (L-cone absent/shifted)
   - Deuteranopia & Deuteranomaly (M-cone absent/shifted)
   - Tritanopia & Tritanomaly (S-cone absent/shifted)
   - Achromatopsia & Achromatomaly (Monochromacy)
4. **Intelligent Delta-E ($\Delta E_{2000}$) Remediation**:
   - Binary search in CIE $L^*a^*b^*$ color space.
   - Calculates the closest accessible color satisfying target contrast with minimal perceptual shift.
5. **Full CSS / HTML Stylesheet Scanner**:
   - Parses CSS custom properties (`--var`), rule declarations (`color`, `background-color`), and HTML inline styles.
6. **Built-in Design System Catalog**:
   - Pre-packaged palettes for Google Material 3, Tailwind CSS 3, GitHub Primer, Apple HIG, Radix Colors, IBM Carbon, Dracula, Solarized, Nord, and One Dark.
7. **Model Context Protocol (MCP) Server**:
   - Native integration with Claude Desktop, Cursor, Cline, and Zed over stdio.
8. **WCAG Contrast Studio Web App** (Design influenced by Material 3 tokens):
   - Interactive dual color picker, real-time ratio badge, WCAG matrix, APCA table, 8-lens CVD viewer, 1-click auto-fix swatch, and CSS auditor.

---

## Mathematical Foundations

### 1. WCAG 2.1 / 2.2 Relative Luminance & Contrast

Under W3C WCAG 2.2, sRGB color channels ($R, G, B \in [0, 255]$) are normalized ($R_{sRGB}, G_{sRGB}, B_{sRGB} \in [0.0, 1.0]$) and converted to linear RGB ($R_{lin}, G_{lin}, B_{lin}$) via the inverse sRGB gamma companding formula:

$$
C_{lin} = \begin{cases} 
\frac{C_{sRGB}}{12.92} & \text{if } C_{sRGB} \le 0.04045 \\
\left(\frac{C_{sRGB} + 0.055}{1.055}\right)^{2.4} & \text{if } C_{sRGB} > 0.04045 
\end{cases}
$$

Relative luminance ($L \in [0.0, 1.0]$) is computed using the ITU-R Recommendation BT.709 coefficients:

$$
L = 0.2126 \cdot R_{lin} + 0.7152 \cdot G_{lin} + 0.0722 \cdot B_{lin}
$$

The contrast ratio between lighter color $L_1$ and darker color $L_2$ ($L_1 \ge L_2$) is:

$$
\text{Ratio} = \frac{L_1 + 0.05}{L_2 + 0.05} \quad (\text{Range: } 1.0 : 1 \text{ to } 21.0 : 1)
$$

#### WCAG Conformance Thresholds

| Element Type | Level AA | Level AAA | Success Criterion |
| :--- | :--- | :--- | :--- |
| **Normal Text** ($< 18\text{pt}$ or $< 14\text{pt bold}$) | $\ge 4.5 : 1$ | $\ge 7.0 : 1$ | SC 1.4.3 / SC 1.4.6 |
| **Large Text** ($\ge 18\text{pt}$ or $\ge 14\text{pt bold}$) | $\ge 3.0 : 1$ | $\ge 4.5 : 1$ | SC 1.4.3 / SC 1.4.6 |
| **UI Components & Graphical Objects** | $\ge 3.0 : 1$ | N/A | SC 1.4.11 |

---

### 2. APCA (Advanced Perceptual Contrast Algorithm) 0.98G

APCA computes Lightness Contrast ($L_c$) based on human spatial contrast sensitivity and polarity:

1. Linearized Y luminance with soft black clamp:
$$
Y = 0.2126729 \cdot R_{lin}^{2.4} + 0.7151522 \cdot G_{lin}^{2.4} + 0.0721750 \cdot B_{lin}^{2.4}
$$
$$
Y_{clamped} = \begin{cases} Y + (0.022 - Y)^{1.414} & \text{if } Y < 0.022 \\ Y & \text{if } Y \ge 0.022 \end{cases}
$$

2. Polarity determination:
   - **Dark text on Light bg (BoW)**: $L_c = \left( Y_{bg}^{0.56} - Y_{txt}^{0.57} \right) \cdot 1.14 - 0.027$
   - **Light text on Dark bg (WoB)**: $L_c = \left( Y_{bg}^{0.65} - Y_{txt}^{0.62} \right) \cdot 1.14 + 0.027$

---

### 3. CIEDE2000 ($\Delta E_{00}$) Perceptual Color Difference

To auto-remediate failing pairs, `wcag-contrast-guard` converts colors into CIE $L^*a^*b^*$ and executes binary search along the $L^*$ axis to locate the color closest to the original with minimum CIEDE2000 distance:

$$
\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{k_L S_L}\right)^2 + \left(\frac{\Delta C'}{k_C S_C}\right)^2 + \left(\frac{\Delta H'}{k_H S_H}\right)^2 + R_T \left(\frac{\Delta C'}{k_C S_C}\right)\left(\frac{\Delta H'}{k_H S_H}\right)}
$$

---

## Installation

```bash
# Install directly via pip
pip install wcag-contrast-guard

# Or install from source in editable mode
git clone https://github.com/google/wcag-contrast-guard.git
cd wcag-contrast-guard
pip install -e .
```

---

## CLI Reference

`wcag-guard` (or `wcag-contrast-guard`) includes subcommands for every accessibility task:

```bash
# 1. Quick WCAG Contrast Check
wcag-guard check "#1a73e8" "#ffffff"
wcag-guard check "rgb(26, 115, 232)" "white" --json

# 2. APCA Perceptual Contrast & Font Weight Table
wcag-guard apca "#1a73e8" "#ffffff" --json

# 3. Simulate 8 Color Vision Deficiencies
wcag-guard simulate "#ea4335" "#34a853"
wcag-guard simulate "#1a73e8" "#ffffff" --json

# 4. Automated CIEDE2000 Color Remediation
wcag-guard suggest "#777777" "#ffffff" --target-ratio 4.5
wcag-guard suggest "#fbbc05" "#ffffff" --adjust background --json

# 5. Scan CSS Files for Low-Contrast Pairs
wcag-guard scan styles.css
wcag-guard scan styles.css --json

# 6. Audit Design System Palettes
wcag-guard palettes
wcag-guard audit google-material-3
wcag-guard audit tailwind-css-3 --json

# 7. Launch WCAG Contrast Studio Web App (Material 3 influenced)
wcag-guard serve --port 8080

# 8. Diagnostics & Self-Test
wcag-guard diagnostics
wcag-guard test
```

---

## Python API Usage

```python
from wcag_contrast_guard import (
    evaluate_wcag,
    calculate_contrast_ratio,
    evaluate_apca,
    simulate_colorblindness,
    simulate_all_deficiencies,
    remediate_contrast,
    scan_css_string,
    audit_palette,
    list_palettes,
)

# 1. WCAG 2.2 Contrast Evaluation
result = evaluate_wcag("#1a73e8", "#ffffff")
print(f"Ratio: {result.ratio_str}")             # '4.52:1'
print(f"AA Normal: {result.aa_normal_pass}")     # True
print(f"AAA Normal: {result.aaa_normal_pass}")   # False
print(f"Summary: {result.summary()}")

# 2. APCA Contrast
apca = evaluate_apca("#1a73e8", "#ffffff")
print(f"APCA Lc: {apca.lc}")                     # -64.2
print(f"Recommended Use: {apca.accessible_use}")
print(f"Min Font Sizes (pt): {apca.min_font_size_pt}")

# 3. Colorblind Simulation
sims = simulate_all_deficiencies("#1a73e8", "#ffffff")
for sim in sims:
    print(f"{sim.deficiency.value}: {sim.simulated_fg.hex} on {sim.simulated_bg.hex} -> {sim.simulated_ratio:.2f}:1")

# 4. CIEDE2000 Remediation
remedy = remediate_contrast("#777777", "#ffffff", target_ratio=4.5, adjust="foreground")
print(f"Suggested Color: {remedy.suggested_color.hex}")
print(f"Delta-E: {remedy.delta_e:.2f}")
print(f"New Ratio: {remedy.new_ratio:.2f}:1")

# 5. CSS Scanning
css = """
:root { --brand: #1a73e8; --bg: #ffffff; }
.card { color: var(--brand); background-color: var(--bg); }
"""
scan_res = scan_css_string(css)
print(f"Found {scan_res.pairs_count} color pairs, {scan_res.failing_pairs_count} failing.")

# 6. WCAG 2.2 Focus Appearance Evaluator (SC 2.4.11 / SC 2.4.13)
from wcag_contrast_guard import evaluate_focus_appearance, evaluate_target_size, solve_scrim
focus_eval = evaluate_focus_appearance(
    focus_indicator_color="#005fcc",
    unfocused_color="#ffffff",
    background_color="#ffffff",
    component_width=120,
    component_height=40,
    indicator_thickness=2
)
print(f"Focus Passing AA: {focus_eval.passes_aa}, Indicator Area: {focus_eval.indicator_area_px}px")

# 7. WCAG 2.2 Target Size Evaluator (SC 2.5.8 / SC 2.5.5)
target_eval = evaluate_target_size(width=28, height=28)
print(f"Target Size Passing AA (24x24): {target_eval.passes_aa}")

# 8. Text Scrim / Backdrop Overlay Solver
scrim_solution = solve_scrim(
    text_color="#ffffff",
    backdrop_color="#ffffff",
    scrim_color="#000000",
    target_ratio=4.5
)
print(f"Minimum Scrim Opacity: {scrim_solution.scrim_alpha:.2f} -> {scrim_solution.css_rgba}")
```

---

## Model Context Protocol (MCP) Server

`wcag-contrast-guard` exposes a full MCP server over `stdio` using JSON-RPC 2.0.

### Setup for Claude Desktop / Cursor / Cline

Add the following to your `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "wcag-contrast-guard": {
      "command": "wcag-guard",
      "args": ["mcp"]
    }
  }
}
```

### Registered MCP Tools

| Tool Name | Description |
| :--- | :--- |
| `wcag_check_contrast` | Evaluate WCAG 2.1/2.2 contrast ratio and AA/AAA compliance |
| `wcag_apca_contrast` | Calculate APCA perceptual contrast ($L_c$) and font requirements |
| `wcag_simulate_colorblindness` | Simulate colors across 8 color vision deficiency types |
| `wcag_suggest_compliant_color` | Find closest accessible color with minimal CIEDE2000 shift |
| `wcag_audit_palette` | Audit a complete color palette matrix |
| `wcag_scan_css` | Extract and audit color pairs from CSS source code |
| `wcag_list_palettes` | List built-in design system palettes |
| `wcag_evaluate_focus_appearance` | Audit WCAG 2.2 SC 2.4.11 / 2.4.13 focus indicator contrast and minimum area |
| `wcag_evaluate_target_size` | Evaluate WCAG 2.2 SC 2.5.8 / 2.5.5 pointer touch target bounding box & spacing circle |
| `wcag_solve_scrim_overlay` | Calculate minimum opacity scrim overlay or audit text over image contrast |
| `wcag_diagnostics` | Check system environment and supported standards |

---

## Testing & CI

The test suite provides 100% verification across all math routines, color parsers, WCAG engines, APCA formulas, CVD matrices, remediation solvers, CSS scanners, CLI entry points, MCP protocols, and the UI HTTP server:

```bash
# Run test suite
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=wcag_contrast_guard --cov-report=term-missing
```

---

## License

MIT License © 2026 WCAG Contrast Guard Engineering Team
