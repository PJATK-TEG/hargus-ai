"""PDF renderer using WeasyPrint + Jinja2 templates."""
from __future__ import annotations

import asyncio
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _render_sync(report_data: dict) -> bytes:
    import weasyprint

    template = _jinja_env.get_template("candidate_report.html")
    html_str = template.render(**report_data)
    return weasyprint.HTML(string=html_str).write_pdf()


async def render_report_pdf(report) -> bytes:
    """Render a ReportDraft to PDF bytes (runs WeasyPrint in a thread)."""
    report_data = {
        "report": report,
        "score": report.score,
        "sections": report.sections,
    }
    return await asyncio.to_thread(_render_sync, report_data)
