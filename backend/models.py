"""Pydantic models that describe candidate-shaped payloads.

These schemas are shared by multiple ingestion sources so the backend, Llama
extraction agent, and API validation all agree on the same basic structure.
"""

from enum import Enum

from pydantic import BaseModel, Field


class CandidateStage(str, Enum):
    """Allowed pipeline stages for candidate progression across the application."""

    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"

class WorkExp(BaseModel):
    """A simplified work-experience record used in metadata payloads."""
    company: str = Field(default="")
    role: str = Field(default="")
    duration: str = Field(default="")

class Education(BaseModel):
    """A simplified education record extracted from resumes/LinkedIn."""
    degree: str = Field(default="")
    institution: str = Field(default="")
    year: str = Field(default="")

class CandidateSchema(BaseModel):
    """Canonical candidate shape used by the resume extractor."""
    name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address", default="")
    phone: str = Field(description="Phone number", default="")
    country: str = Field(description="Country of residence", default="")
    location: str = Field(description="City or country", default="")
    current_role: str = Field(description="Most recent job title", default="")
    experience_years: int = Field(description="Total years of experience", default=0, ge=0)
    skills: list[str] = Field(description="All technical and soft skills", default_factory=list)
    work_history: list[WorkExp] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)


class LinkedInIngestSchema(BaseModel):
    """Request model accepted by the LinkedIn ingestion endpoint."""
    name: str = Field(description="Full name from LinkedIn profile")
    email: str = Field(description="Email used for candidate upsert")
    phone: str = Field(default="")
    country: str = Field(default="")
    location: str = Field(default="")
    current_role: str = Field(default="")
    experience_years: int = Field(default=0, ge=0)
    skills: list[str] = Field(default_factory=list)
    work_history: list[WorkExp] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    profile_url: str = Field(default="")
    headline: str = Field(default="")
    about: str = Field(default="")
