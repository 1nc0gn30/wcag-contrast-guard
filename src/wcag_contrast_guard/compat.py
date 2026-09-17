"""Cross-platform compatibility utilities for wcag-contrast-guard.

Provides atomic file operations, robust path normalization across Linux, macOS,
Windows, and Termux environments, safe encodings, and platform introspection.
Zero external dependencies (pure Python standard library).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class PlatformInfo:
    """System platform information and environment capabilities."""

    system: str
    release: str
    machine: str
    python_version: str
    is_windows: bool
    is_macos: bool
    is_linux: bool
    is_termux: bool
    default_encoding: str
    path_separator: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert platform info to a serializable dictionary."""
        return {
            "system": self.system,
            "release": self.release,
            "machine": self.machine,
            "python_version": self.python_version,
            "is_windows": self.is_windows,
            "is_macos": self.is_macos,
            "is_linux": self.is_linux,
            "is_termux": self.is_termux,
            "default_encoding": self.default_encoding,
            "path_separator": self.path_separator,
        }


def get_platform_info() -> PlatformInfo:
    """Detect current operating system, runtime architecture, and platform quirks.

    Returns:
        PlatformInfo: Comprehensive dataclass describing the runtime platform.
    """
    sys_name = platform.system().lower()
    is_win = sys_name == "windows"
    is_mac = sys_name == "darwin"
    is_lin = sys_name == "linux"

    # Termux detection via environment markers or prefix paths
    is_termux = False
    if is_lin:
        prefix = os.environ.get("PREFIX", "")
        termux_ver = os.environ.get("TERMUX_VERSION", "")
        if "com.termux" in prefix or "com.termux" in sys.prefix or bool(termux_ver):
            is_termux = True

    encoding = sys.getdefaultencoding() or "utf-8"

    return PlatformInfo(
        system=platform.system(),
        release=platform.release(),
        machine=platform.machine(),
        python_version=platform.python_version(),
        is_windows=is_win,
        is_macos=is_mac,
        is_linux=is_lin,
        is_termux=is_termux,
        default_encoding=encoding,
        path_separator=os.sep,
    )


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize and resolve a filesystem path across different OS environments.

    Handles user home expansion (~), environment variables, backslash/slash
    cross-compatibility, and symlink resolution.

    Args:
        path: Path string or Path object.

    Returns:
        Path: Fully resolved and normalized Path object.
    """
    path_str = str(path).strip()
    # Expand environment variables like $HOME or %USERPROFILE%
    path_str = os.path.expandvars(path_str)
    # Expand user directory ~
    path_str = os.path.expanduser(path_str)
    # Convert and resolve
    p = Path(path_str)
    try:
        return p.resolve()
    except (OSError, RuntimeError):
        # Fallback for virtual or non-existing paths
        return p.absolute()


def atomic_write_text(
    path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    make_parents: bool = True,
) -> Path:
    """Write text content to a file atomically with fsync and safe rename.

    Ensures that partially written files never corrupt destination state.

    Args:
        path: Destination target path.
        content: Text content to write.
        encoding: Text encoding (default utf-8).
        make_parents: Automatically create parent directories if missing.

    Returns:
        Path: Normalized destination path.
    """
    dest_path = normalize_path(path)
    parent_dir = dest_path.parent

    if make_parents and not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    temp_file = None
    try:
        # Create temp file in the same directory to allow atomic rename across filesystems
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=str(parent_dir),
            delete=False,
            prefix=".tmp_wcag_",
            suffix=".tmp",
        )
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Atomic replace
        os.replace(temp_path, dest_path)
        return dest_path
    except Exception:
        if temp_file is not None:
            try:
                temp_file.close()
            except Exception:
                pass
            tmp_p = Path(temp_file.name)
            if tmp_p.exists():
                try:
                    tmp_p.unlink()
                except Exception:
                    pass
        raise


def atomic_write_bytes(
    path: Union[str, Path],
    content: bytes,
    make_parents: bool = True,
) -> Path:
    """Write binary content to a file atomically with fsync and safe rename.

    Args:
        path: Destination target path.
        content: Binary bytes to write.
        make_parents: Automatically create parent directories if missing.

    Returns:
        Path: Normalized destination path.
    """
    dest_path = normalize_path(path)
    parent_dir = dest_path.parent

    if make_parents and not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode="wb",
            dir=str(parent_dir),
            delete=False,
            prefix=".tmp_wcag_bin_",
            suffix=".tmp",
        )
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_path = Path(temp_file.name)
        temp_file.close()

        os.replace(temp_path, dest_path)
        return dest_path
    except Exception:
        if temp_file is not None:
            try:
                temp_file.close()
            except Exception:
                pass
            tmp_p = Path(temp_file.name)
            if tmp_p.exists():
                try:
                    tmp_p.unlink()
                except Exception:
                    pass
        raise


def read_text_safe(
    path: Union[str, Path],
    default: Optional[str] = None,
    encodings: Sequence[str] = ("utf-8", "utf-8-sig", "latin-1", "cp1252"),
) -> str:
    """Read a text file trying multiple fallback encodings gracefully.

    Args:
        path: Path to file.
        default: Optional fallback string if file is missing or unreadable.
        encodings: Sequence of character encodings to attempt in order.

    Returns:
        str: File content.

    Raises:
        FileNotFoundError: If file not found and default is None.
        UnicodeDecodeError: If all encodings fail and default is None.
    """
    dest_path = normalize_path(path)
    if not dest_path.is_file():
        if default is not None:
            return default
        raise FileNotFoundError(f"File not found: {dest_path}")

    last_error: Optional[Exception] = None
    for enc in encodings:
        try:
            with open(dest_path, mode="r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as err:
            last_error = err
            continue
        except Exception as err:
            last_error = err
            break

    if default is not None:
        return default
    if last_error:
        raise last_error
    raise RuntimeError(f"Unable to read file {dest_path}")


def read_json_safe(
    path: Union[str, Path],
    default: Any = None,
    encodings: Sequence[str] = ("utf-8", "utf-8-sig", "latin-1"),
) -> Any:
    """Read and deserialize JSON file with fallback encodings.

    Args:
        path: Path to JSON file.
        default: Fallback object if file missing or invalid.
        encodings: Encodings to attempt.

    Returns:
        Any: Parsed JSON structure or default.
    """
    try:
        content = read_text_safe(path, default=None, encodings=encodings)
        return json.loads(content)
    except Exception:
        if default is not None:
            return default
        raise


def write_json_safe(
    path: Union[str, Path],
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """Serialize and write data to a JSON file atomically.

    Args:
        path: Target file path.
        data: Data to serialize.
        indent: JSON indentation spaces.
        ensure_ascii: Escape non-ASCII characters if True.

    Returns:
        Path: Destination path.
    """
    json_str = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii) + "\n"
    return atomic_write_text(path, json_str, encoding="utf-8")


def safe_delete_file(path: Union[str, Path]) -> bool:
    """Safely delete a file if it exists without raising errors.

    Args:
        path: Path to file.

    Returns:
        bool: True if file existed and was removed, False otherwise.
    """
    try:
        p = normalize_path(path)
        if p.is_file() or p.is_symlink():
            p.unlink()
            return True
        return False
    except OSError:
        return False


def safe_delete_dir(path: Union[str, Path], recursive: bool = True) -> bool:
    """Safely delete a directory if it exists.

    Args:
        path: Path to directory.
        recursive: Remove subdirectories and files if True.

    Returns:
        bool: True if removed, False otherwise.
    """
    try:
        p = normalize_path(path)
        if p.is_dir():
            if recursive:
                shutil.rmtree(p)
            else:
                p.rmdir()
            return True
        return False
    except OSError:
        return False
