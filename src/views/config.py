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

    @model_validator(mode="after")
    def validate_currency(self):
        if sum(self.model_dump().values()) > 1:
            raise ValueError("Только одно значение настроек currency может быть True")
        return self


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

    @model_validator(mode="after")
    def validate_experience(self):
        if sum(self.model_dump().values()) > 1:
            raise ValueError("Только одно значение настроек experience может быть True")
        return self


class Employment(BaseModel):
    FULL: bool = False
    PART: bool = False
    PROJECT: bool = False
    FLY_IN_FLY_OUT: bool = False
    INTERNSHIP: bool = False
    ACCEPT_TEMPORARY: bool = False


class JobFormat(BaseModel):
    ON_SITE: bool = False
    REMOTE: bool = False
    HYBRID: bool = False
    FIELD_WORK: bool = False


class VacancyLabel(BaseModel):
    with_address: bool = False
    accept_handicapped: bool = False
    not_from_agency: bool = False
    accept_kids: bool = False
    accept_teens: bool = False
    accredited_it: bool = False
    low_performance: bool = False


class OrderBy(BaseModel):
    relevance: bool = False
    publication_time: bool = False
    salary_desc: bool = False
    salary_asc: bool = False

    @model_validator(mode="after")
    def validate_order(self):
        if sum(self.model_dump().values()) > 1:
            raise ValueError("Только одно значение настроек order by может быть True")
        return self


class Show(BaseModel):
    show_20: bool = True
    show_50: bool = False
    show_100: bool = False

    @model_validator(mode="after")
    def validate_show(self):
        if sum(self.model_dump().values()) > 1:
            raise ValueError("Только одно значение настроек show может быть True")
        return self


class Period(BaseModel):
    all_time: bool = False
    month: bool = False
    week: bool = False
    three_days: bool = False
    one_day: bool = False

    @model_validator(mode="after")
    def validate_period(self):
        if sum(self.model_dump().values()) > 1:
            raise ValueError("Только одно значение настроек period может быть True")
        return self


class SearchConfig(BaseModel):
    # Optional fields
    job_title: Optional[str] = ""
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
    salary: Optional[int] = None
    only_with_salary: Optional[bool] = None
    currency: Optional[Currency] = None
    education: Optional[Education] = None
    job_format: Optional[JobFormat] = None
    vacancy_label: Optional[VacancyLabel] = None
    job_blacklist: Optional[Union[str, List[str]]] = []
    order_by: Optional[OrderBy] = None
    period: Optional[Period] = None
    show: Optional[Show] = None
    cover_letter: Optional[str] = None
    apply_once_at_company: Optional[bool] = True
    skip_companies_with_test: Optional[bool] = False
    max_applies_num: int = 100
    max_total_applies_num: Optional[int] = 1500


class Secrets(BaseModel):
    hh_login: str
    hh_password: str
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
