from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeContacts(BaseModel):
    """Contacts scraped from HH profile/resume pages."""

    model_config = ConfigDict(extra="allow")

    telegram: str = ""
    whatsapp: str = ""
    phone: str = ""
    email: str = ""


class JobPreferences(BaseModel):
    """Job preference block scraped from the resume page."""

    model_config = ConfigDict(extra="allow")

    job_type: str = ""
    job_format: str = ""
    time_to_travel: str = ""
    readiness_to_job_trips: str = ""
    salary: str = ""


class Resume(BaseModel):
    """
    Resume data structure used across the app.

    This model matches the dictionary returned by
    `PlaywrightJobManager.get_resume_content_from_browser()` and is tolerant
    to extra keys (HH markup / scraping may evolve).
    """

    model_config = ConfigDict(extra="allow")

    # Profile basics
    first_name: str = ""
    last_name: str = ""
    area: str = ""
    driving_license: str = ""

    # Contacts & preferences
    contacts: ResumeContacts = Field(default_factory=ResumeContacts)
    job_preferences: JobPreferences = Field(default_factory=JobPreferences)

    # Core resume sections (currently scraped as plain text blobs)
    total_experience: str = ""
    experience: str = ""
    skills: str = ""
    educations: str = ""
    recommendations: str = ""
    additional_education: str = ""
    exams: str = ""
    certificates: str = ""
    about_me: str = ""

    # Optional / API-shaped compatibility fields (may be present in other flows)
    next_publish_at: Optional[str] = None
    personal_information: Optional[Dict[str, Any]] = None
