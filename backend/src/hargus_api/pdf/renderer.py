"""PDF via WeasyPrint, with fpdf2 fallback when GTK/Pango are missing (typical on Windows)."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _latin1_safe(text: str) -> str:
    """Core PDF fonts only support Latin-1; replace unsupported characters."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _fpdf_multi_left(pdf, line_height: float, text: str) -> None:
    """Wrap text from the left margin.

    fpdf2 leaves the cursor at the end of the last line after ``multi_cell``; the
    next ``multi_cell(..., w=0)`` then has **no** horizontal room. Always reset X.
    """
    if not text.strip():
        return
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, line_height, text)


def _render_fallback_pdf(report_data: dict) -> bytes:
    """Pure-Python PDF when WeasyPrint cannot load (missing libgobject/pango on Windows)."""
    from fpdf import FPDF

    report = report_data["report"]
    score = report_data["score"]
    sections = report_data["sections"]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _latin1_safe("Candidate Analysis Report"), ln=True)
    pdf.set_font("Helvetica", size=9)
    meta = _latin1_safe(
        f"Candidate: {report.candidate_id} | Vacancy: {report.vacancy_id} | "
        f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    _fpdf_multi_left(pdf, 5, meta)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _latin1_safe(f"Score: {score.overall_score:.1f} / 100"), ln=True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(
        0,
        6,
        _latin1_safe(f"Recommendation: {report.recommendation.replace('_', ' ')}"),
        ln=True,
    )
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _latin1_safe("Executive Summary"), ln=True)
    pdf.set_font("Helvetica", size=11)
    _fpdf_multi_left(pdf, 5, _latin1_safe(report.executive_summary))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _latin1_safe("Rationale"), ln=True)
    pdf.set_font("Helvetica", size=11)
    _fpdf_multi_left(pdf, 5, _latin1_safe(report.recommendation_rationale))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _latin1_safe("Score Breakdown"), ln=True)
    pdf.set_font("Helvetica", size=10)
    rows = [
        ("Skill Match", f"{score.skill_match_score}%", "40%"),
        ("Experience", f"{score.experience_score}%", "35%"),
        ("Interview Performance", f"{score.interview_score}%", "25%"),
    ]
    for label, val, w in rows:
        pdf.cell(0, 5, _latin1_safe(f"{label}: {val} (weight {w})"), ln=True)
    if score.risk_penalty > 0:
        pdf.cell(0, 5, _latin1_safe(f"Risk Penalty: -{score.risk_penalty} pts"), ln=True)
    pdf.ln(4)

    for section in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _latin1_safe(section.title), ln=True)
        pdf.set_font("Helvetica", size=11)
        _fpdf_multi_left(pdf, 5, _latin1_safe(section.content))
        if section.evidence:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 5, _latin1_safe("Evidence:"), ln=True)
            pdf.set_font("Helvetica", size=9)
            for ev in section.evidence:
                ev_s = (ev or "").strip()
                if not ev_s:
                    continue
                _fpdf_multi_left(pdf, 4, _latin1_safe(f"  - {ev_s}"))
        pdf.ln(2)

    out = pdf.output()
    return bytes(out)


def _render_sync(report_data: dict) -> bytes:
    # GTK/Pango are not bundled on Windows; importing WeasyPrint always fails there.
    if sys.platform == "win32":
        logger.info("Using fpdf2 PDF renderer on Windows (WeasyPrint needs GTK).")
        return _render_fallback_pdf(report_data)

    try:
        import weasyprint  # noqa: PLC0415 — GTK/Pango may be missing

        template = _jinja_env.get_template("candidate_report.html")
        html_str = template.render(**report_data)
        return weasyprint.HTML(string=html_str).write_pdf()
    except Exception as exc:
        logger.warning(
            "WeasyPrint unavailable or failed (%s); using fpdf2 fallback PDF",
            exc,
        )
        return _render_fallback_pdf(report_data)


async def render_report_pdf(report) -> bytes:
    """Render a ReportDraft to PDF bytes (runs renderer in a worker thread)."""
    report_data = {
        "report": report,
        "score": report.score,
        "sections": report.sections,
    }
    return await asyncio.to_thread(_render_sync, report_data)
