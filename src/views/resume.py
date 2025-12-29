from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonalInformation(BaseModel):
    """Personal information scraped from the resume."""

    model_config = ConfigDict(extra="allow")

    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    birthday: Optional[str] = None
    email: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    habr_career: Optional[str] = None
    sex: Optional[str] = None
    citizenship: Optional[str] = None
    legal_authorization: Optional[str] = None
    has_vehicle: Optional[bool] = None


class JobPreferences(BaseModel):
    """Job preference block scraped from the resume page."""

    model_config = ConfigDict(extra="allow")

    job_type: Optional[str] = None
    job_format: Optional[str] = None
    time_to_travel: Optional[str] = None
    readiness_to_job_trips: Optional[str] = None
    salary: Optional[str] = None


class Resume(BaseModel):
    """
    Resume data structure used across the app.

    This model matches the dictionary returned by
    `PlaywrightJobManager.get_resume_content_from_browser()` and is tolerant
    to extra keys (HH markup / scraping may evolve).
    """

    model_config = ConfigDict(extra="allow")

    # Nested structures
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    job_preferences: JobPreferences = Field(default_factory=JobPreferences)

    # Top-level scraped fields
    area: Optional[str] = None
    driving_license: Optional[str] = None
    citizenship: Optional[str] = None
    legal_authorization: Optional[str] = None

    # Core resume sections
    total_experience: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[str] = None
    educations: Optional[str] = None
    recommendations: Optional[str] = None
    additional_education: Optional[str] = None
    exams: Optional[str] = None
    certificates: Optional[str] = None
    about_me: Optional[str] = None
