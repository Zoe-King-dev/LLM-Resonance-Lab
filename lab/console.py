"""Shared Rich console singleton + small helper functions.

Windows compatibility:
  Chinese Windows defaults to GBK (cp936) for stdout/stderr, which can't encode
  the Unicode characters Rich uses (✓ ✗ →). On Python 3.7+, `sys.stdout` has a
  `reconfigure()` method we can call to switch to UTF-8 transparently. If that
  fails (older Python, redirected pipe that's already open), we fall back to
  ASCII-safe glyphs so the CLI still produces readable output.
"""

from __future__ import annotations

import sys

from rich.console import Console

# Try to switch the stdout/stderr streams to UTF-8. On modern Python (3.7+)
# this works even on Windows. If the stream is already wrapped (e.g. by a
# parent process capturing output) reconfigure may raise — we ignore that.
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _glyph(preferred: str, ascii_fallback: str) -> str:
    """Return `preferred` if stdout can encode it, else `ascii_fallback`."""
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        preferred.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return ascii_fallback
    return preferred


console = Console(safe_box=True)


def success(message: str) -> None:
    check = _glyph("✓", "[OK]")
    console.print(f"[bold green]{check}[/bold green] {message}")


def warning(message: str) -> None:
    bang = _glyph("!", "!")
    console.print(f"[bold yellow]{bang}[/bold yellow] {message}")


def error(message: str) -> None:
    cross = _glyph("✗", "[X]")
    console.print(f"[bold red]{cross}[/bold red] {message}")


def info(message: str) -> None:
    arrow = _glyph("→", "->")
    console.print(f"[blue]{arrow}[/blue] {message}")