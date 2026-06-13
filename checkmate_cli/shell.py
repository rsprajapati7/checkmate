"""
CheckMate CLI — Interactive REPL shell.

Port of Shell.tsx — command routing, command history, tab-completion,
natural language → Gemma, offline mode detection.
Uses prompt_toolkit for input with history + completion.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.text import Text

from checkmate_cli.api import (
    API_URL,
    ScanResponse,
    HealthResponse,
    health_check_sync,
    scan_document_sync,
    chat_stream_sync,
    generate_report_sync,
    ai_summary_stream_sync,
)
from checkmate_cli.theme import (
    HEX_GOLD, HEX_CORAL, HEX_SAGE, HEX_CRIMSON, HEX_SLATE, HEX_SAND,
)
from checkmate_cli.ui.banner import print_banner
from checkmate_cli.ui.diagnostic import print_diagnostic_table
from checkmate_cli.ui.help_menu import print_help
from checkmate_cli.ui.pipeline import run_pipeline_progress
from checkmate_cli.ui.status import print_status_panel
from checkmate_cli.ui.chat import stream_chat_response, stream_ai_summary


# ── Prompt toolkit style ─────────────────────────────────────────────────────
_PT_STYLE_NORMAL = PTStyle.from_dict({
    "prompt": f"bold {HEX_GOLD}",
})
_PT_STYLE_ACTIVE = PTStyle.from_dict({
    "prompt": f"bold {HEX_CORAL}",
})

# ── Tab-completable slash commands ───────────────────────────────────────────
_SLASH_COMMANDS = [
    "/analyze", "/view", "/report", "/reset",
    "/status",  "/clear", "/exit", "/help",
    "/a", "/v", "/r", "/rt", "/s", "/c", "/q", "/h",
]

_COMPLETER = WordCompleter(_SLASH_COMMANDS, sentence=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok(console: Console, msg: str) -> None:
    console.print(Text(f"[ OK ] {msg}", style=f"bold {HEX_SAGE}"))

def _err(console: Console, msg: str) -> None:
    console.print(Text(f"[FAIL] {msg}", style=f"bold {HEX_CRIMSON}"))

def _info(console: Console, msg: str) -> None:
    console.print(Text(f"  >>  {msg}", style=HEX_SLATE))

def _warn(console: Console, msg: str) -> None:
    console.print(Text(f"[WARN] {msg}", style=f"bold {HEX_CORAL}"))


# ── Shell ─────────────────────────────────────────────────────────────────────

def run_shell(
    console:    Console,
    is_offline: bool = False,
) -> None:
    """
    Launch the interactive CheckMate REPL.

    Parameters
    ----------
    console     Rich console instance (shared across all output)
    is_offline  True when backend is unavailable; disables scan/chat
    """
    active_doc:   Optional[ScanResponse]                 = None
    chat_history: list[dict[str, str]]                   = []

    session: Optional[PromptSession] = None
    try:
        if sys.stdin.isatty():
            session = PromptSession(
                history=InMemoryHistory(),
                completer=_COMPLETER,
                complete_while_typing=False,
            )
    except Exception:
        pass

    def _prompt_html() -> HTML:
        if active_doc:
            name = Path(active_doc.filename).name
            return HTML(f'<prompt>CheckMate [{name}] &gt;&gt; </prompt>')
        return HTML('<prompt>CheckMate &gt;&gt; </prompt>')

    def _prompt_style() -> PTStyle:
        return _PT_STYLE_ACTIVE if active_doc else _PT_STYLE_NORMAL

    # ── Command handlers ─────────────────────────────────────────────────────

    def cmd_analyze(arg: str) -> None:
        nonlocal active_doc
        if is_offline:
            _err(console, "Backend unavailable. Start the server and restart the CLI.")
            return
        if not arg:
            _err(console, "Usage: /analyze <file_path>")
            return

        full_path = Path(arg).expanduser().resolve()
        if not full_path.exists():
            _err(console, f'File not found: "{full_path}"')
            return

        result_holder: dict = {"result": None, "error": None}
        done_event = threading.Event()

        def _scan_worker():
            try:
                result_holder["result"] = scan_document_sync(str(full_path))
            except Exception as exc:
                result_holder["error"] = str(exc)
            finally:
                done_event.set()

        worker = threading.Thread(target=_scan_worker, daemon=True)
        worker.start()

        # Run animated progress while API call is in flight
        run_pipeline_progress(console, is_done_fn=done_event.is_set)
        worker.join()

        if result_holder["error"]:
            _err(console, f"Scan failed: {result_holder['error']}")
            return

        results = result_holder["result"]
        active_doc = results
        print_diagnostic_table(console, results)

        # Auto AI summary
        _info(console, "Generating AI forensic summary...")
        try:
            stream_ai_summary(console, ai_summary_stream_sync(results))
        except Exception as exc:
            _warn(console, f"AI summary unavailable: {exc}")

        # Auto-report
        _info(console, "Generating forensic report...")
        try:
            data, is_pdf = generate_report_sync(results)
            ext       = ".pdf" if is_pdf else ".html"
            stem      = full_path.stem
            out_path  = full_path.parent / f"{stem}_report{ext}"
            out_path.write_bytes(data)
            _ok(console, f"Report saved to: {out_path}")
        except Exception as exc:
            _warn(console, f"Auto-report failed: {exc}")

    def cmd_view(arg: str) -> None:
        if not active_doc:
            _err(console, "No active document. Run /analyze <path> first.")
            return
        valid = {"ela", "metadata", "meta", "seal", "nlp"}
        engine = arg.lower()
        if engine not in valid:
            _err(console, "Usage: /view <ela | metadata | seal | nlp>")
            return
        key = "metadata" if engine == "meta" else engine
        data = getattr(active_doc, key, None)
        if data is None:
            _err(console, f"No results for engine: {engine}")
            return
        console.print(Text(f"\n[Raw Engine Output: {engine.upper()}]", style=f"bold {HEX_GOLD}"))
        console.print_json(json.dumps(data))
        console.print()

    def cmd_report(arg: str) -> None:
        if is_offline:
            _err(console, "Backend unavailable. Cannot generate report.")
            return
        if not active_doc:
            _err(console, "No active document. Run /analyze <path> first.")
            return
        if not arg:
            _err(console, "Usage: /report <output_path.pdf|output_path.html>")
            return

        out_path = Path(arg).expanduser().resolve()
        _info(console, "Requesting report from backend...")
        try:
            data, is_pdf = generate_report_sync(active_doc)
            if is_pdf and not str(out_path).endswith(".pdf"):
                out_path = out_path.with_suffix(".pdf")
            elif not is_pdf and not str(out_path).endswith(".html"):
                out_path = out_path.with_suffix(".html")
            out_path.write_bytes(data)
            _ok(console, f"Report saved: {out_path} ({'PDF' if is_pdf else 'HTML'})")
        except Exception as exc:
            _err(console, f"Report failed: {exc}")

    def cmd_reset() -> None:
        nonlocal chat_history
        chat_history = []
        _ok(console, "Chat memory cleared.")

    def cmd_status() -> None:
        print_status_panel(console, None)

    def cmd_clear() -> None:
        console.clear()
        print_banner(console)

    def cmd_chat(text: str) -> None:
        nonlocal chat_history
        if is_offline:
            _err(console, "Backend unavailable. Cannot reach Gemma.")
            return
        console.print(Text(f"\nYou: {text}", style="white"))
        chat_history.append({"role": "user", "content": text})
        try:
            response = stream_chat_response(
                console,
                chat_stream_sync(
                    message=text,
                    context=active_doc._raw if active_doc else None,
                    history=chat_history,
                ),
            )
            chat_history.append({"role": "assistant", "content": response})
        except Exception as exc:
            _err(console, f"Gemma error: {exc}")
            chat_history.pop()  # remove failed user message

    # ── REPL loop ─────────────────────────────────────────────────────────────
    while True:
        try:
            if session is not None:
                raw = session.prompt(
                    _prompt_html(),
                    style=_prompt_style(),
                )
            else:
                prompt_text = f"CheckMate [{Path(active_doc.filename).name}] >> " if active_doc else "CheckMate >> "
                raw = input(prompt_text)
        except (KeyboardInterrupt, EOFError):
            _info(console, "Closing CheckMate session. Goodbye.")
            break

        trimmed = raw.strip()
        if not trimmed:
            continue

        if trimmed.startswith("/"):
            parts = trimmed.split(None, 1)
            cmd   = parts[0].lower()
            arg   = parts[1].strip() if len(parts) > 1 else ""

            if cmd in ("/exit", "/quit", "/q", "/e"):
                _info(console, "Closing CheckMate session. Goodbye.")
                break
            elif cmd in ("/clear", "/c"):
                cmd_clear()
            elif cmd in ("/help", "/h"):
                print_help(console)
            elif cmd in ("/status", "/s"):
                cmd_status()
            elif cmd in ("/reset", "/rt"):
                cmd_reset()
            elif cmd in ("/analyze", "/a"):
                cmd_analyze(arg)
            elif cmd in ("/view", "/v"):
                cmd_view(arg)
            elif cmd in ("/report", "/r"):
                cmd_report(arg)
            else:
                _err(console, f'Unknown command: "{trimmed}". Type /help for the command index.')
        else:
            cmd_chat(trimmed)
