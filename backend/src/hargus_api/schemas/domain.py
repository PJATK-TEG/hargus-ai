from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    "candidate_query",
]
AiTaskStatus = Literal["queued", "running", "completed", "failed"]
BackgroundSource = Literal[
    "courtlistener",
    "recap",
    "fbi_cde",
    "openalex",
    "crossref",
    "orcid",
    "wos",
]


class Vacancy(BaseModel):
    model_config = {"populate_by_name": True}
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


class VacancyCreate(BaseModel):
    model_config = {"populate_by_name": True}
    title: str
    department: str
    location: str
    type: VacancyType
    description: str
    requirements: list[str]
    hires_target: int = Field(1, alias="hiresTarget")


class VacancyUpdate(BaseModel):
    model_config = {"populate_by_name": True}
    title: str | None = None
    department: str | None = None
    location: str | None = None
    type: VacancyType | None = None
    status: VacancyStatus | None = None
    description: str | None = None
    requirements: list[str] | None = None
    hires_target: int | None = Field(default=None, alias="hiresTarget")


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
    model_config = {"populate_by_name": True}
    id: str
    type: FileType
    name: str
    content: str
    uploaded_at: str = Field(alias="uploadedAt")
    size: str


class Candidate(BaseModel):
    model_config = {"populate_by_name": True}
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
    # Prompt is optional: when omitted the backend loads it from analysis_config.
    prompt: str = ""

    @model_validator(mode="after")
    def validate_candidates(self) -> "AiTaskRequest":
        if self.candidate_id is None and not self.candidate_ids:
            raise ValueError("Either candidateId or candidateIds must be provided")
        return self


class BackgroundCheckRequest(BaseModel):
    candidate_id: str | None = Field(default=None, alias="candidateId")
    candidate_ids: list[str] = Field(default_factory=list, alias="candidateIds")
    vacancy_id: str | None = Field(default=None, alias="vacancyId")
    prompt: str | None = None
    sources: list[BackgroundSource] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_candidates(self) -> "BackgroundCheckRequest":
        if self.candidate_id is None and not self.candidate_ids:
            raise ValueError("Either candidateId or candidateIds must be provided")
        return self


class BackgroundSourceSearchRequest(BaseModel):
    candidate_id: str | None = Field(default=None, alias="candidateId")
    candidate_ids: list[str] = Field(default_factory=list, alias="candidateIds")
    vacancy_id: str | None = Field(default=None, alias="vacancyId")
    query: str

    @model_validator(mode="after")
    def validate_candidates(self) -> "BackgroundSourceSearchRequest":
        if self.candidate_id is None and not self.candidate_ids:
            raise ValueError("Either candidateId or candidateIds must be provided")
        return self


class BackgroundSourceInfo(BaseModel):
    id: BackgroundSource
    name: str
    category: Literal["legal", "scholarly"]
    requires_api_key: bool = Field(alias="requiresApiKey")


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


class AnalysisReportResponse(BaseModel):
    id: str
    candidate_id: str = Field(alias="candidateId")
    vacancy_id: str = Field(alias="vacancyId")
    overall_score: float = Field(alias="overallScore")
    skill_match_score: float = Field(alias="skillMatchScore")
    experience_score: float = Field(alias="experienceScore")
    recommendation: str
    has_pdf: bool = Field(alias="hasPdf")
    created_at: datetime = Field(alias="createdAt")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app: str
    environment: str
    temporal_enabled: bool = Field(alias="temporalEnabled")


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    returned: int


class VacancyListResponse(BaseModel):
    items: list[Vacancy]
    meta: PaginationMeta


class CandidateListResponse(BaseModel):
    items: list[Candidate]
    meta: PaginationMeta


class MessageListResponse(BaseModel):
    items: list[Message]
    meta: PaginationMeta


class BackgroundSourceListResponse(BaseModel):
    items: list[BackgroundSourceInfo]



class CandidateQueryRequest(BaseModel):
    model_config = {"populate_by_name": True}
    query: str
    vacancy_id: str = Field("", alias="vacancyId")


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "recruiter"


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}
    id: str
    email: str
    name: str
    role: str
    created_at: datetime = Field(alias="createdAt")


class TokenResponse(BaseModel):
    model_config = {"populate_by_name": True}
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    user: UserResponse
