"""
CheckMate CLI — Diagnostic results table.

Port of DiagnosticTable.tsx — risk summary + per-engine rows + embedded assets.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

from checkmate_cli.api import ScanResponse
from checkmate_cli.theme import (
    HEX_GOLD, HEX_CORAL, HEX_SAGE, HEX_CRIMSON, HEX_SLATE, HEX_SAND,
    score_style, risk_tier_style,
)


def _score_bar(score: float, total: int = 10) -> Text:
    """Return a color-coded █/░ progress bar as Rich Text."""
    filled = min(total, max(0, round((score / 100) * total)))
    empty  = total - filled

    bar_color = HEX_CRIMSON if score >= 70 else HEX_CORAL if score >= 30 else HEX_SAGE

    t = Text()
    t.append("█" * filled, style=bar_color)
    t.append("░" * empty,  style=HEX_SLATE)
    return t


def _pipeline_panel(name: str, data: dict, console: Console) -> None:
    """Render a single pipeline row as a bordered panel."""
    score = float(data.get("score", 0))
    flags = data.get("flags", [])

    # Header row: name + score bar + score value
    header = Text()
    header.append(name, style="bold white")

    score_text = Text()
    score_text.append("[ ", style=HEX_SLATE)
    score_text.append_text(_score_bar(score))
    score_text.append(" ]", style=HEX_SLATE)
    score_text.append(f" {score:.1f}/100", style=score_style(score))

    # Extra fields (seal-specific)
    extra_rows = []
    if "seals_found" in data:
        suspicious = data.get("suspicious", 0)
        sus_color  = HEX_CORAL if suspicious > 0 else HEX_SAGE
        extra_rows.append(
            f"[{HEX_SLATE}]Official Seals:[/{HEX_SLATE}] [white]{data['seals_found']}[/white]  "
            f"[{HEX_SLATE}]Suspicious:[/{HEX_SLATE}] [{sus_color}]{suspicious}[/{sus_color}]"
        )

    # Flag rows
    flag_color = "yellow" if score >= 50 else HEX_SLATE
    flag_lines = [f"  > {f}" for f in flags] if flags else ["  (no anomalies detected)"]
    flag_style = flag_color if flags else f"italic {HEX_SLATE}"

    content = Text()
    content.append_text(score_text)
    content.append("\n")

    for ex in extra_rows:
        console.print(f"  {ex}")

    for fl in flag_lines:
        content.append(fl + "\n", style=flag_style if flags else f"italic {HEX_SLATE}")

    panel = Panel(
        content,
        title=Text(name, style="bold white"),
        title_align="left",
        border_style=HEX_SLATE,
        padding=(0, 1),
    )
    console.print(panel)


def print_diagnostic_table(console: Console, results: ScanResponse) -> None:
    """Print the full diagnostic table for a completed scan."""

    tier_style, tier_label = risk_tier_style(results.risk_tier)

    # ── Risk summary panel ───────────────────────────────────────────────────
    summary = Text()
    summary.append(f"File Name:      ", style="white")
    summary.append(f"{results.filename}\n", style=f"bold {HEX_GOLD}")
    summary.append(f"File Type:      ", style="white")
    summary.append(f"{results.file_type}", style=HEX_SAND)
    summary.append(f"  ({results.page_count} page{'s' if results.page_count != 1 else ''})\n", style=HEX_SLATE)
    summary.append(f"Classification: ", style="white")
    doc_class = "Scanned Document (Image-only)" if results.is_scanned else "Digital Native PDF"
    summary.append(f"{doc_class}\n\n", style=HEX_SAND)
    summary.append("FORENSIC THREAT INDEX:  ", style="bold white")
    summary.append(f"{results.final_score:.1f} / 100", style=tier_style)

    risk_header = Text()
    risk_header.append("-- DOCUMENT SCAN REPORT", style="bold white")

    console.print()
    console.print(Panel(
        summary,
        title=risk_header,
        title_align="left",
        border_style=HEX_GOLD,
        box=box.DOUBLE,
        padding=(1, 2),
    ))

    # ── Engine diagnostics ───────────────────────────────────────────────────
    console.print(Text(f"\n-- FORENSIC ENGINE DIAGNOSTICS", style=f"bold {HEX_GOLD}"))

    _pipeline_panel("Error Level Analysis (ELA)", results.ela,      console)
    _pipeline_panel("Metadata Forensics",          results.metadata, console)
    _pipeline_panel("Seal & Signature Detection",  results.seal,     console)
    _pipeline_panel("NLP Logical Scrutiny",        results.nlp,      console)

    # ── Embedded assets ──────────────────────────────────────────────────────
    console.print(Text(f"\n-- EMBEDDED ASSETS & METADATA", style=f"bold {HEX_GOLD}"))

    assets = Text()
    assets.append("QR Codes:  ", style=f"bold {HEX_SLATE}")
    if results.qr_codes:
        for i, qr in enumerate(results.qr_codes):
            assets.append(f"\n  [{i + 1}] {qr}", style="cyan")
    else:
        assets.append("none extracted", style=f"italic {HEX_SLATE}")

    if results.pdf_metadata:
        assets.append("\n\nPDF Core Properties:\n", style=f"bold {HEX_SLATE}")
        for k, v in list(results.pdf_metadata.items())[:5]:
            assets.append(f"  > {k}: ", style=HEX_SLATE)
            assets.append(f"{v}\n", style="white")

    console.print(Panel(assets, border_style=HEX_SLATE, padding=(0, 1)))
    console.print()
