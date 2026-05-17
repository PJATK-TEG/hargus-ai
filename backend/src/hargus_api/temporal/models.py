"""Pydantic models for all Temporal activity inputs and outputs.

Every value that crosses an activity boundary must be serialisable via these
models. Only use primitives, lists, dicts, and nested Pydantic models here.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── Workflow entry ────────────────────────────────────────────────────────────


class AnalysisWorkflowInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    task_type: str  # candidate_summary | candidate_red_flags | candidate_comparison
    analysis_prompt: str = ""  # coordinator prompt; loaded from config when empty


# ── Ingestion ─────────────────────────────────────────────────────────────────


class RawDocument(BaseModel):
    source_type: Literal["cv", "transcript", "notes", "background"]
    storage_key: str
    filename: str
    size_bytes: int | None
    inline_text: str | None = None


class LoadDocumentsInput(BaseModel):
    workflow_run_id: str
    candidate_id: str


class LoadDocumentsOutput(BaseModel):
    documents: list[RawDocument]


class ParsedDocument(BaseModel):
    source_type: Literal["cv", "transcript", "notes", "background"]
    storage_key: str
    raw_text: str
    page_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParseDocumentsInput(BaseModel):
    workflow_run_id: str
    documents: list[RawDocument]


class ParseDocumentsOutput(BaseModel):
    documents: list[ParsedDocument]


# ── Embedding ─────────────────────────────────────────────────────────────────


class ChunkEmbedInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    documents: list[ParsedDocument]
    chunk_size: int = 512
    chunk_overlap: int = 64


class ChunkEmbedOutput(BaseModel):
    collection_name: str  # pgvector collection identifier for this run
    chunk_count: int


# ── Agent inputs (shared by all 4 analysis agents) ───────────────────────────


class AgentActivityInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    collection_name: str
    documents: list[ParsedDocument]


# ── Agent outputs ─────────────────────────────────────────────────────────────


class JobRubric(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_years_min: int = 0
    key_responsibilities: list[str] = Field(default_factory=list)
    seniority_level: str = ""
    domain_keywords: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    company: str
    role: str
    duration_months: int
    description: str


class CandidateFacts(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience_entries: list[ExperienceEntry] = Field(default_factory=list)
    total_years_experience: float = 0.0
    education: list[dict[str, str]] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    domain_signals: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class BehavioralExample(BaseModel):
    competency: str
    example: str
    is_strength: bool


class InterviewFindings(BaseModel):
    communication_quality: Literal["strong", "adequate", "weak", "unknown"] = "unknown"
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    behavioral_examples: list[BehavioralExample] = Field(default_factory=list)
    overall_impression: str = ""


class RiskFlag(BaseModel):
    severity: Literal["low", "medium", "high"]
    category: Literal["gap", "contradiction", "inconsistency", "other"]
    description: str


class RiskFlags(BaseModel):
    flags: list[RiskFlag] = Field(default_factory=list)
    overall_severity: Literal["low", "medium", "high"] = "low"
    has_critical_issues: bool = False


# ── Consolidation ─────────────────────────────────────────────────────────────


class ConsolidateInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    rubric: JobRubric
    candidate_facts: CandidateFacts
    interview_findings: InterviewFindings
    risk_flags: RiskFlags


class ConsolidatedFacts(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    rubric: JobRubric
    candidate_facts: CandidateFacts
    interview_findings: InterviewFindings
    risk_flags: RiskFlags
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    skill_coverage: float = 0.0  # 0.0–1.0


# ── Scoring ───────────────────────────────────────────────────────────────────


class ScoringResult(BaseModel):
    overall_score: float  # 0.0–100.0
    skill_match_score: float
    experience_score: float
    interview_score: float
    risk_penalty: float
    recommendation: Literal["strong_match", "possible", "weak", "manual_review"]
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    rationale: str = ""


# ── Reporting ─────────────────────────────────────────────────────────────────


class ReportSection(BaseModel):
    title: str
    content: str
    evidence: list[str] = Field(default_factory=list)


class ReportDraftInput(BaseModel):
    consolidated: ConsolidatedFacts
    score: ScoringResult
    analysis_prompt: str = ""  # coordinator mission prompt forwarded from workflow input


class ReportDraft(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    generated_at: datetime
    executive_summary: str
    sections: list[ReportSection]
    recommendation: str
    recommendation_rationale: str
    score: ScoringResult


class PDFOutput(BaseModel):
    storage_key: str
    size_bytes: int


# ── Candidate update ─────────────────────────────────────────────────────────


class CandidateProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class UpdateCandidateProfileInput(BaseModel):
    candidate_id: str
    profile: CandidateProfile


class UpdateCandidateInput(BaseModel):
    candidate_id: str
    consolidated: ConsolidatedFacts
    score: ScoringResult


# ── Final store ───────────────────────────────────────────────────────────────


class StoreResultInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    report: ReportDraft
    score: ScoringResult
    pdf: PDFOutput | None
    consolidated: ConsolidatedFacts | None = None  # update moved to update_candidate_activity
    # Langfuse / dashboards — from consolidation (not persisted separately)
    skill_coverage: float = 0.0
    risk_flag_count: int = 0
    risk_flags_high: int = 0
    risk_flags_medium: int = 0
    risk_flags_low: int = 0


class MarkTaskFailedInput(BaseModel):
    workflow_run_id: str
    error_message: str


# ── Candidate query ───────────────────────────────────────────────────────────


class CandidateQueryInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    query: str
    collection_name: str = ""  # auto-computed in activity if empty


class CandidateQueryActivityInput(BaseModel):
    workflow_run_id: str
    candidate_id: str
    vacancy_id: str
    query: str
    collection_name: str = ""


class CandidateQueryResult(BaseModel):
    workflow_run_id: str
    candidate_id: str
    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: str = "low"


class StoreQueryResultInput(BaseModel):
    workflow_run_id: str
    result: CandidateQueryResult
