"""
CheckMate CLI — Rich color palette and styles.

Same hex values as the original TypeScript theme.ts.
Gold/Coral/Sage/Crimson — no blue.
"""

from rich.style import Style
from rich.theme import Theme

# ── Raw hex values ──────────────────────────────────────────────────────────
HEX_GOLD    = "#D4AF37"
HEX_CORAL   = "#D1855C"
HEX_SAGE    = "#8DECB4"
HEX_CRIMSON = "#C0392B"
HEX_SAND    = "#F6F3EB"
HEX_SLATE   = "#4A4A5A"

# ── Rich Styles ──────────────────────────────────────────────────────────────
GOLD         = Style(color=HEX_GOLD)
CORAL        = Style(color=HEX_CORAL)
SAGE         = Style(color=HEX_SAGE)
CRIMSON      = Style(color=HEX_CRIMSON)
SAND         = Style(color=HEX_SAND)
SLATE        = Style(color=HEX_SLATE)

GOLD_BOLD    = Style(color=HEX_GOLD, bold=True)
CORAL_BOLD   = Style(color=HEX_CORAL, bold=True)
SAGE_BOLD    = Style(color=HEX_SAGE, bold=True)
CRIMSON_BOLD = Style(color=HEX_CRIMSON, bold=True)
SAND_BOLD    = Style(color=HEX_SAND, bold=True)

GOLD_DIM     = Style(color=HEX_GOLD, dim=True)
MUTED        = Style(color=HEX_SLATE)

# Success / warning / error
SUCCESS  = SAGE_BOLD
WARNING  = CORAL_BOLD
ERROR    = CRIMSON_BOLD
INFO     = GOLD

# ── Rich Theme (registered names) ───────────────────────────────────────────
CHECKMATE_THEME = Theme({
    "gold":         HEX_GOLD,
    "coral":        HEX_CORAL,
    "sage":         HEX_SAGE,
    "crimson":      HEX_CRIMSON,
    "sand":         HEX_SAND,
    "slate":        HEX_SLATE,
    "success":      f"bold {HEX_SAGE}",
    "warning":      f"bold {HEX_CORAL}",
    "error":        f"bold {HEX_CRIMSON}",
    "muted":        HEX_SLATE,
    "prompt":       f"bold {HEX_GOLD}",
    "header":       f"bold {HEX_GOLD}",
})

# ── Score risk color helper ──────────────────────────────────────────────────
def score_style(score: float) -> Style:
    """Return a risk-colored style based on score (0–100)."""
    if score >= 70:
        return CRIMSON_BOLD
    elif score >= 30:
        return CORAL_BOLD
    return SAGE_BOLD


def risk_tier_style(tier: str) -> tuple[Style, str]:
    """Return (style, label) for a risk tier string."""
    t = tier.upper()
    if t in ("RED", "HIGH"):
        return CRIMSON_BOLD, "CRITICAL RISK"
    elif t in ("ORANGE", "AMBER", "MEDIUM"):
        return CORAL_BOLD, "SUSPICIOUS"
    return SAGE_BOLD, "VERIFIED SAFE"


# ── Gradient helper (gold → coral across n chars) ───────────────────────────
def gradient_chars(text: str) -> list[tuple[str, Style]]:
    """
    Produce a list of (char, style) pairs interpolating from gold to coral.
    Used by the banner renderer.
    """
    n = max(len(text), 1)
    # Parse hex → RGB
    def hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    r1, g1, b1 = hex_to_rgb(HEX_GOLD)
    r2, g2, b2 = hex_to_rgb(HEX_CORAL)

    result = []
    for i, ch in enumerate(text):
        t = i / (n - 1) if n > 1 else 0
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        style = Style(color=f"#{r:02x}{g:02x}{b:02x}", bold=True)
        result.append((ch, style))
    return result
