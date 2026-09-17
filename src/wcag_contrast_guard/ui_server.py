"""WCAG & APCA Contrast Guard Studio Web UI & REST API Server.

Provides a multi-threaded pure Python HTTP server hosting:
- Studio web application UI influenced by Material 3 design.
- REST API for WCAG 2.2, APCA calculations, colorblindness simulation,
  auto-remediation, design system palette audits, and CSS scanning.
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from wcag_contrast_guard.apca_engine import evaluate_apca
from wcag_contrast_guard.catalog import audit_palette, get_palette, list_palettes
from wcag_contrast_guard.color_math import Color, delta_e_ciede2000, parse_color
from wcag_contrast_guard.colorblind_sim import simulate_colorblindness
from wcag_contrast_guard.compat import get_platform_info, normalize_path as safe_path_normalization
from wcag_contrast_guard.css_scanner import scan_css_string
from wcag_contrast_guard.models import ColorblindType, WCAGLevel
from wcag_contrast_guard.remediation import suggest_remediation
from wcag_contrast_guard.wcag_engine import check_contrast

# Default embedded HTML fallback for standalone execution
EMBEDDED_STUDIO_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WCAG Contrast Studio | Standalone Fallback</title>
  <style>
    :root {
      --primary: #1a73e8;
      --surface: #ffffff;
      --bg: #f8f9fa;
      --text: #202124;
      --text-muted: #5f6368;
      --border: #dadce0;
      --pass: #1e8e3e;
      --fail: #d93025;
    }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 2rem; }
    .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; max-width: 800px; margin: 0 auto; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1 { color: var(--primary); font-size: 1.5rem; margin-bottom: 1rem; }
    .row { display: flex; gap: 1rem; margin-bottom: 1rem; }
    .col { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
    input[type="text"], input[type="color"] { padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px; }
    .ratio-box { font-size: 2.5rem; font-weight: bold; margin: 1rem 0; font-family: monospace; }
    .pill { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 999px; font-weight: bold; font-size: 0.85rem; }
    .pass { background: #ceead6; color: var(--pass); }
    .fail { background: #fad2cf; color: var(--fail); }
    .preview { padding: 1.5rem; border-radius: 8px; margin-top: 1rem; border: 1px solid var(--border); }
  </style>
</head>
<body>
  <div class="card">
    <h1>WCAG &amp; APCA Contrast Studio</h1>
    <div class="row">
      <div class="col">
        <label>Foreground Color</label>
        <input type="text" id="fg-text" value="#1a73e8">
      </div>
      <div class="col">
        <label>Background Color</label>
        <input type="text" id="bg-text" value="#ffffff">
      </div>
    </div>
    <div class="ratio-box" id="ratio-display">4.52 : 1</div>
    <span class="pill pass" id="ratio-status">PASS WCAG AA</span>
    <div class="preview" id="preview-box">
      <h3>The quick brown fox jumps over the lazy dog.</h3>
      <p>Accessible typography ensures readability for all users across various lighting conditions and displays.</p>
    </div>
  </div>
  <script>
    async function update() {
      const fg = document.getElementById('fg-text').value;
      const bg = document.getElementById('bg-text').value;
      try {
        const res = await fetch(`/api/check?fg=${encodeURIComponent(fg)}&bg=${encodeURIComponent(bg)}`);
        if (res.ok) {
          const data = await res.json();
          document.getElementById('ratio-display').textContent = data.ratio_str;
          const status = document.getElementById('ratio-status');
          if (data.aa_normal_pass) {
            status.className = 'pill pass';
            status.textContent = data.aaa_normal_pass ? 'PASS WCAG AAA' : 'PASS WCAG AA';
          } else {
            status.className = 'pill fail';
            status.textContent = 'FAIL WCAG AA';
          }
          const box = document.getElementById('preview-box');
          box.style.color = data.foreground.hex;
          box.style.backgroundColor = data.background.hex;
        }
      } catch (e) {}
    }
    document.getElementById('fg-text').addEventListener('input', update);
    document.getElementById('bg-text').addEventListener('input', update);
    update();
  </script>
</body>
</html>
"""


class StudioHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler for WCAG Studio UI & REST API Endpoints."""

    server_version = "Google-WCAG-Studio/0.1.0"

    def __init__(self, *args: Any, public_dir: Optional[Path] = None, quiet: bool = False, **kwargs: Any) -> None:
        self.public_dir = public_dir
        self.quiet = quiet
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress logging if quiet mode is active."""
        if not self.quiet:
            sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def _set_cors_headers(self) -> None:
        """Send standard Cross-Origin Resource Sharing (CORS) headers."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Send JSON response with UTF-8 encoding and headers."""
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_text(self, text: str, status: int = 200, content_type: str = "text/html; charset=utf-8") -> None:
        """Send plain text or HTML response."""
        try:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_error(self, message: str, status: int = 400) -> None:
        """Send standard JSON error envelope."""
        self._send_json({"error": message, "status": status, "success": False}, status=status)

    def _read_json_body(self) -> Dict[str, Any]:
        """Read and parse JSON payload from request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception:
            # Fallback if raw text
            return {"raw": raw_body.decode("utf-8", errors="replace")}

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight OPTIONS request."""
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for static UI assets and REST API endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # ---------------------------------------------------------------------
        # REST API Routes
        # ---------------------------------------------------------------------
        if path == "/api/stats" or path == "/api/diagnostics":
            self._handle_api_diagnostics()
            return

        if path == "/api/palettes":
            self._handle_api_list_palettes()
            return

        if path.startswith("/api/palettes/"):
            pal_name = path[len("/api/palettes/") :]
            self._handle_api_get_palette(pal_name)
            return

        if path == "/api/check":
            fg = query.get("fg", ["#1a73e8"])[0]
            bg = query.get("bg", ["#ffffff"])[0]
            self._handle_api_check(fg, bg)
            return

        if path == "/api/apca":
            fg = query.get("fg", ["#1a73e8"])[0]
            bg = query.get("bg", ["#ffffff"])[0]
            self._handle_api_apca(fg, bg)
            return

        if path == "/api/simulate":
            fg = query.get("fg", ["#1a73e8"])[0]
            bg = query.get("bg", ["#ffffff"])[0]
            deficiency = query.get("deficiency", [None])[0]
            self._handle_api_simulate(fg, bg, deficiency)
            return

        if path == "/api/suggest":
            fg = query.get("fg", ["#1a73e8"])[0]
            bg = query.get("bg", ["#ffffff"])[0]
            ratio = float(query.get("target_ratio", query.get("ratio", [4.5]))[0])
            adjust = query.get("adjust", ["foreground"])[0]
            self._handle_api_suggest(fg, bg, ratio, adjust)
            return

        # ---------------------------------------------------------------------
        # Static Assets & Studio UI
        # ---------------------------------------------------------------------
        if path in ("/", "/index.html", "/studio"):
            self._serve_studio_ui()
            return

        # Serve static file from public_dir if available
        if self.public_dir and (self.public_dir / path.lstrip("/")).is_file():
            self._serve_static_file(self.public_dir / path.lstrip("/"))
            return

        self._send_error(f"Route '{path}' not found", status=404)

    def do_POST(self) -> None:
        """Handle POST requests for REST API endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._read_json_body()

        if path == "/api/check":
            fg = body.get("fg") or body.get("foreground") or "#1a73e8"
            bg = body.get("bg") or body.get("background") or "#ffffff"
            self._handle_api_check(fg, bg)
            return

        if path == "/api/apca":
            fg = body.get("fg") or body.get("foreground") or "#1a73e8"
            bg = body.get("bg") or body.get("background") or "#ffffff"
            self._handle_api_apca(fg, bg)
            return

        if path == "/api/simulate":
            fg = body.get("fg") or body.get("foreground") or "#1a73e8"
            bg = body.get("bg") or body.get("background") or "#ffffff"
            deficiency = body.get("deficiency")
            self._handle_api_simulate(fg, bg, deficiency)
            return

        if path == "/api/suggest":
            fg = body.get("fg") or body.get("foreground") or "#1a73e8"
            bg = body.get("bg") or body.get("background") or "#ffffff"
            ratio = float(body.get("target_ratio") or body.get("ratio") or 4.5)
            adjust = body.get("adjust") or "foreground"
            self._handle_api_suggest(fg, bg, ratio, adjust)
            return

        if path == "/api/audit-palette":
            palette_name = body.get("name") or body.get("palette") or "google-material-3"
            ratio = float(body.get("target_ratio") or body.get("min_ratio") or 4.5)
            custom_colors = body.get("colors")
            if custom_colors and isinstance(custom_colors, dict):
                report = audit_custom_palette(palette_name, custom_colors, min_ratio=ratio)
                self._send_json(report.to_dict())
            else:
                try:
                    report = audit_palette(palette_name, min_ratio=ratio)
                    self._send_json(report.to_dict())
                except KeyError as err:
                    self._send_error(str(err), status=404)
            return

        if path == "/api/scan-css":
            css_code = body.get("css") or body.get("raw") or ""
            default_bg = body.get("default_bg") or "#ffffff"
            scan_res = scan_css_string(css_code, default_bg=default_bg)
            self._send_json(scan_res.to_dict())
            return

        if path == "/api/palettes":
            self._handle_api_list_palettes()
            return

        if path == "/api/diagnostics":
            self._handle_api_diagnostics()
            return

        self._send_error(f"POST route '{path}' not found", status=404)

    # -------------------------------------------------------------------------
    # Route Handlers
    # -------------------------------------------------------------------------
    def _handle_api_diagnostics(self) -> None:
        """Return comprehensive system and engine diagnostics."""
        diag = {
            "success": True,
            "application": "Google WCAG & APCA Contrast Guard Studio",
            "version": "0.1.0",
            "platform": get_platform_info(),
            "supported_standards": ["WCAG 2.1", "WCAG 2.2", "APCA-W3 0.98G-4g", "CIEDE2000"],
            "supported_deficiencies": [d.value for d in ColorblindType],
            "palettes_count": len(list_palettes()),
            "palettes": list_palettes(),
        }
        self._send_json(diag)

    def _handle_api_list_palettes(self) -> None:
        """Return all supported design system palettes with their colors."""
        res = {}
        for pal in list_palettes():
            res[pal] = get_palette(pal)
        self._send_json({"success": True, "palettes": res})

    def _handle_api_get_palette(self, name: str) -> None:
        """Return color dictionary for a single named palette."""
        try:
            colors = get_palette(name)
            self._send_json({"success": True, "palette": name, "colors": colors})
        except KeyError as err:
            self._send_error(str(err), status=404)

    def _handle_api_check(self, fg: str, bg: str) -> None:
        """Evaluate WCAG 2.1/2.2 contrast ratio."""
        try:
            res = evaluate_wcag(fg, bg)
            self._send_json(res.to_dict())
        except Exception as err:
            self._send_error(f"Failed to check contrast: {err}")

    def _handle_api_apca(self, fg: str, bg: str) -> None:
        """Evaluate APCA contrast."""
        try:
            res = evaluate_apca(fg, bg)
            self._send_json(res.to_dict())
        except Exception as err:
            self._send_error(f"Failed to calculate APCA: {err}")

    def _handle_api_simulate(self, fg: str, bg: str, deficiency: Optional[str]) -> None:
        """Run colorblindness simulation."""
        try:
            if deficiency and deficiency.lower() != "all":
                res = simulate_colorblindness(fg, bg, deficiency)
                self._send_json(res.to_dict())
            else:
                sims = simulate_all_deficiencies(fg, bg)
                self._send_json({"simulations": [s.to_dict() for s in sims]})
        except Exception as err:
            self._send_error(f"Failed to simulate colorblindness: {err}")

    def _handle_api_suggest(self, fg: str, bg: str, ratio: float, adjust: str) -> None:
        """Calculate CIEDE2000 minimal perceptual shift remediation."""
        try:
            res = remediate_contrast(fg, bg, target_ratio=ratio, adjust=adjust)
            self._send_json(res.to_dict())
        except Exception as err:
            self._send_error(f"Failed to remediate color: {err}")

    def _serve_studio_ui(self) -> None:
        """Serve public/index.html or embedded fallback."""
        candidates = []
        if self.public_dir:
            candidates.append(self.public_dir / "index.html")

        # Check repository root public/index.html
        root_public = Path(__file__).resolve().parent.parent.parent / "public" / "index.html"
        candidates.append(root_public)

        # Check package bundled directory
        pkg_public = Path(__file__).resolve().parent / "public" / "index.html"
        candidates.append(pkg_public)

        for cand in candidates:
            if cand.is_file():
                try:
                    html_content = read_text_safe(cand)
                    self._send_text(html_content, content_type="text/html; charset=utf-8")
                    return
                except Exception:
                    pass

        # Fallback to embedded HTML
        self._send_text(EMBEDDED_STUDIO_HTML, content_type="text/html; charset=utf-8")

    def _serve_static_file(self, file_path: Path) -> None:
        """Serve a static file with appropriate MIME type."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as err:
            self._send_error(f"Failed to read static asset: {err}", status=500)


def create_ui_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    public_dir: Optional[Union[str, Path]] = None,
    quiet: bool = False,
) -> socketserver.ThreadingTCPServer:
    """Create a multi-threaded HTTP server configured for Google WCAG Studio.

    Args:
        host: Host IP or hostname to bind.
        port: TCP port to listen on.
        public_dir: Optional custom directory path containing static files.
        quiet: If True, suppress stdout/stderr access logging.

    Returns:
        socketserver.ThreadingTCPServer: Configured, bound HTTP server instance.
    """
    resolved_pub_dir = Path(public_dir).resolve() if public_dir else None

    def handler_factory(*args: Any, **kwargs: Any) -> StudioHTTPRequestHandler:
        return StudioHTTPRequestHandler(*args, public_dir=resolved_pub_dir, quiet=quiet, **kwargs)

    # Enable SO_REUSEADDR for rapid restart without TIME_WAIT errors
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((host, port), handler_factory)
    return server


def start_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    open_browser: bool = False,
    public_dir: Optional[Union[str, Path]] = None,
    block: bool = True,
    quiet: bool = False,
) -> Tuple[socketserver.ThreadingTCPServer, Optional[threading.Thread]]:
    """Start the WCAG Studio HTTP server.

    Args:
        host: Host address (default '127.0.0.1').
        port: TCP port (default 8080).
        open_browser: If True, automatically open the default web browser.
        public_dir: Optional directory with public assets.
        block: If True, blocks on server.serve_forever(). If False, runs in background thread.
        quiet: If True, suppresses terminal logs.

    Returns:
        Tuple[ThreadingTCPServer, Optional[Thread]]: The server and background thread (if non-blocking).
    """
    server = create_ui_server(host=host, port=port, public_dir=public_dir, quiet=quiet)
    url = f"http://{host}:{port}/"

    if not quiet:
        print("=" * 70)
        print("  Google WCAG Contrast Guard Studio & REST API Server")
        print(f"  URL: {url}")
        print("  Press Ctrl+C to stop the server.")
        print("=" * 70)

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    if block:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            if not quiet:
                print("\nShutting down studio server...")
            server.shutdown()
            server.server_close()
        return server, None
    else:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread


def main() -> None:
    """Entry point for running ui_server directly via `python -m wcag_contrast_guard.ui_server`."""
    import argparse

    parser = argparse.ArgumentParser(description="Google WCAG Contrast Guard Studio Web UI & REST API")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port number (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (suppress logs)")

    args = parser.parse_args()
    start_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        quiet=args.quiet,
        block=True,
    )


if __name__ == "__main__":
    main()
