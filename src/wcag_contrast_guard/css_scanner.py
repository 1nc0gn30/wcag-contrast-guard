"""Pure Python CSS and HTML color scanner and pair extractor.

Extracts CSS custom properties (variables), CSS rules with foreground and background
declarations, HTML inline styles, and constructs accessible color pairs with automated
WCAG contrast evaluation.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from wcag_contrast_guard.color_math import NAMED_CSS_COLORS, parse_color
from wcag_contrast_guard.compat import read_text_safe
from wcag_contrast_guard.models import Color
from wcag_contrast_guard.wcag_engine import calculate_contrast_ratio


@dataclass
class CSSRule:
    """Parsed CSS rule block."""

    selector: str
    properties: Dict[str, str]
    line_number: int


@dataclass
class CSSColorPair:
    """Identified foreground and background color pair from CSS."""

    selector: str
    fg_raw: str
    bg_raw: str
    fg_color: Optional[Color]
    bg_color: Optional[Color]
    line_number: int
    wcag_ratio: Optional[float] = None
    passes_aa: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pair to serializable dictionary."""
        return {
            "selector": self.selector,
            "fg_raw": self.fg_raw,
            "bg_raw": self.bg_raw,
            "fg_color": self.fg_color.to_dict() if self.fg_color else None,
            "bg_color": self.bg_color.to_dict() if self.bg_color else None,
            "line_number": self.line_number,
            "wcag_ratio": self.wcag_ratio,
            "passes_aa": self.passes_aa,
        }


@dataclass
class CSSScanResult:
    """Aggregate result from scanning CSS stylesheet or HTML source."""

    variables: Dict[str, str] = field(default_factory=dict)
    rules: List[CSSRule] = field(default_factory=list)
    color_pairs: List[CSSColorPair] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def failing_pairs(self) -> List[CSSColorPair]:
        """Return list of pairs failing WCAG AA standard."""
        return [p for p in self.color_pairs if p.passes_aa is False]

    @property
    def passing_pairs(self) -> List[CSSColorPair]:
        """Return list of pairs passing WCAG AA standard."""
        return [p for p in self.color_pairs if p.passes_aa is True]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "variables_count": len(self.variables),
            "rules_count": len(self.rules),
            "pairs_count": len(self.color_pairs),
            "failing_pairs_count": len(self.failing_pairs),
            "variables": self.variables,
            "color_pairs": [p.to_dict() for p in self.color_pairs],
            "errors": self.errors,
        }


# -------------------------------------------------------------------------
# Regex Matchers
# -------------------------------------------------------------------------
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_VAR_DEF_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;{}]+);", re.MULTILINE)
_RULE_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]+)\}", re.DOTALL)
_VAR_USAGE_RE = re.compile(r"var\(\s*(--[\w-]+)(?:\s*,\s*([^)]+))?\s*\)")
_INLINE_STYLE_RE = re.compile(r'style=["\']([^"\']+)["\']', re.IGNORECASE)
_HTML_STYLE_TAG_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)


def _strip_comments_preserving_lines(css: str) -> str:
    """Strip CSS comments while replacing comment bodies with newlines to keep line numbers intact."""
    def replacer(match: re.Match) -> str:
        newlines_count = match.group(0).count("\n")
        return "\n" * newlines_count

    return _COMMENT_RE.sub(replacer, css)


def resolve_css_variables(value: str, variables: Dict[str, str], max_depth: int = 5) -> str:
    """Recursively resolve var(--name, fallback) references using collected CSS variables."""
    current = value.strip()
    depth = 0

    while "var(" in current and depth < max_depth:
        depth += 1
        changed = False

        def repl(match: re.Match) -> str:
            nonlocal changed
            var_name = match.group(1).strip()
            fallback = match.group(2).strip() if match.group(2) else ""
            if var_name in variables:
                changed = True
                return variables[var_name]
            elif fallback:
                changed = True
                return fallback
            return match.group(0)

        new_val = _VAR_USAGE_RE.sub(repl, current)
        if not changed:
            break
        current = new_val

    return current


def _extract_color_from_declaration(decl_value: str) -> Optional[str]:
    """Attempt to extract color string from declaration value (handling backgrounds)."""
    val = decl_value.strip().rstrip("!important").strip()

    # Direct match for hex, rgb, hsl, or named colors
    tokens = val.split()
    for token in tokens:
        clean_token = token.strip(",;")
        # Check if clean_token starts with # or rgb/hsl
        if clean_token.startswith("#") or clean_token.startswith("rgb") or clean_token.startswith("hsl"):
            return clean_token
        if clean_token.lower() in NAMED_CSS_COLORS and clean_token.lower() != "transparent":
            return clean_token

    # If entire val is parseable
    try:
        parse_color(val)
        return val
    except Exception:
        pass

    return None


def scan_css_string(
    css_content: str,
    default_bg: str = "#ffffff",
) -> CSSScanResult:
    """Scan and parse a CSS stylesheet string for colors and contrast pairs.

    Args:
        css_content: Raw CSS content.
        default_bg: Fallback background color when rule only defines foreground.

    Returns:
        CSSScanResult: Discovered variables, rules, and evaluated color pairs.
    """
    cleaned_css = _strip_comments_preserving_lines(css_content)
    result = CSSScanResult()

    # Pass 1: Extract all CSS variables (--primary: #123456;)
    for match in _VAR_DEF_RE.finditer(cleaned_css):
        var_name = match.group(1).strip()
        var_val = match.group(2).strip().rstrip("!important").strip()
        result.variables[var_name] = var_val

    # Resolve variables against each other
    for var_name, var_val in list(result.variables.items()):
        result.variables[var_name] = resolve_css_variables(var_val, result.variables)

    # Pass 2: Extract CSS rules and selectors
    for match in _RULE_BLOCK_RE.finditer(cleaned_css):
        raw_selector = match.group(1).strip()
        body = match.group(2).strip()
        # Find line number
        line_num = cleaned_css[: match.start()].count("\n") + 1

        # Skip @media, @keyframes container headers if empty
        if raw_selector.startswith("@keyframes") or raw_selector.startswith("@font-face"):
            continue

        props: Dict[str, str] = {}
        for decl in body.split(";"):
            decl = decl.strip()
            if not decl or ":" not in decl:
                continue
            k, _, v = decl.partition(":")
            prop_name = k.strip().lower()
            prop_val = resolve_css_variables(v.strip(), result.variables)
            props[prop_name] = prop_val

        rule = CSSRule(selector=raw_selector, properties=props, line_number=line_num)
        result.rules.append(rule)

        # Look for color properties
        fg_raw = props.get("color")
        bg_raw = props.get("background-color") or props.get("background")

        if fg_raw or bg_raw:
            fg_val = _extract_color_from_declaration(fg_raw) if fg_raw else None
            bg_val = _extract_color_from_declaration(bg_raw) if bg_raw else default_bg

            # If only fg is set, use default_bg
            if fg_val and not bg_val:
                bg_val = default_bg

            # If both are valid, parse and evaluate
            if fg_val and bg_val:
                try:
                    fg_c = parse_color(fg_val)
                except Exception as err:
                    result.errors.append(f"Line {line_num}: Failed to parse fg color '{fg_val}': {err}")
                    fg_c = None

                try:
                    bg_c = parse_color(bg_val)
                except Exception as err:
                    result.errors.append(f"Line {line_num}: Failed to parse bg color '{bg_val}': {err}")
                    bg_c = None

                ratio = None
                passes = None
                if fg_c and bg_c:
                    ratio = calculate_contrast_ratio(fg_c, bg_c)
                    passes = ratio >= 4.5

                pair = CSSColorPair(
                    selector=raw_selector,
                    fg_raw=fg_raw or fg_val,
                    bg_raw=bg_raw or bg_val,
                    fg_color=fg_c,
                    bg_color=bg_c,
                    line_number=line_num,
                    wcag_ratio=ratio,
                    passes_aa=passes,
                )
                result.color_pairs.append(pair)

    return result


def scan_css_file(
    file_path: Union[str, Path],
    default_bg: str = "#ffffff",
) -> CSSScanResult:
    """Scan a CSS file on disk.

    Args:
        file_path: Path to the .css file.
        default_bg: Fallback background color.

    Returns:
        CSSScanResult: Scan findings.
    """
    content = read_text_safe(file_path)
    return scan_css_string(content, default_bg=default_bg)


def scan_html_inline_styles(
    html_content: str,
    default_bg: str = "#ffffff",
) -> CSSScanResult:
    """Scan an HTML document for embedded `<style>` blocks and `style="..."` inline attributes.

    Args:
        html_content: HTML source code string.
        default_bg: Fallback background color.

    Returns:
        CSSScanResult: Extracted variables and color pairs.
    """
    aggregate = CSSScanResult()

    # 1. Process <style> blocks
    for match in _HTML_STYLE_TAG_RE.finditer(html_content):
        css_block = match.group(1)
        sub_res = scan_css_string(css_block, default_bg=default_bg)
        aggregate.variables.update(sub_res.variables)
        aggregate.rules.extend(sub_res.rules)
        aggregate.color_pairs.extend(sub_res.color_pairs)
        aggregate.errors.extend(sub_res.errors)

    # 2. Process inline style attributes
    for match in _INLINE_STYLE_RE.finditer(html_content):
        style_decl = match.group(1).strip()
        line_num = html_content[: match.start()].count("\n") + 1
        dummy_css = f"inline[line={line_num}] {{ {style_decl} }}"
        sub_res = scan_css_string(dummy_css, default_bg=default_bg)
        aggregate.rules.extend(sub_res.rules)
        aggregate.color_pairs.extend(sub_res.color_pairs)

    return aggregate


def extract_css_colors(css_content: str) -> List[str]:
    """Extract all distinct raw color strings mentioned in a CSS snippet.

    Args:
        css_content: CSS text.

    Returns:
        List[str]: Unique list of color strings found.
    """
    cleaned = _strip_comments_preserving_lines(css_content)
    colors = set()

    # Find hex codes
    for hex_m in re.finditer(r"#(?:[0-9a-fA-F]{3,8})\b", cleaned):
        colors.add(hex_m.group(0))

    # Find rgb/rgba/hsl/hsla
    for func_m in re.finditer(r"(?:rgba?|hsla?)\([^)]+\)", cleaned, re.IGNORECASE):
        colors.add(func_m.group(0))

    # Find named colors
    for word_m in re.finditer(r"\b[a-zA-Z]+\b", cleaned):
        w = word_m.group(0).lower()
        if w in NAMED_CSS_COLORS and w != "transparent":
            colors.add(w)

    return sorted(list(colors))
