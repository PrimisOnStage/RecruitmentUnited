from pydantic import BaseModel, Field

class WorkExp(BaseModel):
    company: str = Field(default="")
    role: str = Field(default="")
    duration: str = Field(default="")

class Education(BaseModel):
    degree: str = Field(default="")
    institution: str = Field(default="")
    year: str = Field(default="")

class CandidateSchema(BaseModel):
    name: str = Field(description="Full name of candidate")
    email: str = Field(description="Email address", default="")
    phone: str = Field(description="Phone number", default="")
    country: str = Field(description="Country of residence", default="")
    location: str = Field(description="City or country", default="")
    current_role: str = Field(description="Most recent job title", default="")
    experience_years: int = Field(description="Total years of experience", default=0)
    skills: list[str] = Field(description="All technical and soft skills", default=[])
    work_history: list[WorkExp] = Field(default=[])
    education: list[Education] = Field(default=[])


class LinkedInIngestSchema(BaseModel):
    name: str = Field(description="Full name from LinkedIn profile")
    email: str = Field(description="Email used for candidate upsert")
    phone: str = Field(default="")
    country: str = Field(default="")
    location: str = Field(default="")
    current_role: str = Field(default="")
    experience_years: int = Field(default=0)
    skills: list[str] = Field(default=[])
    work_history: list[WorkExp] = Field(default=[])
    education: list[Education] = Field(default=[])
    profile_url: str = Field(default="")
    headline: str = Field(default="")
    about: str = Field(default="")
