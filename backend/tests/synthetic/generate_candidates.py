"""Synthetic candidate dataset generator for pipeline testing.

Generates realistic candidate profiles across a spectrum of quality (strong → weak)
for use in:
  - agent unit tests (mock inputs)
  - evaluation metric benchmarking (rank-order tests)
  - end-to-end smoke tests (trigger the full workflow without real CVs)

Usage:
    python -m tests.synthetic.generate_candidates --count 20 --out candidates.json

Each generated candidate includes:
  - Structured CV text (parsedFields equivalent)
  - Mock interview transcript
  - Expected scoring tier (strong / possible / weak / red_flag)
  - Ground-truth labels for evaluation
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from dataclasses import asdict, dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Domain vocabulary
# ---------------------------------------------------------------------------

BACKEND_SKILLS = ["Python", "Go", "PostgreSQL", "Redis", "Kafka", "Docker", "Kubernetes",
                  "gRPC", "REST APIs", "Distributed Systems", "AWS", "Celery", "FastAPI"]
ML_SKILLS = ["PyTorch", "TensorFlow", "Transformers", "LangChain", "RAG", "Fine-tuning",
             "ONNX", "MLflow", "scikit-learn", "HuggingFace", "Python", "CUDA"]
FRONTEND_SKILLS = ["React", "TypeScript", "Next.js", "CSS", "Vite", "Figma", "GraphQL"]

COMPANIES_SENIOR = ["Stripe", "Airbnb", "Notion", "Cohere", "Anthropic", "OpenAI",
                    "Databricks", "Scale AI", "Hugging Face"]
COMPANIES_MID = ["Startup A", "Series B Corp", "Consulting Firm X", "Agency Y"]
COMPANIES_JUNIOR = ["Local Agency", "Freelance", "Bootcamp Project", "Internship Co"]

UNIVERSITIES_TOP = ["Stanford", "MIT", "CMU", "ETH Zurich", "Oxford", "Cambridge"]
UNIVERSITIES_MID = ["State University", "City College", "Online University"]

DEGREES = ["B.S.", "M.S.", "Ph.D.", "B.Eng."]

Tier = Literal["strong", "possible", "weak", "red_flag"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExperienceEntry:
    company: str
    role: str
    duration_months: int
    description: str


@dataclass
class EducationEntry:
    institution: str
    degree: str
    field: str
    year: str


@dataclass
class SyntheticCandidate:
    id: str
    name: str
    email: str
    location: str
    skills: list[str]
    experience_entries: list[ExperienceEntry]
    total_years_experience: float
    education: list[EducationEntry]
    certifications: list[str]
    domain_signals: list[str]
    interview_transcript: str
    vacancy_id: str
    # Ground-truth labels for evaluation
    expected_tier: Tier
    expected_skill_coverage: float  # 0–1 against the target vacancy's required skills
    has_risk_flags: bool
    risk_description: str = ""

    def to_cv_text(self) -> str:
        """Render the candidate as a plain-text CV document."""
        lines = [
            f"CANDIDATE: {self.name}",
            f"Email: {self.email}   Location: {self.location}",
            "",
            f"SKILLS: {', '.join(self.skills)}",
            "",
            f"EXPERIENCE ({self.total_years_experience:.1f} years total)",
        ]
        for exp in self.experience_entries:
            lines += [
                f"  {exp.company} — {exp.role} ({exp.duration_months} months)",
                f"  {exp.description}",
            ]
        lines += ["", "EDUCATION"]
        for edu in self.education:
            lines.append(f"  {edu.degree} in {edu.field}, {edu.institution} ({edu.year})")
        if self.certifications:
            lines += [f"CERTIFICATIONS: {', '.join(self.certifications)}"]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generators per tier
# ---------------------------------------------------------------------------


def _pick(lst: list, k: int) -> list:
    return random.sample(lst, min(k, len(lst)))


def _gen_strong(vacancy_skills: list[str], vacancy_id: str, idx: int) -> SyntheticCandidate:
    skills = list(set(vacancy_skills + _pick(BACKEND_SKILLS, 3)))
    random.shuffle(skills)
    years = random.uniform(6, 12)
    exp = [
        ExperienceEntry(
            company=random.choice(COMPANIES_SENIOR),
            role="Senior Engineer",
            duration_months=random.randint(24, 48),
            description="Led design and delivery of high-scale distributed systems.",
        ),
        ExperienceEntry(
            company=random.choice(COMPANIES_MID),
            role="Software Engineer",
            duration_months=random.randint(18, 36),
            description="Owned backend APIs and database migrations.",
        ),
    ]
    transcript = (
        "Interviewer: Walk me through your most complex system design.\n"
        "Candidate: I led a complete rewrite of our payments pipeline. "
        "We moved from a monolith to event-driven microservices using Kafka. "
        "The system now handles 500k TPS with 99.99% uptime.\n"
        "Interviewer: How did you handle data consistency?\n"
        "Candidate: We used saga patterns and idempotency keys at every step."
    )
    return SyntheticCandidate(
        id=f"syn-{idx:03d}",
        name=f"Strong Candidate {idx}",
        email=f"strong{idx}@example.com",
        location="San Francisco, CA",
        skills=skills,
        experience_entries=exp,
        total_years_experience=years,
        education=[EducationEntry(
            institution=random.choice(UNIVERSITIES_TOP),
            degree=random.choice(["M.S.", "Ph.D."]),
            field="Computer Science",
            year=str(random.randint(2012, 2019)),
        )],
        certifications=[random.choice(["AWS Solutions Architect", "GCP Professional", "CKA"])],
        domain_signals=["distributed systems", "fintech"],
        interview_transcript=transcript,
        vacancy_id=vacancy_id,
        expected_tier="strong",
        expected_skill_coverage=1.0,
        has_risk_flags=False,
    )


def _gen_possible(vacancy_skills: list[str], vacancy_id: str, idx: int) -> SyntheticCandidate:
    # Matches ~60% of required skills
    matched = _pick(vacancy_skills, max(1, len(vacancy_skills) * 2 // 3))
    extra = _pick(BACKEND_SKILLS, 2)
    skills = list(set(matched + extra))
    years = random.uniform(3, 6)
    exp = [
        ExperienceEntry(
            company=random.choice(COMPANIES_MID),
            role="Software Engineer",
            duration_months=random.randint(18, 36),
            description="Built REST APIs and maintained PostgreSQL databases.",
        )
    ]
    transcript = (
        "Interviewer: Describe a technical challenge you solved.\n"
        "Candidate: I had to optimise a slow query that was timing out. "
        "I added an index and rewrote the ORM call to use a raw query — "
        "dropped latency from 4s to 120ms.\n"
        "Interviewer: Good. What about system design at scale?\n"
        "Candidate: I have some exposure but most of my work has been single-service."
    )
    return SyntheticCandidate(
        id=f"syn-{idx:03d}",
        name=f"Possible Candidate {idx}",
        email=f"possible{idx}@example.com",
        location="Remote",
        skills=skills,
        experience_entries=exp,
        total_years_experience=years,
        education=[EducationEntry(
            institution=random.choice(UNIVERSITIES_MID),
            degree="B.S.",
            field="Software Engineering",
            year=str(random.randint(2016, 2022)),
        )],
        certifications=[],
        domain_signals=["backend", "web"],
        interview_transcript=transcript,
        vacancy_id=vacancy_id,
        expected_tier="possible",
        expected_skill_coverage=len(matched) / len(vacancy_skills),
        has_risk_flags=False,
    )


def _gen_weak(vacancy_skills: list[str], vacancy_id: str, idx: int) -> SyntheticCandidate:
    skills = _pick(FRONTEND_SKILLS, 3)  # Wrong domain
    years = random.uniform(0.5, 2.0)
    exp = [
        ExperienceEntry(
            company=random.choice(COMPANIES_JUNIOR),
            role="Junior Developer",
            duration_months=random.randint(6, 18),
            description="Built landing pages and maintained WordPress sites.",
        )
    ]
    transcript = (
        "Interviewer: What backend technologies have you used?\n"
        "Candidate: Mainly JavaScript and some PHP for WordPress.\n"
        "Interviewer: Have you worked with PostgreSQL or Redis?\n"
        "Candidate: No, not really. I've used MySQL a bit."
    )
    return SyntheticCandidate(
        id=f"syn-{idx:03d}",
        name=f"Weak Candidate {idx}",
        email=f"weak{idx}@example.com",
        location="New York, NY",
        skills=skills,
        experience_entries=exp,
        total_years_experience=years,
        education=[EducationEntry(
            institution=random.choice(UNIVERSITIES_MID),
            degree="B.S.",
            field="Graphic Design",
            year=str(random.randint(2019, 2023)),
        )],
        certifications=[],
        domain_signals=["frontend", "design"],
        interview_transcript=transcript,
        vacancy_id=vacancy_id,
        expected_tier="weak",
        expected_skill_coverage=0.0,
        has_risk_flags=False,
    )


def _gen_red_flag(vacancy_skills: list[str], vacancy_id: str, idx: int) -> SyntheticCandidate:
    candidate = _gen_possible(vacancy_skills, vacancy_id, idx)
    # Add a 2-year unexplained employment gap and contradictory claims
    candidate.experience_entries.append(
        ExperienceEntry(
            company="Unknown Firm",
            role="Consultant",
            duration_months=4,
            description="Short contract role. Company dissolved.",
        )
    )
    candidate.id = f"syn-rf-{idx:03d}"
    candidate.name = f"RedFlag Candidate {idx}"
    candidate.email = f"redflag{idx}@example.com"
    candidate.interview_transcript += (
        "\nInterviewer: There's a 2-year gap in your CV (2020-2022). Can you explain?\n"
        "Candidate: I was consulting... mostly informal work. Hard to document."
    )
    candidate.expected_tier = "red_flag"
    candidate.has_risk_flags = True
    candidate.risk_description = "2-year unexplained employment gap; inconsistent company history"
    return candidate


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

# The required skills for the default test vacancy
DEFAULT_VACANCY_SKILLS = ["Python", "PostgreSQL", "Distributed Systems"]
DEFAULT_VACANCY_ID = "v1"


def generate_dataset(
    count: int = 20,
    seed: int = 42,
    vacancy_skills: list[str] = DEFAULT_VACANCY_SKILLS,
    vacancy_id: str = DEFAULT_VACANCY_ID,
) -> list[SyntheticCandidate]:
    random.seed(seed)

    tiers: list[Tier] = ["strong", "possible", "weak", "red_flag"]
    # Distribute: 25% each tier
    per_tier = max(1, count // 4)
    remainder = count - per_tier * 4
    counts = {t: per_tier for t in tiers}
    counts["possible"] += remainder  # give extras to the middle tier

    generators = {
        "strong": _gen_strong,
        "possible": _gen_possible,
        "weak": _gen_weak,
        "red_flag": _gen_red_flag,
    }

    candidates: list[SyntheticCandidate] = []
    idx = 1
    for tier in tiers:
        for _ in range(counts[tier]):
            candidates.append(generators[tier](vacancy_skills, vacancy_id, idx))
            idx += 1

    random.shuffle(candidates)
    return candidates


def dataset_to_json(candidates: list[SyntheticCandidate]) -> str:
    def _serialise(c: SyntheticCandidate) -> dict:
        d = asdict(c)
        d["cv_text"] = c.to_cv_text()
        return d

    return json.dumps([_serialise(c) for c in candidates], indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic candidate dataset")
    parser.add_argument("--count", type=int, default=20, help="Number of candidates to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="-", help="Output file path (default: stdout)")
    args = parser.parse_args()

    dataset = generate_dataset(count=args.count, seed=args.seed)
    output = dataset_to_json(dataset)

    if args.out == "-":
        print(output)
    else:
        from pathlib import Path
        Path(args.out).write_text(output)
        print(f"Wrote {len(dataset)} candidates to {args.out}")

    # Print a summary
    from collections import Counter
    tiers = Counter(c.expected_tier for c in dataset)
    print(f"\nDataset summary ({len(dataset)} candidates):")
    for tier, n in sorted(tiers.items()):
        print(f"  {tier:12s}: {n}")
