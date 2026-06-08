"""
Accounting rules for cross-document NLP verification.

Checks standard accounting identities and cross-document figure consistency.
"""

from typing import List, Tuple


def check_balance_sheet(assets: float, liabilities: float, equity: float) -> Tuple[bool, str]:
    """Assets should approximately equal Liabilities + Equity (±5% tolerance)."""
    if assets <= 0:
        return False, ""
    expected = liabilities + equity
    if expected <= 0:
        return False, ""
    ratio = abs(assets - expected) / assets
    if ratio > 0.05:
        return True, f"Balance sheet mismatch: Assets={assets:,.0f} != Liabilities+Equity={expected:,.0f} ({ratio:.1%} deviation)"
    return False, ""


def check_revenue_gst_consistency(revenue: float, gst_turnover: float) -> Tuple[bool, str]:
    """Revenue in P&L should match GST turnover within ±20%."""
    if revenue <= 0 or gst_turnover <= 0:
        return False, ""
    ratio = abs(revenue - gst_turnover) / max(revenue, gst_turnover)
    if ratio > 0.20:
        return True, f"Revenue/GST mismatch: P&L Revenue={revenue:,.0f}, GST Turnover={gst_turnover:,.0f} ({ratio:.1%} deviation)"
    return False, ""


def check_pan_consistency(pan_numbers: List[str]) -> Tuple[bool, str]:
    """All documents should reference the same PAN number."""
    unique = set(pan_numbers)
    if len(unique) > 1:
        return True, f"Multiple different PAN numbers found across documents: {sorted(unique)}"
    return False, ""


def check_aadhaar_consistency(aadhaar_numbers: List[str]) -> Tuple[bool, str]:
    """All documents should reference the same Aadhaar number."""
    unique = set(aadhaar_numbers)
    if len(unique) > 1:
        return True, f"Multiple different Aadhaar numbers found across documents: {sorted(unique)}"
    return False, ""


def check_gst_consistency(gst_numbers: List[str]) -> Tuple[bool, str]:
    """All documents should reference the same GST number."""
    unique = set(gst_numbers)
    if len(unique) > 1:
        return True, f"Multiple different GST numbers found across documents: {sorted(unique)}"
    return False, ""
