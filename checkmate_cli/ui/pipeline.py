"""
CheckMate CLI — Animated forensic pipeline progress display.

Port of PipelineProgress.tsx — 6 stages with spinners, checkmarks,
and per-stage descriptions. Uses Rich Progress + Live.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner
from rich.table import Table
from rich import box

from checkmate_cli.theme import HEX_GOLD, HEX_SAGE, HEX_CORAL, HEX_SLATE


@dataclass
class Stage:
    id:           str
    name:         str
    desc:         str
    min_duration: float  # seconds


STAGES: list[Stage] = [
    Stage("ingest", "Document Ingestion",    "Parsing structure and extracting pages",           3.5),
    Stage("ela",    "Error Level Analysis",   "Scanning compression and local noise differences", 3.0),
    Stage("meta",   "Metadata Forensics",     "Analyzing PDF revision history and author tags",   0.8),
    Stage("seal",   "Seal Detection",         "Running YOLO seal and signature detection",        2.5),
    Stage("nlp",    "NLP Cross-Doc Scrutiny", "Checking logical flow and text consistency",       0.8),
    Stage("fusion", "Score Fusion",           "Fusing scores and determining risk tier",          0.5),
]

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def _build_table(
    current_idx:      int,
    completed_ids:    set[str],
    spinner_frame:    int,
) -> Table:
    """Build the stage display table for one render frame."""
    table = Table(box=None, show_header=False, padding=(0, 0), expand=False)
    table.add_column("icon",  no_wrap=True, width=7)
    table.add_column("name",  no_wrap=True)
    table.add_column("desc",  style=HEX_SLATE)

    for i, stage in enumerate(STAGES):
        is_done   = stage.id in completed_ids
        is_active = i == current_idx and not is_done

        if is_done:
            icon       = Text(f"[ OK ]", style=f"bold {HEX_SAGE}")
            name_style = f"bold {HEX_SAGE}"
            desc_style = HEX_SLATE
        elif is_active:
            frame      = SPINNER_FRAMES[spinner_frame % len(SPINNER_FRAMES)]
            icon       = Text(f"  {frame}   ", style=f"bold {HEX_GOLD}")
            name_style = f"bold {HEX_GOLD}"
            desc_style = "white"
        else:
            icon       = Text("  ...  ", style=HEX_SLATE)
            name_style = HEX_SLATE
            desc_style = HEX_SLATE

        table.add_row(
            icon,
            Text(stage.name,  style=name_style),
            Text(stage.desc,  style=desc_style),
        )

    return table


def run_pipeline_progress(
    console:     Console,
    is_done_fn:  Callable[[], bool],
) -> None:
    """
    Display animated pipeline progress while `is_done_fn()` returns False.
    Stages advance at their minimum durations. When `is_done_fn()` returns True,
    remaining stages fast-complete.

    Call this in a thread while the actual API request runs in another.
    """
    header = Text("-- RUNNING FORENSIC PIPELINES\n", style=f"bold {HEX_GOLD}")

    current_idx    = 0
    completed_ids: set[str] = set()
    frame_idx      = 0
    start_of_stage = time.monotonic()

    with Live(console=console, refresh_per_second=12, transient=False) as live:
        while current_idx < len(STAGES):
            stage    = STAGES[current_idx]
            elapsed  = time.monotonic() - start_of_stage
            api_done = is_done_fn()

            can_advance = elapsed >= stage.min_duration
            is_last     = current_idx == len(STAGES) - 1

            if can_advance and (not is_last or api_done):
                completed_ids.add(stage.id)
                current_idx    += 1
                start_of_stage  = time.monotonic()
            elif api_done and can_advance and is_last:
                completed_ids.add(stage.id)
                current_idx += 1

            table = _build_table(current_idx, completed_ids, frame_idx)

            from rich.console import Group
            live.update(Group(header, table))

            frame_idx += 1
            time.sleep(0.083)   # ~12 fps

        # Final frame — all done
        table = _build_table(len(STAGES), completed_ids | {s.id for s in STAGES}, frame_idx)
        from rich.console import Group
        live.update(Group(header, table))
        time.sleep(0.3)
