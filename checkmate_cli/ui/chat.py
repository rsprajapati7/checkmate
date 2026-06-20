"""
CheckMate CLI — Streaming chat panel for Local LLM responses.

Port of ChatPanel.tsx — streaming cursor indicator, Rich Markdown rendering
of completed responses, bordered panel with Local LLM Assistant header.
"""

from __future__ import annotations

from typing import Generator, Iterable

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from checkmate_cli.theme import HEX_GOLD, HEX_SAGE, HEX_SLATE


def stream_chat_response(
    console:  Console,
    chunks:   Iterable[str],
    heading:  str = "Local LLM Assistant",
) -> str:
    """
    Stream tokens from an iterable into a Rich Live panel.
    Shows a live blinking cursor (▌) while streaming.
    Returns the full accumulated response string.
    """
    accumulated = ""

    def _render_panel(content: str, streaming: bool) -> Panel:
        header = Text()
        header.append(f"-- {heading}", style=f"bold {HEX_GOLD}")
        if streaming:
            header.append("  generating...", style=f"dim {HEX_SLATE}")

        if not content.strip():
            body = Text("Thinking...", style=f"italic {HEX_SLATE}")
        elif streaming:
            body = Text()
            body.append(content, style="white")
            body.append("▌", style=f"bold {HEX_SAGE}")
        else:
            body = Markdown(content)

        return Panel(body, title=header, title_align="left", border_style=HEX_SAGE, padding=(0, 1))

    with Live(
        _render_panel("", streaming=True),
        console=console,
        refresh_per_second=15,
        transient=False,
    ) as live:
        for chunk in chunks:
            accumulated += chunk
            live.update(_render_panel(accumulated, streaming=True))

        # Final render — full markdown
        live.update(_render_panel(accumulated, streaming=False))

    return accumulated


def stream_ai_summary(
    console: Console,
    chunks:  Iterable[str],
) -> str:
    """Stream an AI forensic summary with a gold-bordered panel."""
    accumulated = ""

    def _render_panel(content: str, streaming: bool) -> Panel:
        header = Text()
        header.append("-- AI FORENSIC REPORT", style=f"bold {HEX_GOLD}")
        if streaming:
            header.append("  generating...", style=f"dim {HEX_SLATE}")

        if not content.strip():
            body = Text("Analyzing findings...", style=f"italic {HEX_SLATE}")
        elif streaming:
            body = Text()
            body.append(content, style="white")
            body.append("▌", style=f"bold {HEX_SAGE}")
        else:
            body = Markdown(content)

        return Panel(body, title=header, title_align="left", border_style=HEX_GOLD, padding=(0, 1))

    with Live(
        _render_panel("", streaming=True),
        console=console,
        refresh_per_second=15,
        transient=False,
    ) as live:
        for chunk in chunks:
            accumulated += chunk
            live.update(_render_panel(accumulated, streaming=True))

        live.update(_render_panel(accumulated, streaming=False))

    return accumulated
