"""
CheckMate CLI — Typer application.

Commands
--------
  checkmate                   Launch interactive REPL shell (default)
  checkmate analyze <file>    Direct scan + diagnostic table + auto-report
  checkmate setup             Interactive first-time setup wizard
  checkmate config [key] [v]  Get or set configuration values
"""

from __future__ import annotations

import os
import sys

# Ensure UTF-8 output on Windows before any Rich output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
from pathlib import Path
from typing import Optional

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-16"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf-16"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text

from checkmate_cli import __version__
from checkmate_cli.config import (
    load_config, save_config, get_config_path, VALID_KEYS,
)
from checkmate_cli.theme import (
    CHECKMATE_THEME,
    HEX_GOLD, HEX_CORAL, HEX_SAGE, HEX_CRIMSON, HEX_SLATE, HEX_SAND,
)
from checkmate_cli.ui.banner import print_banner

# ── Typer app ────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="checkmate",
    help="CheckMate / Suraksha 2.0 -- AI-powered document forgery detection CLI.",
    add_completion=False,
    no_args_is_help=False,
    invoke_without_command=True,
)

console = Console(theme=CHECKMATE_THEME, highlight=False)

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"CheckMate CLI v{__version__}")
        raise typer.Exit()


# ── Device flag callback ─────────────────────────────────────────────────────
def _set_device(cpu: bool, gpu: bool, device: str) -> None:
    if cpu:
        os.environ["CHECKMATE_DEVICE"] = "cpu"
    elif gpu:
        os.environ["CHECKMATE_DEVICE"] = "gpu"
    elif device != "auto":
        os.environ["CHECKMATE_DEVICE"] = device


# ── Default command: interactive REPL ────────────────────────────────────────
@app.callback(invoke_without_command=True)
def main(
    ctx:     typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    cpu:     bool = typer.Option(False, "--cpu",    help="Force CPU execution."),
    gpu:     bool = typer.Option(False, "--gpu",    help="Force GPU execution."),
    device:  str  = typer.Option("auto", "--device", help="Device: cpu | gpu | cuda | auto"),
) -> None:
    """Launch the interactive CheckMate forensic shell (REPL)."""
    # If a sub-command was invoked, let it handle execution
    if ctx.invoked_subcommand is not None:
        return

    _set_device(cpu, gpu, device)

    from checkmate_cli.ui.status import run_status_check
    from checkmate_cli.shell import run_shell

    print_banner(console)
    health = run_status_check(console)

    from checkmate_cli.ui.help_menu import print_help
    print_help(console)

    run_shell(console, is_offline=(health is None))


# ── analyze ──────────────────────────────────────────────────────────────────
@app.command()
def analyze(
    file_path: Path = typer.Argument(..., help="Path to the document to analyze."),
    cpu:  bool = typer.Option(False, "--cpu",  help="Force CPU execution."),
    gpu:  bool = typer.Option(False, "--gpu",  help="Force GPU execution."),
    device: str = typer.Option("auto", "--device", help="Device: cpu | gpu | cuda | auto"),
) -> None:
    """Directly scan a document and display the forensic report."""
    _set_device(cpu, gpu, device)

    full_path = file_path.expanduser().resolve()
    if not full_path.exists():
        console.print(Text(f'[FAIL] File not found: "{full_path}"', style=f"bold {HEX_CRIMSON}"))
        raise typer.Exit(1)

    from checkmate_cli.api import scan_document_sync, generate_report_sync, ai_summary_stream_sync
    from checkmate_cli.ui.pipeline import run_pipeline_progress
    from checkmate_cli.ui.diagnostic import print_diagnostic_table
    from checkmate_cli.ui.chat import stream_ai_summary

    import threading

    console.print(Text(f"\n  Scanning {full_path.name} ...\n", style=f"bold {HEX_GOLD}"))

    result_holder: dict = {"result": None, "error": None}
    done_event = threading.Event()

    def _scan():
        try:
            result_holder["result"] = scan_document_sync(str(full_path))
        except Exception as exc:
            result_holder["error"] = str(exc)
        finally:
            done_event.set()

    worker = threading.Thread(target=_scan, daemon=True)
    worker.start()
    run_pipeline_progress(console, is_done_fn=done_event.is_set)
    worker.join()

    if result_holder["error"]:
        console.print(Text(f"[FAIL] Scan failed: {result_holder['error']}", style=f"bold {HEX_CRIMSON}"))
        raise typer.Exit(1)

    results = result_holder["result"]
    print_diagnostic_table(console, results)

    # AI summary
    console.print(Text("  >> Generating AI forensic summary...", style=HEX_SLATE))
    try:
        stream_ai_summary(console, ai_summary_stream_sync(results))
    except Exception as exc:
        console.print(Text(f"[WARN] AI summary unavailable: {exc}", style=f"bold {HEX_CORAL}"))

    # Auto-report
    console.print(Text("  >> Generating forensic report...", style=HEX_SLATE))
    try:
        data, is_pdf = generate_report_sync(results)
        ext      = ".pdf" if is_pdf else ".html"
        out_path = full_path.parent / f"{full_path.stem}_report{ext}"
        out_path.write_bytes(data)
        console.print(Text(f"[ OK ] Report saved: {out_path}", style=f"bold {HEX_SAGE}"))
    except Exception as exc:
        console.print(Text(f"[WARN] Auto-report failed: {exc}", style=f"bold {HEX_CORAL}"))


# ── setup ─────────────────────────────────────────────────────────────────────
@app.command()
def setup() -> None:
    """Interactive first-time setup wizard."""
    print_banner(console)
    console.print(Text("  CheckMate Setup Wizard", style=f"bold {HEX_GOLD}"))
    console.print(Text("  " + "─" * 42, style=HEX_SLATE))
    console.print(Text("  Configure your CheckMate CLI to connect to a backend server.", style="white"))
    console.print(Text("  Press Enter to keep the current value.\n", style=HEX_SLATE))

    cfg = load_config()

    # API URL
    current_url = cfg.get("api_url", "(not set)")
    console.print(Text(f"  Current API URL: {current_url}", style=HEX_SLATE))
    new_url = Prompt.ask(
        f"[bold {HEX_GOLD}]  Backend API URL[/]",
        default="",
        console=console,
    ).strip()
    if new_url:
        cfg["api_url"] = new_url

    console.print()

    # API Key
    current_key = (cfg.get("api_key", "")[:8] + "...") if cfg.get("api_key") else "(not set)"
    console.print(Text(f"  Current API Key: {current_key}", style=HEX_SLATE))
    console.print(Text("  Get a free key at: https://aistudio.google.com/app/apikey", style=HEX_SLATE))
    new_key = Prompt.ask(
        f"[bold {HEX_GOLD}]  Gemini API Key [/]",
        default="",
        password=True,
        console=console,
    ).strip()
    if new_key:
        cfg["api_key"] = new_key

    save_config(cfg)

    console.print()
    console.print(Text("  Configuration saved!", style=f"bold {HEX_SAGE}"))
    console.print(Text(f"  Location: {get_config_path()}", style=HEX_SLATE))
    console.print()
    console.print(Text("  Run  ", style="white"), end="")
    console.print(Text("checkmate", style=f"bold {HEX_GOLD}"), end="")
    console.print(Text("  to start the forensic shell.\n", style="white"))


# ── config ────────────────────────────────────────────────────────────────────
@app.command(name="config")
def config_cmd(
    key:   Optional[str] = typer.Argument(None, help="Config key: api_url | api_key"),
    value: Optional[str] = typer.Argument(None, help="Value to set (omit to get)"),
) -> None:
    """Get or set configuration values."""
    cfg = load_config()

    if key is None:
        # Show all
        console.print()
        console.print(Text("  CheckMate Configuration", style=f"bold {HEX_GOLD}"))
        console.print(Text("  " + "─" * 42, style=HEX_SLATE))
        api_url = cfg.get("api_url", "")
        api_key = cfg.get("api_key", "")
        console.print(Text(f"  api_url  ", style="white"), end="")
        console.print(Text(api_url or "(not set)", style=HEX_SAND if api_url else HEX_SLATE))
        console.print(Text(f"  api_key  ", style="white"), end="")
        console.print(Text(
            (api_key[:8] + "...") if api_key else "(not set)",
            style=HEX_SAND if api_key else HEX_SLATE,
        ))
        console.print(Text(f"\n  Config file: {get_config_path()}\n", style=HEX_SLATE))
        return

    if key not in VALID_KEYS:
        console.print(Text(f'  Unknown config key: "{key}"', style=f"bold {HEX_CRIMSON}"))
        console.print(Text(f"  Valid keys: {', '.join(VALID_KEYS)}", style=HEX_SLATE))
        raise typer.Exit(1)

    if value is None:
        # Get
        val = cfg.get(key)
        if val:
            display = val[:8] + "..." if key == "api_key" else val
            console.print(Text(display, style=HEX_SAND))
        else:
            console.print(Text("(not set)", style=HEX_SLATE))
        return

    # Set
    cfg[key] = value
    save_config(cfg)
    display = value[:8] + "..." if key == "api_key" else value
    console.print(Text(f"  Set {key} = {display}", style=f"bold {HEX_SAGE}"))


# ── Entry point ───────────────────────────────────────────────────────────────
def main_entry() -> None:
    """Console scripts entry point."""
    app()


if __name__ == "__main__":
    main_entry()
