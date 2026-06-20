"""
CheckMate CLI — System diagnostics display.

Port of StatusCheck.tsx — checks backend health, starts local server
if needed, shows connection status with Rich Live animation.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner

from checkmate_cli.api import (
    API_URL,
    HealthResponse,
    health_check_sync,
    start_server,
)
from checkmate_cli.theme import HEX_GOLD, HEX_SAGE, HEX_CRIMSON, HEX_CORAL, HEX_SLATE


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def _is_local() -> bool:
    return "localhost" in API_URL or "127.0.0.1" in API_URL


def run_status_check(console: Console) -> Optional[HealthResponse]:
    """
    Run system diagnostics:
    1. Check health endpoint
    2. If local + not running, auto-start uvicorn
    3. Show results

    Returns HealthResponse if healthy, None if offline.
    """
    console.print(
        Text("-- SYSTEM DIAGNOSTICS ────────────────────────", style=f"bold {HEX_GOLD}")
    )

    frame_idx = 0

    def _spinner_text(msg: str) -> Text:
        nonlocal frame_idx
        f = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
        frame_idx += 1
        t = Text()
        t.append(f"  {f}  ", style=f"bold {HEX_GOLD}")
        t.append(msg, style="white")
        return t

    # Step 1 — initial health check
    with Live(console=console, refresh_per_second=10, transient=True) as live:
        import time
        live.update(_spinner_text(
            f"Verifying {'local' if _is_local() else 'remote'} backend at {API_URL}..."
        ))
        health = health_check_sync()

    if not health:
        if _is_local():
            # Try to auto-start server
            log_msgs: list[str] = []

            def on_progress(msg: str) -> None:
                log_msgs.append(msg)

            with Live(console=console, refresh_per_second=10, transient=True) as live:
                import threading

                result: dict = {"success": False}

                def _start():
                    result["success"] = start_server(on_progress)

                t = threading.Thread(target=_start, daemon=True)
                t.start()

                import time
                while t.is_alive():
                    msg = log_msgs[-1] if log_msgs else "Starting backend server..."
                    live.update(_spinner_text(msg))
                    time.sleep(0.1)

            health = health_check_sync()

        else:
            # Remote — retry 3 times
            with Live(console=console, refresh_per_second=10, transient=True) as live:
                import time
                for attempt in range(1, 4):
                    live.update(_spinner_text(
                        f"Connecting to remote backend... (Attempt {attempt}/3)"
                    ))
                    time.sleep(1.5)
                    health = health_check_sync()
                    if health:
                        break

    # ── Display result ───────────────────────────────────────────────────────
    if health:
        db_style  = f"bold {HEX_SAGE}"   if health.db  == "connected"  else f"bold {HEX_CRIMSON}"
        llm_style = f"bold {HEX_SAGE}"   if "ok" in health.llm.lower() else f"bold {HEX_CORAL}"
        db_icon   = "[ OK ]" if health.db  == "connected"  else "[FAIL]"
        llm_icon  = "[ OK ]" if "ok" in health.llm.lower() else "[WARN]"

        console.print(Text(f"[ OK ] Backend Server: {health.version}", style=f"bold {HEX_SAGE}"))
        console.print(Text(f"{db_icon}  Database:       {health.db}",  style=db_style))
        console.print(Text(f"{llm_icon}  Local LLM:      {health.llm}", style=llm_style))
        console.print(Text("All checks passed — entering shell...\n", style=f"{HEX_SAGE}"))

        import time
        time.sleep(0.8)
    else:
        console.print(Text("[FAIL] Connection Failed", style=f"bold {HEX_CRIMSON}"))
        console.print(Text(f"  Could not reach backend at {API_URL}.", style=HEX_SLATE))
        if _is_local():
            console.print(
                Text(f"  Run manually: uvicorn backend.main:app --reload", style=HEX_SLATE)
            )
        else:
            console.print(
                Text("  Verify your network connection and deployment status.", style=HEX_SLATE)
            )
        console.print(
            Text("  Entering offline mode — scan and chat commands are disabled.\n", style=f"italic {HEX_CORAL}")
        )

    return health


def print_status_panel(console: Console, health: Optional[HealthResponse]) -> None:
    """Print a concise status summary (used by /status command in REPL)."""
    console.print(
        Text("-- SYSTEM DIAGNOSTICS ────────────────────────", style=f"bold {HEX_GOLD}")
    )
    if not health:
        health = health_check_sync()

    if health:
        db_style  = f"bold {HEX_SAGE}"  if health.db  == "connected"  else f"bold {HEX_CRIMSON}"
        llm_style = f"bold {HEX_SAGE}"  if "ok" in health.llm.lower() else f"bold {HEX_CORAL}"

        console.print(Text(f"  Backend : {health.version}",  style=f"bold {HEX_SAGE}"))
        console.print(Text(f"  Database: {health.db}",        style=db_style))
        console.print(Text(f"  LLM     : {health.llm}",       style=llm_style))
        console.print(Text(f"  URL     : {API_URL}\n",         style=HEX_SLATE))
    else:
        console.print(Text(f"  Backend unreachable at {API_URL}\n", style=f"bold {HEX_CRIMSON}"))
