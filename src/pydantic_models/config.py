from typing import List, Optional, Union

from pydantic import BaseModel, field_validator, model_validator


class SearchField(BaseModel):
    name: bool = False
    company_name: bool = False
    description: bool = False


class Currency(BaseModel):
    RUR: bool = False
    EUR: bool = False
    USD: bool = False


class Education(BaseModel):
    not_needed: bool = False
    middle: bool = False
    higher: bool = False


class Experience(BaseModel):
    doesntMatter: bool = False
    noExperience: bool = False
    between1And3: bool = False
    between3And6: bool = False
    moreThan6: bool = False

    # @model_validator(mode="after")
    # def validate_experience(cls, values):
    #     if sum(values.__dict__.values()) > 1:
    #         raise ValueError("Только одно значение настроек experience может быть True")
    #     return values


class Employment(BaseModel):
    full: bool = False
    part: bool = False
    project: bool = False
    volunteer: bool = False
    probation: bool = False


class Schedule(BaseModel):
    fullDay: bool = False
    shift: bool = False
    flexible: bool = False
    remote: bool = False
    flyInFlyOut: bool = False


class PartTime(BaseModel):
    project: bool = False
    part: bool = False
    from_four_to_six_hours_in_a_day: bool = False
    only_saturday_and_sunday: bool = False
    start_after_sixteen: bool = False


class VacancyLabel(BaseModel):
    with_address: bool = False
    accept_handicapped: bool = False
    not_from_agency: bool = False
    accept_kids: bool = False
    accredited_it: bool = False
    low_performance: bool = False


class OrderBy(BaseModel):
    relevance: bool = False
    publication_time: bool = False
    salary_desc: bool = False
    salary_asc: bool = False

    @model_validator(mode="after")
    def validate_order(cls, values):
        if sum(values.__dict__.values()) > 1:
            raise ValueError("Только одно значение настроек order by может быть True")
        return values


class Period(BaseModel):
    all_time: bool = False
    month: bool = False
    week: bool = False
    three_days: bool = False
    one_day: bool = False

    @model_validator(mode="after")
    def validate_period(cls, values):
        if sum(values.__dict__.values()) > 1:
            raise ValueError("Только одно значение настроек period может быть True")
        return values


class SearchConfig(BaseModel):
    # Optional fields
    job_title: Optional[str] = ""
    user_id: Optional[str] = ""
    resume_id: Optional[str] = ""
    keywords: Optional[str] = ""
    experience: Optional[Experience] = None
    employment: Optional[Employment] = None
    search_field: Optional[SearchField] = None
    words_to_exclude: Optional[str] = ""
    professional_role: Optional[str] = ""
    industry: Optional[str] = ""
    area: Optional[str] = ""
    districts: Optional[str] = ""
    metro: Optional[str] = ""
    salary: Optional[int] = None
    only_with_salary: Optional[bool] = None
    currency: Optional[Currency] = None
    education: Optional[Education] = None
    schedule: Optional[Schedule] = None
    part_time: Optional[PartTime] = None
    vacancy_label: Optional[VacancyLabel] = None
    job_blacklist: Optional[Union[str, List[str]]] = []
    order_by: Optional[OrderBy] = None
    period: Optional[Period] = None
    cover_letter: Optional[str] = None
    apply_once_at_company: Optional[bool] = True
    skip_companies_with_test: Optional[bool] = False
    max_applies_num: int = 100
    max_total_applies_num: Optional[int] = 1500


class Secrets(BaseModel):
    access_token: str
    refresh_token: str
    hh_login: Optional[str] = ""
    hh_password: Optional[str] = ""
    llm_api_key: str
    llm_proxy: List[str]
    tg_token: str
    tg_api_id: Optional[str] = ""
    tg_api_hash: Optional[str] = ""

    @field_validator("tg_api_id", mode="before")
    @classmethod
    def validate_tg_api_id(cls, v):
        if isinstance(v, int):
            return str(v)
        elif isinstance(v, str):
            return v
        else:
            raise ValueError("tg_api_id должно быть строкой или числом")
