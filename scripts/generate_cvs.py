"""
Generate synthetic PDF CVs and interview transcripts for each vacancy using local Ollama.

Usage:
    uv run --project backend python scripts/generate_cvs.py [options]

Output layout:
    example_data/generated/
        {vacancy_slug}/
            {tier}_{candidate_name}/
                cv.pdf
                transcript_1.pdf
                transcript_2.pdf
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_ollama import ChatOllama

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inlined JSON utilities (copied from backend/src/hargus_api/ai/agents/base.py)
# ---------------------------------------------------------------------------

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _normalize_llm_json_slice(s: str) -> str:
    return _TRAILING_COMMA.sub(r"\1", s)


def stringify_llm_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if isinstance(block.get("text"), str):
                    parts.append(block["text"])
                elif isinstance(block.get("content"), str):
                    parts.append(block["content"])
                else:
                    parts.append(str(block))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def parse_llm_json(text: Any) -> Any:
    raw = stringify_llm_content(text)
    if not raw.strip():
        raise ValueError("empty LLM output")

    stripped = raw.strip()
    m = _JSON_FENCE.search(stripped)
    if m:
        stripped = m.group(1).strip()

    decoder = json.JSONDecoder()

    def _try_load(s: str) -> Any:
        s = _normalize_llm_json_slice(s)
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        for i, ch in enumerate(s):
            if ch in "{[":
                try:
                    return decoder.raw_decode(s[i:])[0]
                except json.JSONDecodeError:
                    continue
        raise json.JSONDecodeError("No JSON object or array found", s, 0)

    return _try_load(stripped)


class LenientJsonOutputParser(BaseOutputParser):
    def parse(self, text: Any) -> Any:
        return parse_llm_json(text)

    @property
    def _type(self) -> str:
        return "lenient_json"


def build_json_chain(llm: BaseChatModel, system_prompt: str, human_template: str):
    dated_prompt = system_prompt + f"\n\nToday's date: {date.today().isoformat()}"
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=dated_prompt),
            HumanMessagePromptTemplate.from_template(human_template),
        ]
    )
    return prompt | llm | LenientJsonOutputParser()


def truncate(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_CV_SYSTEM = """\
You are a professional CV writer creating realistic candidate profiles for recruitment pipeline testing.

Given a job vacancy, generate a synthetic candidate CV that matches the specified quality tier.

Tier definitions:
- strong: 8-12 years of relevant experience, well-known companies, all required skills present, \
relevant degree and certifications, impressive achievements
- possible: 3-6 years of experience, solid but not elite background, roughly 60-70% of required \
skills, partial qualification match
- weak: 0-2 years of experience or entirely wrong domain, few or none of the required skills, \
no relevant certifications, generic education

Return ONLY valid JSON with this exact structure (no prose before or after):
{
  "name": "FirstName LastName",
  "email": "firstname.lastname@example.com",
  "phone": "+1 (555) 000-0000",
  "location": "City, State",
  "summary": "2-3 sentence professional summary tailored to the tier",
  "experience": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "from_year": "2019",
      "to_year": "2022",
      "description": "1-2 sentence description of responsibilities and achievements"
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "B.S.",
      "field": "Computer Science",
      "year": "2018"
    }
  ],
  "skills": ["Skill1", "Skill2"],
  "certifications": ["Certification Name"]
}

Rules:
- Use realistic, varied fictional names and company names
- Certifications may be an empty list [] for weak candidates
- Experience list: 3-5 entries for strong, 2-3 for possible, 1-2 for weak
- Do NOT wrap output in markdown fences
"""

_CV_HUMAN = """\
Vacancy:
{vacancy}

Tier: {tier}
Already used candidate names (do NOT use any of these): {taken_names}

Generate a realistic candidate CV as JSON.
"""

_CV_FALLBACK: dict = {
    "name": "Fallback Candidate",
    "email": "fallback@example.com",
    "phone": "+1 (555) 000-0000",
    "location": "Unknown",
    "summary": "CV generation failed.",
    "experience": [],
    "education": [],
    "skills": [],
    "certifications": [],
}

_TRANSCRIPT_SYSTEM = """\
You are generating a realistic job interview transcript for recruitment system testing.

The transcript should clearly reflect the candidate's quality tier:
- strong: articulate, uses specific STAR examples, demonstrates deep technical knowledge, \
confident and well-structured answers (4-6 sentences per answer)
- possible: adequate answers, some concrete examples but vague in places, moderate technical \
depth (2-4 sentences per answer)
- weak: short or evasive answers, lacks relevant examples, unable to answer technical questions \
well (1-3 sentences per answer)

The interview is a structured 1:1 with a hiring manager.

Return ONLY valid JSON with this exact structure:
{
  "candidate_name": "Full Name",
  "job_title": "Job Title from vacancy",
  "interviewer_name": "A realistic interviewer full name",
  "date": "YYYY-MM-DD",
  "turns": [
    {
      "question": "Interviewer question text",
      "answer": "Candidate answer text"
    }
  ]
}

Generate exactly 10-12 turns, one question per turn, covering ALL of these in order:
1. Opening — ask the candidate to introduce themselves and walk through their background
2. Motivation — why are they interested in this specific role and company?
3. Technical depth #1 — a question directly testing a core required skill from the vacancy
4. Technical depth #2 — a question on a second required skill or tool from the vacancy
5. Technical depth #3 — a scenario-based technical problem relevant to the role
6. Behavioural STAR #1 — a past example of handling a tight deadline or high-pressure situation
7. Behavioural STAR #2 — a past example of resolving a conflict or disagreement with a colleague
8. Behavioural STAR #3 — an example of leading or influencing without formal authority
9. Culture & collaboration — how they approach cross-functional work and communication
10. Growth areas — what skills or knowledge are they actively working to improve?
11. Candidate questions — invite them to ask the interviewer anything about the role or team
12. Closing — wrap up, explain next steps in the process

Use different question wording for different transcript indices.
Do NOT wrap output in markdown fences.
"""

_TRANSCRIPT_HUMAN = """\
Vacancy:
{vacancy}

Candidate summary:
{cv_summary}

Tier: {tier}
Transcript index: {transcript_index}

Generate the interview transcript as JSON.
"""

_TRANSCRIPT_FALLBACK: dict = {
    "candidate_name": "Fallback Candidate",
    "job_title": "Unknown Position",
    "interviewer_name": "Alex Johnson",
    "date": date.today().isoformat(),
    "turns": [{"question": "Transcript generation failed.", "answer": "N/A"}],
}


# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------


async def generate_cv(
    llm: BaseChatModel, vacancy_text: str, tier: str, taken_names: list[str]
) -> dict:
    names_str = ", ".join(taken_names) if taken_names else "none"
    chain = build_json_chain(llm, _CV_SYSTEM, _CV_HUMAN)
    for attempt in range(3):
        try:
            result = await chain.ainvoke(
                {"vacancy": truncate(vacancy_text), "tier": tier, "taken_names": names_str}
            )
            if isinstance(result, dict) and "name" in result:
                return result
            logger.warning("CV generation attempt %d returned unexpected shape: %s", attempt + 1, type(result))
        except Exception as exc:
            logger.warning("CV generation attempt %d failed (%s): %s", attempt + 1, type(exc).__name__, exc)
    logger.error("All CV generation attempts failed for tier=%s; using fallback", tier)
    return {**_CV_FALLBACK, "name": f"Fallback {tier.title()} Candidate"}


async def generate_transcript(
    llm: BaseChatModel,
    vacancy_text: str,
    cv_data: dict,
    tier: str,
    transcript_index: int,
) -> dict:
    skills_preview = ", ".join(cv_data.get("skills", [])[:5]) or "N/A"
    exp_count = len(cv_data.get("experience", []))
    cv_summary = (
        f"Name: {cv_data.get('name', 'Unknown')}\n"
        f"Skills: {skills_preview}\n"
        f"Experience entries: {exp_count}\n"
        f"Summary: {cv_data.get('summary', '')}"
    )

    chain = build_json_chain(llm, _TRANSCRIPT_SYSTEM, _TRANSCRIPT_HUMAN)
    for attempt in range(3):
        try:
            result = await chain.ainvoke(
                {
                    "vacancy": truncate(vacancy_text),
                    "cv_summary": cv_summary,
                    "tier": tier,
                    "transcript_index": transcript_index,
                }
            )
            if isinstance(result, dict) and "turns" in result:
                return result
            logger.warning(
                "Transcript generation attempt %d returned unexpected shape: %s", attempt + 1, type(result)
            )
        except Exception as exc:
            logger.warning(
                "Transcript generation attempt %d failed (%s): %s", attempt + 1, type(exc).__name__, exc
            )
    logger.error(
        "All transcript generation attempts failed for tier=%s index=%d; using fallback",
        tier,
        transcript_index,
    )
    return {
        **_TRANSCRIPT_FALLBACK,
        "candidate_name": cv_data.get("name", "Unknown"),
        "date": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Transcript text formatter
# ---------------------------------------------------------------------------


def _format_transcript_txt(transcript: dict, tier: str) -> str:
    lines = [
        f"INTERVIEW TRANSCRIPT",
        "=" * 60,
        f"Candidate:   {transcript.get('candidate_name', '')}",
        f"Position:    {transcript.get('job_title', '')}",
        f"Interviewer: {transcript.get('interviewer_name', '')}",
        f"Date:        {transcript.get('date', '')}",
        "=" * 60,
        "",
    ]
    for i, turn in enumerate(transcript.get("turns", []), 1):
        lines.append(f"[{i}] INTERVIEWER")
        lines.append(turn.get("question", ""))
        lines.append("")
        lines.append(f"[{i}] {transcript.get('candidate_name', 'CANDIDATE')}")
        lines.append(turn.get("answer", ""))
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
    # lines.append("-- Synthetic transcript · Hargus AI test data pipeline --")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------


def _render_pdf_sync(template_path: Path, context: dict) -> bytes:
    env = Environment(loader=FileSystemLoader(str(template_path.parent)), autoescape=True)
    html = env.get_template(template_path.name).render(**context)
    try:
        import weasyprint  # noqa: PLC0415

        return weasyprint.HTML(string=html).write_pdf()
    except Exception as exc:
        logger.error("WeasyPrint failed: %s", exc)
        raise


async def render_pdf(template_path: Path, context: dict) -> bytes:
    return await asyncio.to_thread(_render_pdf_sync, template_path, context)


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name).strip("_")


def candidate_dir(output_dir: Path, vacancy_slug: str, tier: str, candidate_name: str) -> Path:
    folder = output_dir / vacancy_slug / f"{tier}_{_safe_name(candidate_name)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

TIERS = ["strong", "possible", "weak"]


async def process_candidate(
    llm: BaseChatModel,
    vacancy_text: str,
    cv_data: dict,
    tier: str,
    vacancy_slug: str,
    output_dir: Path,
    templates_dir: Path,
    n_transcripts: int,
) -> None:
    name = cv_data.get("name", f"Unknown_{tier}")
    cdir = candidate_dir(output_dir, vacancy_slug, tier, name)
    logger.info("  [%s] rendering CV for %s", tier, name)

    # Render CV PDF
    try:
        cv_bytes = await render_pdf(templates_dir / "cv.html", {"cv": cv_data, "tier": tier})
        (cdir / "cv.pdf").write_bytes(cv_bytes)
        logger.info("  [%s] cv.pdf written (%d bytes)", tier, len(cv_bytes))
    except Exception as exc:
        logger.error("  [%s] cv.pdf render failed: %s", tier, exc)

    # Generate transcripts concurrently then render
    logger.info("  [%s] generating %d transcript(s)", tier, n_transcripts)
    t_tasks = [
        generate_transcript(llm, vacancy_text, cv_data, tier, i)
        for i in range(1, n_transcripts + 1)
    ]
    t_results = await asyncio.gather(*t_tasks, return_exceptions=True)

    for i, t_result in enumerate(t_results, 1):
        if isinstance(t_result, Exception):
            logger.error("  [%s] transcript %d generation error: %s", tier, i, t_result)
            continue
        fname = f"transcript_{i}.txt"
        txt = _format_transcript_txt(t_result if isinstance(t_result, dict) else {}, tier)
        (cdir / fname).write_text(txt, encoding="utf-8")
        logger.info("  [%s] %s written", tier, fname)


async def process_vacancy(
    vacancy_path: Path,
    llm: BaseChatModel,
    output_dir: Path,
    n_candidates: int,
    n_transcripts: int,
    templates_dir: Path,
    taken_names: list[str],
) -> None:
    vacancy_text = vacancy_path.read_text(encoding="utf-8")
    vacancy_slug = vacancy_path.stem
    tiers = TIERS[:n_candidates]

    logger.info("Processing vacancy: %s  (tiers: %s)", vacancy_slug, tiers)

    # Generate CVs sequentially so each call sees names already assigned
    for tier in tiers:
        cv_data = await generate_cv(llm, vacancy_text, tier, taken_names)
        name = cv_data.get("name", "")
        if name and not name.startswith("Fallback"):
            taken_names.append(name)
        await process_candidate(
            llm=llm,
            vacancy_text=vacancy_text,
            cv_data=cv_data,
            tier=tier,
            vacancy_slug=vacancy_slug,
            output_dir=output_dir,
            templates_dir=templates_dir,
            n_transcripts=n_transcripts,
        )

    logger.info("Done: %s", vacancy_slug)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic CV and interview transcript PDFs for each vacancy using local Ollama."
    )
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model name (default: llama3.2:3b)")
    parser.add_argument("--base-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--temperature", type=float, default=0.7, help="LLM temperature (default: 0.7)")
    parser.add_argument(
        "--vacancies-dir",
        default="example_data/vacancies",
        help="Directory containing vacancy .txt files",
    )
    parser.add_argument(
        "--output-dir",
        default="example_data/generated",
        help="Root directory for generated PDFs",
    )
    parser.add_argument(
        "--candidates-per-vacancy",
        type=int,
        default=3,
        help="Number of candidates to generate per vacancy (1-3, maps to tiers strong/possible/weak)",
    )
    parser.add_argument(
        "--transcripts-per-candidate",
        type=int,
        default=2,
        help="Number of interview transcripts per candidate",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    n_candidates = max(1, min(3, args.candidates_per_vacancy))
    n_transcripts = max(1, args.transcripts_per_candidate)

    llm = ChatOllama(
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
    )
    vacancies_dir = Path(args.vacancies_dir)
    output_dir = Path(args.output_dir)
    templates_dir = Path(__file__).parent / "templates"

    vacancy_files = sorted(vacancies_dir.glob("*.txt"))
    if not vacancy_files:
        logger.error("No .txt files found in %s", vacancies_dir)
        sys.exit(1)

    logger.info(
        "Found %d vacancies | model=%s | %d candidates × %d transcripts each",
        len(vacancy_files),
        args.model,
        n_candidates,
        n_transcripts,
    )

    total_pdfs = len(vacancy_files) * n_candidates * (1 + n_transcripts)
    logger.info("Expecting up to %d PDFs in %s", total_pdfs, output_dir)

    taken_names: list[str] = []
    for vf in vacancy_files:
        await process_vacancy(vf, llm, output_dir, n_candidates, n_transcripts, templates_dir, taken_names)

    logger.info("All done. Output: %s", output_dir.resolve())


if __name__ == "__main__":
    asyncio.run(main())
