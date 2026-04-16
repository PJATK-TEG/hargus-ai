from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VacancyType = Literal["full-time", "part-time", "contract", "remote"]
VacancyStatus = Literal["active", "paused", "closed"]
TagColor = Literal["purple", "cyan", "emerald", "amber", "pink", "red", "indigo"]
FileType = Literal["cv", "transcript", "note", "background"]
CandidateStatus = Literal["new", "screening", "interview", "offer", "hired", "rejected"]
AiTaskType = Literal[
    "candidate_summary",
    "candidate_comparison",
    "candidate_red_flags",
    "candidate_background_check",
]
AiTaskStatus = Literal["queued", "running", "completed", "failed"]


class Vacancy(BaseModel):
    id: str
    title: str
    department: str
    location: str
    type: VacancyType
    status: VacancyStatus
    description: str
    requirements: list[str]
    created_at: str = Field(alias="createdAt")
    candidates_count: int = Field(alias="candidatesCount")
    hires_target: int = Field(alias="hiresTarget")


class Tag(BaseModel):
    id: str
    label: str
    color: TagColor


class ExperienceItem(BaseModel):
    company: str
    role: str
    from_: str = Field(alias="from")
    to: str
    description: str


class EducationItem(BaseModel):
    institution: str
    degree: str
    field: str
    year: str


class SkillScore(BaseModel):
    skill: str
    score: int


class ParsedFields(BaseModel):
    summary: str
    skills: list[str]
    skill_scores: list[SkillScore] = Field(alias="skillScores")
    experience: list[ExperienceItem]
    education: list[EducationItem]
    languages: list[str]
    certifications: list[str]
    total_years_exp: int = Field(alias="totalYearsExp")


class CandidateFile(BaseModel):
    id: str
    type: FileType
    name: str
    content: str
    uploaded_at: str = Field(alias="uploadedAt")
    size: str


class Candidate(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    location: str
    avatar_initials: str = Field(alias="avatarInitials")
    avatar_color: str = Field(alias="avatarColor")
    vacancy_id: str = Field(alias="vacancyId")
    score: int
    relevancy_score: int = Field(alias="relevancyScore")
    tags: list[Tag]
    status: CandidateStatus
    parsed_fields: ParsedFields = Field(alias="parsedFields")
    files: list[CandidateFile]
    applied_at: str = Field(alias="appliedAt")
    linkedin_url: str | None = Field(default=None, alias="linkedinUrl")


class Message(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class AiTaskRequest(BaseModel):
    type: AiTaskType
    candidate_id: str | None = Field(default=None, alias="candidateId")
    candidate_ids: list[str] = Field(default_factory=list, alias="candidateIds")
    vacancy_id: str | None = Field(default=None, alias="vacancyId")
    prompt: str


class AiTaskRecord(BaseModel):
    id: str
    type: AiTaskType
    status: AiTaskStatus
    prompt: str
    candidate_id: str | None = Field(default=None, alias="candidateId")
    candidate_ids: list[str] = Field(default_factory=list, alias="candidateIds")
    vacancy_id: str | None = Field(default=None, alias="vacancyId")
    provider: str = "temporal_stub"
    workflow_id: str | None = Field(default=None, alias="workflowId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    result: dict[str, str] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    environment: str
    temporal_enabled: bool = Field(alias="temporalEnabled")


class PaginationMeta(BaseModel):
    total: int


class VacancyListResponse(BaseModel):
    items: list[Vacancy]
    meta: PaginationMeta


class CandidateListResponse(BaseModel):
    items: list[Candidate]
    meta: PaginationMeta


class MessageListResponse(BaseModel):
    items: list[Message]
    meta: PaginationMeta
