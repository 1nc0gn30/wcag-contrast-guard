"""Model Context Protocol (MCP) Server for WCAG Contrast Guard.

Implements JSON-RPC 2.0 protocol over stdio for tool calling, resource inspection,
and prompting per the MCP specification (2024-11-05).
100% Python Standard Library. Zero external dependencies.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from wcag_contrast_guard.apca_engine import calculate_apca_lc, evaluate_apca
from wcag_contrast_guard.catalog import (
    audit_custom_palette,
    audit_palette,
    get_palette,
    list_palettes,
)
from wcag_contrast_guard.color_math import (
    color_distance,
    delta_e_ciede2000,
    parse_color,
)
from wcag_contrast_guard.colorblind_sim import (
    simulate_all_deficiencies,
    simulate_colorblindness,
)
from wcag_contrast_guard.compat import get_platform_info
from wcag_contrast_guard.css_scanner import scan_css_string
from wcag_contrast_guard.models import Color, ColorblindType
from wcag_contrast_guard.remediation import remediate_contrast
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio, evaluate_wcag

# Protocol Constants
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "wcag-contrast-guard"
SERVER_VERSION = "0.1.0"

# Registered MCP Tools
TOOL_DEFINITIONS = [
    {
        "name": "wcag_check_contrast",
        "description": "Evaluate WCAG 2.1/2.2 contrast ratio and AA/AAA compliance between two colors.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "foreground": {
                    "type": "string",
                    "description": "Foreground / text color representation (e.g., '#1a73e8', 'rgb(26, 115, 232)', 'white')."
                },
                "background": {
                    "type": "string",
                    "description": "Background color representation (e.g., '#ffffff', 'hsl(0, 0%, 100%)', 'black')."
                }
            },
            "required": ["foreground", "background"]
        }
    },
    {
        "name": "wcag_apca_contrast",
        "description": "Calculate APCA perceptual Lightness Contrast (Lc) and font requirements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "foreground": {
                    "type": "string",
                    "description": "Foreground / text color."
                },
                "background": {
                    "type": "string",
                    "description": "Background color."
                }
            },
            "required": ["foreground", "background"]
        }
    },
    {
        "name": "wcag_simulate_colorblindness",
        "description": "Simulate color perception across 8 types of color vision deficiencies (protanopia, deuteranopia, tritanopia, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "foreground": {
                    "type": "string",
                    "description": "Foreground color to simulate."
                },
                "background": {
                    "type": "string",
                    "description": "Background color to simulate."
                },
                "deficiency": {
                    "type": "string",
                    "description": "Deficiency type ('all', 'protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia', etc.). Default: 'all'.",
                    "default": "all"
                }
            },
            "required": ["foreground", "background"]
        }
    },
    {
        "name": "wcag_suggest_compliant_color",
        "description": "Find closest accessible color satisfying target contrast with minimal CIEDE2000 perceptual delta-E shift.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "foreground": {
                    "type": "string",
                    "description": "Foreground color."
                },
                "background": {
                    "type": "string",
                    "description": "Background color."
                },
                "target_ratio": {
                    "type": "number",
                    "description": "Target WCAG contrast ratio (default: 4.5 for AA normal text).",
                    "default": 4.5
                },
                "adjust": {
                    "type": "string",
                    "description": "Which color to adjust: 'foreground' or 'background'. Default: 'foreground'.",
                    "default": "foreground"
                }
            },
            "required": ["foreground", "background"]
        }
    },
    {
        "name": "wcag_audit_palette",
        "description": "Audit a complete design system color palette matrix for WCAG compliance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "palette": {
                    "type": "string",
                    "description": "Built-in palette ID (e.g. 'google-material-3', 'tailwind-css-3', 'apple-human-interface') or JSON object of key-value color hexes."
                }
            },
            "required": ["palette"]
        }
    },
    {
        "name": "wcag_scan_css",
        "description": "Extract and audit foreground/background color declarations from CSS stylesheet source code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "css": {
                    "type": "string",
                    "description": "Raw CSS stylesheet content to parse and audit."
                }
            },
            "required": ["css"]
        }
    },
    {
        "name": "wcag_list_palettes",
        "description": "List all built-in accessible design system color palettes and presets.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "wcag_diagnostics",
        "description": "Return environment telemetry, supported standards, and color conversion capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "wcag_generate_harmonic_palette",
        "description": "Generate an N-color accessible harmonic palette with full contrast matrix, CSS custom properties, and design tokens.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seed_color": {
                    "type": "string",
                    "description": "Seed or brand anchor color (#hex, rgb, hsl, or CSS name).",
                    "default": "#1a73e8"
                },
                "harmony_type": {
                    "type": "string",
                    "enum": ["analogous", "complementary", "split_complementary", "triadic", "tetradic", "monochromatic", "tonal"],
                    "description": "Color harmony relationship.",
                    "default": "analogous"
                },
                "mode": {
                    "type": "string",
                    "enum": ["light", "dark", "auto"],
                    "description": "Theme mode.",
                    "default": "light"
                },
                "count": {
                    "type": "integer",
                    "description": "Optional specific number of colors (default: 10 semantic roles)."
                },
                "guarantee_wcag_aa": {
                    "type": "boolean",
                    "description": "Whether to mathematically solve contrast for WCAG AA compliance.",
                    "default": True
                }
            },
            "required": ["seed_color"]
        }
    }
]


# Tool Execution Handlers
def _tool_check_contrast(args: Dict[str, Any]) -> Dict[str, Any]:
    fg = args.get("foreground", "")
    bg = args.get("background", "")
    res = evaluate_wcag(fg, bg)
    return res.to_dict()


def _tool_apca(args: Dict[str, Any]) -> Dict[str, Any]:
    fg = args.get("foreground", "")
    bg = args.get("background", "")
    res = evaluate_apca(fg, bg)
    return res.to_dict()


def _tool_simulate(args: Dict[str, Any]) -> Dict[str, Any]:
    fg = args.get("foreground", "")
    bg = args.get("background", "")
    deficiency = args.get("deficiency", "all").lower()

    if deficiency == "all":
        sims = simulate_all_deficiencies(fg, bg)
        return {
            "foreground": parse_color(fg).hex,
            "background": parse_color(bg).hex,
            "simulations": [s.to_dict() for s in sims],
        }
    else:
        try:
            dtype = ColorblindType(deficiency)
        except ValueError:
            dtype = ColorblindType.DEUTERANOPIA
        sim = simulate_colorblindness(fg, bg, dtype)
        return sim.to_dict()


def _tool_suggest(args: Dict[str, Any]) -> Dict[str, Any]:
    fg = args.get("foreground", "")
    bg = args.get("background", "")
    ratio = float(args.get("target_ratio", 4.5))
    adjust = args.get("adjust", "foreground")
    sug = remediate_contrast(fg, bg, target_ratio=ratio, adjust=adjust)
    return sug.to_dict()


def _tool_audit_palette(args: Dict[str, Any]) -> Dict[str, Any]:
    pal = args.get("palette", "")
    if pal.startswith("{"):
        try:
            colors_dict = json.loads(pal)
            rep = audit_custom_palette("custom", colors_dict)
            return rep.to_dict()
        except Exception:
            pass
    rep = audit_palette(pal)
    return rep.to_dict()


def _tool_scan_css(args: Dict[str, Any]) -> Dict[str, Any]:
    css = args.get("css", "")
    rep = scan_css_string(css)
    return rep.to_dict()


def _tool_list_palettes(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"palettes": list_palettes()}


def _tool_diagnostics(args: Dict[str, Any]) -> Dict[str, Any]:
    pinfo = get_platform_info()
    return {
        "server": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "protocol_version": PROTOCOL_VERSION,
        },
        "platform": pinfo.as_dict() if hasattr(pinfo, "as_dict") else {
            "os_name": pinfo.os_name,
            "python_version": pinfo.python_version,
            "is_linux": pinfo.is_linux,
            "is_macos": pinfo.is_macos,
            "is_windows": pinfo.is_windows,
        },
        "standards": [
            "WCAG 2.1 (Level AA / AAA)",
            "WCAG 2.2 (Focus Appearance & Non-text Contrast)",
            "APCA 0.98G-4g (Advanced Perceptual Contrast Algorithm)",
            "CIEDE2000 (Color Difference Delta-E 00)",
            "Brettel 1997 / Machado 2009 Colorblindness Simulation",
        ],
        "tool_count": len(TOOL_DEFINITIONS),
    }


def _tool_generate_harmonic_palette(args: Dict[str, Any]) -> Dict[str, Any]:
    from .harmonic_palette import generate_harmonic_palette
    seed = args.get("seed_color", "#1a73e8")
    harmony = args.get("harmony_type", "analogous")
    mode = args.get("mode", "light")
    count = args.get("count")
    guarantee = args.get("guarantee_wcag_aa", True)
    res = generate_harmonic_palette(seed, harmony_type=harmony, mode=mode, count=count, guarantee_wcag_aa=guarantee)
    return res.to_dict()


TOOL_HANDLERS = {
    "wcag_check_contrast": _tool_check_contrast,
    "wcag_apca_contrast": _tool_apca,
    "wcag_simulate_colorblindness": _tool_simulate,
    "wcag_suggest_compliant_color": _tool_suggest,
    "wcag_audit_palette": _tool_audit_palette,
    "wcag_scan_css": _tool_scan_css,
    "wcag_list_palettes": _tool_list_palettes,
    "wcag_diagnostics": _tool_diagnostics,
    "wcag_generate_harmonic_palette": _tool_generate_harmonic_palette,
}


def handle_jsonrpc_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle a single parsed JSON-RPC 2.0 request dictionary."""
    if not isinstance(request, dict):
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
        }

    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {}) or {}

    if method is None:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid Request: missing method name"},
        }

    # 1. initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            },
        }

    # 2. notifications/initialized
    if method == "notifications/initialized":
        if req_id is not None:
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        return None

    # 3. ping
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 4. tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOL_DEFINITIONS},
        }

    # 5. tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {}) or {}

        if tool_name not in TOOL_HANDLERS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: '{tool_name}'",
                },
            }

        handler = TOOL_HANDLERS[tool_name]
        try:
            tool_result = handler(arguments)
            formatted_text = json.dumps(tool_result, indent=2, ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": formatted_text,
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }

    # Unknown Method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: '{method}'"},
    }


def process_request(request: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    """Process a raw JSON string or dictionary request and return response."""
    if isinstance(request, str):
        try:
            parsed = json.loads(request)
        except json.JSONDecodeError as exc:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(exc)}"},
            })
        resp = handle_jsonrpc_request(parsed)
        return json.dumps(resp, ensure_ascii=False) if resp is not None else ""
    elif isinstance(request, dict):
        resp = handle_jsonrpc_request(request)
        return resp if resp is not None else {}
    raise ValueError("Request must be a JSON string or dict")


handle_jsonrpc_message = handle_jsonrpc_request


def run_stdio_server() -> None:
    """Run the MCP server over standard input/output streams."""
    sys.stderr.write(f"[{SERVER_NAME} v{SERVER_VERSION}] MCP stdio server started.\n")
    sys.stderr.flush()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            trimmed = line.strip()
            if not trimmed:
                continue

            resp = process_request(trimmed)
            if resp:
                sys.stdout.write(f"{resp}\n")
                sys.stdout.flush()
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as err:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal server error: {str(err)}"},
            }
            sys.stdout.write(f"{json.dumps(err_resp)}\n")
            sys.stdout.flush()
