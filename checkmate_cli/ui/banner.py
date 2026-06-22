"""
CheckMate CLI — ASCII art banner with gold-to-coral gradient.

Port of Banner.tsx — same block-letter art, same gradient direction.
"""

from rich.console import Console
from rich.text import Text
from rich.padding import Padding

from checkmate_cli.theme import gradient_chars, HEX_GOLD, HEX_SLATE, GOLD, SLATE


BANNER_LINES = [
    "   _____ _               _                    _       ",
    "  / ____| |             | |                  | |      ",
    " | |    | |__   ___  ___| | ___ __ ___   __ _| |_ ___ ",
    " | |    | '_ \\ / _ \\/ __| |/ / '_ ` _ \\ / _` | __/ _ \\",
    " | |____| | | |  __/ (__|   <| | | | | | (_| | ||  __/",
    "  \\_____|_| |_|\\___|\\___|_|\\_\\_| |_| |_|\\__,_|\\__\\___|",
]


def _make_gradient_text(lines: list[str]) -> Text:
    """Merge all banner lines into a single Rich Text with a gold→coral gradient."""
    full = "\n".join(lines)
    colored = gradient_chars(full)
    t = Text()
    for ch, style in colored:
        t.append(ch, style=style)
    return t


def print_banner(console: Console) -> None:
    """Print the CheckMate banner to the console."""
    banner_text = _make_gradient_text(BANNER_LINES)
    console.print()
    console.print(Padding(banner_text, (0, 0, 0, 2)))

    # Subtitle line
    subtitle = Text()
    subtitle.append("─" * 4, style=f"{HEX_SLATE}")
    subtitle.append(" CheckMate / Suraksha 2.0 ", style="bold white")
    subtitle.append("-" * 2, style=f"{HEX_SLATE}")
    subtitle.append(" AI Document Forensic Toolkit ", style=f"italic {HEX_GOLD}")
    subtitle.append("─" * 4, style=f"{HEX_SLATE}")

    console.print(Padding(subtitle, (0, 0, 1, 3)))
