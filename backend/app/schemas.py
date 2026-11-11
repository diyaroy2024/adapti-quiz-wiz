"""Pydantic schemas — mirror src/lib/types.ts on the React side exactly."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
Language = Literal["en", "hi", "ta", "te", "mr"]
QuestionType = Literal["mcq", "fill", "descriptive"]
Difficulty = Literal["easy", "medium", "hard"]
EvidenceStatus = Literal["direct", "partial", "unsupported"]


class DifficultyMix(BaseModel):
    easy: int = 30
    medium: int = 50
    hard: int = 20


class PaperConfig(BaseModel):
    language: Language = "en"
    totalMarks: int = 50
    bloomLevels: List[BloomLevel] = Field(
        default_factory=lambda: ["remember", "understand", "apply"]
    )
    types: List[QuestionType] = Field(default_factory=lambda: ["mcq", "fill", "descriptive"])
    difficultyMix: DifficultyMix = Field(default_factory=DifficultyMix)
    topicHint: Optional[str] = None


class SourcePage(BaseModel):
    page: int = Field(ge=1)
    text: str


class GenerateRequest(BaseModel):
    text: str
    config: PaperConfig = Field(default_factory=PaperConfig)
    title: str = "Untitled Paper"
    sourceName: Optional[str] = None
    sourcePages: Optional[List[SourcePage]] = None


class GeneratedQuestion(BaseModel):
    id: str
    type: QuestionType
    bloom: BloomLevel
    difficulty: Difficulty
    marks: int
    question: str
    options: Optional[List[str]] = None
    answer: str
    keywords: Optional[List[str]] = None
    topic: Optional[str] = None
    co: Optional[str] = None
    sourceReference: Optional[str] = None
    sourceEvidence: Optional[str] = None
    evidenceStatus: Optional[EvidenceStatus] = None
    evidenceWarning: Optional[str] = None


class GeneratedPaper(BaseModel):
    id: str
    title: str
    createdAt: str
    config: PaperConfig
    questions: List[GeneratedQuestion]
    sourcePreview: str
    coverageReport: Optional[dict] = None
    # Post-processing transparency: drafted vs kept, and why drafts were dropped.
    qualityReport: Optional[dict] = None
