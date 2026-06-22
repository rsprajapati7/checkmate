"""
CheckMate CLI — Help menu panel.

Port of HelpMenu.tsx — same command set, aliases, descriptions.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from checkmate_cli.theme import HEX_GOLD, HEX_SAGE, HEX_SLATE, HEX_CORAL


COMMANDS = [
    ("/analyze", "/a",  "<file_path>",              "Upload document and run all forensic pipelines"),
    ("/report",  "/r",  "<output.pdf|output.html>", "Generate a polished PDF/HTML forensic report"),
    ("/dashboard", "/d", "<ela|seal> [page_num]",    "Generate and open ELA/Seal visual diagnostic dashboard"),
    ("/reset",   "/rt", "",                          "Clear chat memory and reset document selection"),
    ("/status",  "/s",  "",                          "Run backend server health diagnostics"),
    ("/clear",   "/c",  "",                          "Clear terminal and redraw banner"),
    ("/exit",    "/q",  "",                          "Exit the CheckMate interactive shell"),
]


def print_help(console: Console) -> None:
    """Print the command index panel."""
    table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("cmd",   style=f"bold {HEX_GOLD}",  no_wrap=True)
    table.add_column("alias", style=HEX_SLATE,            no_wrap=True)
    table.add_column("args",  style=f"italic {HEX_SAGE}", no_wrap=True)
    table.add_column("desc",  style=HEX_SLATE)

    for cmd, alias, args, desc in COMMANDS:
        table.add_row(cmd, alias, args, desc)

    hint = Text()
    hint.append("\nAny input not starting with ", style=HEX_SLATE)
    hint.append("/", style=f"bold {HEX_GOLD}")
    hint.append(" is routed to ", style=HEX_SLATE)
    hint.append("Local LLM", style=f"bold {HEX_GOLD}")
    hint.append(" as a natural language prompt.", style=HEX_SLATE)
    hint.append("\nIf a document is active, the Local LLM receives its full forensic context.", style=HEX_SLATE)

    panel_content = Text()
    # We'll compose table + hint inside a group
    from rich.console import Group
    group = Group(table, hint)

    header = Text()
    header.append("-- COMMAND INDEX", style=f"bold {HEX_GOLD}")
    header.append("  (tab-completion supported)", style=HEX_SLATE)

    panel = Panel(
        group,
        title=header,
        title_align="left",
        border_style=HEX_GOLD,
        padding=(0, 1),
    )
    console.print(panel)
