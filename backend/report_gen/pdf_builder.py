"""
PDF report builder using Jinja2 + WeasyPrint.

Falls back to HTML file if WeasyPrint is not installed.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from backend.core.logger import get_logger

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


def build_report(
    job_id: str,
    filename: str,
    doc_type: str,
    risk_tier: str,
    tier_label: str,
    final_score: float,
    ela_score: float,
    metadata_score: float,
    seal_score: float,
    nlp_score: float,
    ela_flags: list,
    metadata_flags: list,
    seal_flags: list,
    nlp_flags: list,
    pattern_flags: list,
    ela_heatmap_b64: str,
    extracted_fields: dict,
    registry_details: dict,
    llm_investigation: str,
    output_dir: str,
) -> dict:
    """
    Render the HTML report and attempt PDF generation via WeasyPrint.

    Returns:
        dict with keys: html_path, pdf_path (or None if WeasyPrint unavailable)
    """
    all_flags = ela_flags + metadata_flags + seal_flags + nlp_flags + pattern_flags

    template_data = {
        "job_id": job_id,
        "filename": filename,
        "doc_type": doc_type or "Unknown",
        "risk_tier": risk_tier,
        "tier_label": tier_label,
        "final_score": final_score,
        "final_score_pct": f"{final_score * 100:.0f}",
        "ela_score": ela_score,
        "metadata_score": metadata_score,
        "seal_score": seal_score,
        "nlp_score": nlp_score,
        "ela_flags": ela_flags,
        "metadata_flags": metadata_flags,
        "seal_flags": seal_flags,
        "nlp_flags": nlp_flags,
        "pattern_flags": pattern_flags,
        "all_flags": all_flags,
        "ela_heatmap_b64": ela_heatmap_b64 or "",
        "extracted_fields": extracted_fields or {},
        "registry_details": registry_details or {},
        "llm_investigation": llm_investigation or "",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    template = _jinja_env.get_template("report.html")
    html_content = template.render(**template_data)

    # Save HTML
    html_path = os.path.join(output_dir, f"{job_id}_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"[Report] HTML report saved: {html_path}")

    # Try PDF generation
    pdf_path = None
    try:
        from weasyprint import HTML
        pdf_path = os.path.join(output_dir, f"{job_id}_report.pdf")
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info(f"[Report] PDF report saved: {pdf_path}")
    except ImportError:
        logger.warning("[Report] WeasyPrint not installed — PDF generation skipped. Install: pip install weasyprint")
    except Exception as e:
        logger.error(f"[Report] PDF generation failed: {e}")

    return {"html_path": html_path, "pdf_path": pdf_path}
