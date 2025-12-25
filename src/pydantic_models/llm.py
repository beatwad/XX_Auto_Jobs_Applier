from pydantic import BaseModel, Field


class JobIsInteresting(BaseModel):
    score: int = Field(description="Suitability score from 1 to 100")
    reasoning: str = Field(description="Brief justification for the score")


class ResumeIsInteresting(BaseModel):
    demand_score: int = Field(description="Job market demand score from 1 to 10")
    resume_score: int = Field(description="Resume quality score from 1 to 10")
    solvency_score: int = Field(description="Potential solvency score from 1 to 10")
    reasoning: str = Field(description="Brief explanation of all three scores")


class ContactInfo(BaseModel):
    telegram: str = Field(description="Telegram username or link, or 'No info'")
    whatsapp: str = Field(description="WhatsApp number, or 'No info'")
    email: str = Field(description="Email address, or 'No info'")
    phone: str = Field(description="Phone number, or 'No info'")
    linkedin: str = Field(description="LinkedIn profile link, or 'No info'")
