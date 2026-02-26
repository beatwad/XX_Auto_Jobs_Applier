from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.job_manager.job_applier import JobApplier


@pytest.fixture
def mock_manager():
    manager = MagicMock()
    manager.get_vacancy_full_info = AsyncMock()
    manager.get_vacancies_from_page = AsyncMock()
    manager.apply_to_vacancy = AsyncMock()
    return manager


@pytest.fixture
def mock_resume_component():
    component = MagicMock()
    component.job_title = "Python Developer"
    return component


@pytest.fixture
def mock_search_component():
    component = MagicMock()
    component.start_search = AsyncMock()
    return component


@pytest.fixture
def applier(mock_manager, mock_resume_component, mock_search_component):
    return JobApplier(mock_manager, mock_resume_component, mock_search_component)


@pytest.fixture
def applier_with_params(applier):
    """JobApplier с установленными параметрами (файловый I/O замокан)."""
    resume_id = "resume123"
    with (
        patch.object(applier, "_load_companies_from_yaml", return_value={resume_id: {}}),
        patch.object(applier, "_load_data_from_yaml", return_value={}),
        patch.object(applier, "_load_seen_job_descriptions_from_file", return_value=[]),
        patch.object(applier, "_load_cache", return_value={}),
        patch.object(applier, "_check_the_previous_apply_number", return_value=0),
    ):
        applier.set_parameters(
            {
                "resume_id": resume_id,
                "resume_titles": ["Python Developer"],
                "max_applies_num": 10,
                "max_total_applies_num": 1500,
            }
        )
    applier.gpt_answerer = MagicMock()
    return applier


def _make_vacancy(
    name="Python Dev",
    vacancy_id="vac1",
    company_id="comp1",
    company_name="TestCo",
    url="https://hh.ru/1",
):
    return {
        "name": name,
        "id": vacancy_id,
        "employer": {"id": company_id, "name": company_name},
        "alternate_url": url,
    }


def _make_job(
    job_title="Python Dev",
    vacancy_id="vac1",
    company_id="comp1",
    company_name="TestCo",
    skills="python",
    description="Описание вакансии",
):
    return {
        "job_title": job_title,
        "vacancy_id": vacancy_id,
        "company_id": company_id,
        "company_name": company_name,
        "skills": skills,
        "description": description,
    }


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_sets_attributes(self, mock_manager, mock_resume_component, mock_search_component):
        ja = JobApplier(mock_manager, mock_resume_component, mock_search_component)

        assert ja.manager is mock_manager
        assert ja.resume_component is mock_resume_component
        assert ja.search_component is mock_search_component
        assert ja.gpt_answerer is None
        assert ja.jobs_no_info == []
        assert ja.resume_recommendations == ""
        assert ja.job_key_skills == []
        assert ja.page_num == 0
        assert ja.error_num == 0
        assert ja.total_applies_num == 0


# ---------------------------------------------------------------------------
# set_parameters
# ---------------------------------------------------------------------------


class TestSetParameters:
    def test_sets_required_fields(self, applier_with_params):
        assert applier_with_params.resume_id == "resume123"
        assert applier_with_params.resume_titles == ["Python Developer"]
        assert applier_with_params.max_applies_num == 10
        assert applier_with_params.job_title == "Python Developer"

    def test_sets_defaults(self, applier_with_params):
        assert applier_with_params.apply_once_at_company is True
        assert applier_with_params.skip_companies_with_test is False
        assert applier_with_params.job_blacklist == []
        assert applier_with_params.applies_num == 0

    def test_sanitizes_blacklist(self, applier, mock_resume_component):
        mock_resume_component.job_title = "Python Developer"
        with (
            patch.object(applier, "_load_companies_from_yaml", return_value={"resume123": {}}),
            patch.object(applier, "_load_data_from_yaml", return_value={}),
            patch.object(applier, "_load_seen_job_descriptions_from_file", return_value=[]),
            patch.object(applier, "_load_cache", return_value={}),
            patch.object(applier, "_check_the_previous_apply_number", return_value=0),
        ):
            applier.set_parameters(
                {
                    "resume_id": "resume123",
                    "resume_titles": [],
                    "job_blacklist": ["Bad Company", '"Quoted Co"'],
                }
            )

        assert "bad company" in applier.job_blacklist
        assert "quoted co" in applier.job_blacklist


# ---------------------------------------------------------------------------
# _sanitize_text
# ---------------------------------------------------------------------------


class TestSanitizeText:
    def test_lowercases_and_strips(self, applier):
        assert applier._sanitize_text("  Hello World  ") == "hello world"

    def test_removes_quotes(self, applier):
        assert applier._sanitize_text('"test"') == "test"

    def test_removes_backslash(self, applier):
        assert applier._sanitize_text("test\\value") == "testvalue"

    def test_removes_control_chars(self, applier):
        assert applier._sanitize_text("test\x00value") == "testvalue"

    def test_removes_newline(self, applier):
        # \n попадает в диапазон [\x00-\x1F] и удаляется regex-ом до замены на пробел
        assert applier._sanitize_text("test\nvalue") == "testvalue"

    def test_strips_trailing_comma(self, applier):
        assert applier._sanitize_text("test,") == "test"

    def test_empty_string(self, applier):
        assert applier._sanitize_text("") == ""


# ---------------------------------------------------------------------------
# _process_skill_string
# ---------------------------------------------------------------------------


class TestProcessSkillString:
    def test_splits_on_comma_space(self, applier):
        assert applier._process_skill_string("Python, SQL, Docker") == ["python", "sql", "docker"]

    def test_lowercases(self, applier):
        assert applier._process_skill_string("Python") == ["python"]

    def test_removes_non_alphanumeric_except_spaces(self, applier):
        result = applier._process_skill_string("C++, Node.js")
        assert result == ["c", "nodejs"]

    def test_empty_string(self, applier):
        assert applier._process_skill_string("") == []

    def test_skips_blank_parts(self, applier):
        assert applier._process_skill_string("Python, , SQL") == ["python", "sql"]


# ---------------------------------------------------------------------------
# _is_blacklisted
# ---------------------------------------------------------------------------


class TestIsBlacklisted:
    def test_returns_true_for_blacklisted_company(self, applier_with_params):
        applier_with_params.job_blacklist = ["bad company"]
        assert applier_with_params._is_blacklisted("bad company") is True

    def test_returns_false_for_unknown_company(self, applier_with_params):
        applier_with_params.job_blacklist = ["bad company"]
        assert applier_with_params._is_blacklisted("good company") is False

    def test_returns_false_for_empty_blacklist(self, applier_with_params):
        applier_with_params.job_blacklist = []
        assert applier_with_params._is_blacklisted("any company") is False


# ---------------------------------------------------------------------------
# _is_already_applied_to_job_or_company
# ---------------------------------------------------------------------------


class TestIsAlreadyAppliedToJobOrCompany:
    def test_returns_false_for_new_company(self, applier_with_params):
        applier_with_params.success_companies = {"resume123": {}}
        is_applied, _ = applier_with_params._is_already_applied_to_job_or_company(_make_job())
        assert is_applied is False

    def test_skips_company_when_apply_once_at_company(self, applier_with_params):
        applier_with_params.apply_once_at_company = True
        applier_with_params.success_companies = {
            "resume123": {"comp1": [{"vacancy_id": "vac1", "job_title": "Python Dev"}]}
        }
        is_applied, reason = applier_with_params._is_already_applied_to_job_or_company(_make_job())
        assert is_applied is True
        assert reason != ""

    def test_skips_seen_vacancy_by_id_when_apply_once_disabled(self, applier_with_params):
        applier_with_params.apply_once_at_company = False
        applier_with_params.success_companies = {
            "resume123": {"comp1": [{"vacancy_id": "vac1", "job_title": "Other Title"}]}
        }
        is_applied, _ = applier_with_params._is_already_applied_to_job_or_company(_make_job())
        assert is_applied is True

    def test_skips_seen_vacancy_by_title_when_apply_once_disabled(self, applier_with_params):
        applier_with_params.apply_once_at_company = False
        applier_with_params.success_companies = {
            "resume123": {"comp1": [{"vacancy_id": "vac99", "job_title": "Python Dev"}]}
        }
        is_applied, _ = applier_with_params._is_already_applied_to_job_or_company(_make_job())
        assert is_applied is True

    def test_matches_company_by_name_when_no_id(self, applier_with_params):
        applier_with_params.apply_once_at_company = True
        applier_with_params.success_companies = {
            "resume123": {"TestCo": [{"vacancy_id": "vac1", "job_title": "Python Dev"}]}
        }
        is_applied, _ = applier_with_params._is_already_applied_to_job_or_company(
            _make_job(company_id=None)
        )
        assert is_applied is True

    def test_returns_false_for_different_company_and_vacancy(self, applier_with_params):
        applier_with_params.apply_once_at_company = False
        applier_with_params.success_companies = {
            "resume123": {"comp2": [{"vacancy_id": "vac99", "job_title": "Java Dev"}]}
        }
        is_applied, _ = applier_with_params._is_already_applied_to_job_or_company(_make_job())
        assert is_applied is False


# ---------------------------------------------------------------------------
# _job_description_is_already_met
# ---------------------------------------------------------------------------


class TestJobDescriptionIsAlreadyMet:
    def test_returns_true_for_seen_vacancy(self, applier):
        applier.seen_job_descriptions = [{"vacancy_id": "vac1"}]
        is_met, _ = applier._job_description_is_already_met("vac1")
        assert is_met is True

    def test_returns_false_for_unseen_vacancy(self, applier):
        applier.seen_job_descriptions = [{"vacancy_id": "vac1"}]
        is_met, _ = applier._job_description_is_already_met("vac2")
        assert is_met is False

    def test_returns_false_for_empty_list(self, applier):
        applier.seen_job_descriptions = []
        is_met, _ = applier._job_description_is_already_met("vac1")
        assert is_met is False


# ---------------------------------------------------------------------------
# _collect_job_info
# ---------------------------------------------------------------------------


class TestCollectJobInfo:
    def test_appends_job_info(self, applier):
        applier.jobs_no_info = []
        applier._collect_job_info("Python Dev", "https://hh.ru/1", "Нет информации")

        assert len(applier.jobs_no_info) == 1
        info = applier.jobs_no_info[0]
        assert info["job_title"] == "Python Dev"
        assert info["link"] == "https://hh.ru/1"
        assert info["reason"] == "Нет информации"

    def test_appends_multiple_entries(self, applier):
        applier.jobs_no_info = []
        applier._collect_job_info("Dev 1", "https://hh.ru/1", "Причина 1")
        applier._collect_job_info("Dev 2", "https://hh.ru/2", "Причина 2")
        assert len(applier.jobs_no_info) == 2


# ---------------------------------------------------------------------------
# _add_job_info_to_seen_companies
# ---------------------------------------------------------------------------


class TestAddJobInfoToSeenCompanies:
    def test_appends_new_vacancy(self, applier):
        job_info = {"vacancy_id": "vac2", "job_title": "New Job"}
        company_vacancies = [{"vacancy_id": "vac1", "job_title": "Old Job"}]
        applier._add_job_info_to_seen_companies(job_info, company_vacancies)
        assert len(company_vacancies) == 2

    def test_skips_duplicate_vacancy(self, applier):
        job_info = {"vacancy_id": "vac1", "job_title": "Same Job"}
        company_vacancies = [{"vacancy_id": "vac1", "job_title": "Old Job"}]
        applier._add_job_info_to_seen_companies(job_info, company_vacancies)
        assert len(company_vacancies) == 1


# ---------------------------------------------------------------------------
# _save_company
# ---------------------------------------------------------------------------


class TestSaveCompany:
    def test_routes_success_to_success_file(self, applier_with_params):
        vacancy = {"alternate_url": "https://hh.ru/1"}
        with patch.object(applier_with_params, "_save_company_to_yaml") as mock_save:
            applier_with_params._save_company(_make_job(), ("Success", "Применено"), vacancy)
        mock_save.assert_called_once_with("success.yaml", applier_with_params.success_companies)

    def test_routes_skip_to_skipped_file(self, applier_with_params):
        vacancy = {"alternate_url": "https://hh.ru/1"}
        with patch.object(applier_with_params, "_save_company_to_yaml") as mock_save:
            applier_with_params._save_company(_make_job(), ("Skip", "Пропущено"), vacancy)
        mock_save.assert_called_once_with("skipped.yaml", applier_with_params.skipped_companies)

    def test_routes_error_to_failed_file(self, applier_with_params):
        vacancy = {"alternate_url": "https://hh.ru/1"}
        with patch.object(applier_with_params, "_save_company_to_yaml") as mock_save:
            applier_with_params._save_company(_make_job(), ("Error", "Ошибка"), vacancy)
        mock_save.assert_called_once_with("failed.yaml", applier_with_params.failed_companies)

    def test_uses_company_name_as_key_when_no_company_id(self, applier_with_params):
        vacancy = {"alternate_url": "https://hh.ru/1"}
        with patch.object(applier_with_params, "_save_company_to_yaml"):
            applier_with_params._save_company(_make_job(company_id=None), ("Success", ""), vacancy)
        seen = applier_with_params.success_companies.get("resume123", {})
        assert "TestCo" in seen

    def test_appends_to_existing_company_entry(self, applier_with_params):
        applier_with_params.success_companies = {
            "resume123": {"comp1": [{"vacancy_id": "vac0", "job_title": "Old Dev"}]}
        }
        vacancy = {"alternate_url": "https://hh.ru/2"}
        with patch.object(applier_with_params, "_save_company_to_yaml"):
            applier_with_params._save_company(
                _make_job(vacancy_id="vac2"), ("Success", ""), vacancy
            )
        seen = applier_with_params.success_companies["resume123"]["comp1"]
        assert len(seen) == 2


# ---------------------------------------------------------------------------
# check_the_last_search_time
# ---------------------------------------------------------------------------


class TestCheckTheLastSearchTime:
    def test_returns_true_when_no_last_run(self, applier_with_params):
        applier_with_params.cache = {}
        assert applier_with_params.check_the_last_search_time() is True

    def test_returns_true_when_24h_elapsed(self, applier_with_params):
        applier_with_params.cache = {"last_run": (datetime.now() - timedelta(hours=25)).isoformat()}
        applier_with_params.previous_apply_number = 0
        assert applier_with_params.check_the_last_search_time() is True

    def test_returns_false_when_less_than_24h_and_no_previous_applies(self, applier_with_params):
        applier_with_params.cache = {"last_run": (datetime.now() - timedelta(hours=12)).isoformat()}
        applier_with_params.previous_apply_number = 0
        assert applier_with_params.check_the_last_search_time() is False

    def test_returns_true_when_previous_applies_exist(self, applier_with_params):
        applier_with_params.cache = {"last_run": (datetime.now() - timedelta(hours=12)).isoformat()}
        applier_with_params.previous_apply_number = 5
        assert applier_with_params.check_the_last_search_time() is True


# ---------------------------------------------------------------------------
# _check_the_previous_apply_number
# ---------------------------------------------------------------------------


class TestCheckThePreviousApplyNumber:
    def test_returns_zero_when_no_last_apply(self, applier):
        applier.cache = {}
        assert applier._check_the_previous_apply_number() == 0

    def test_returns_count_when_apply_was_recent(self, applier):
        applier.cache = {
            "last_apply": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "success_applies_num": 7,
        }
        assert applier._check_the_previous_apply_number() == 7

    def test_returns_zero_when_apply_was_long_ago(self, applier):
        applier.cache = {
            "last_apply": (datetime.now() - timedelta(hours=2)).isoformat(),
            "success_applies_num": 7,
        }
        assert applier._check_the_previous_apply_number() == 0


# ---------------------------------------------------------------------------
# _update_skill_stat
# ---------------------------------------------------------------------------


class TestUpdateSkillStat:
    def test_adds_new_skills(self, applier_with_params):
        applier_with_params.skill_stat = {}
        with patch.object(applier_with_params, "_save_data_to_yaml"):
            applier_with_params._update_skill_stat(["python", "sql"])
        assert applier_with_params.skill_stat["python"] == 1
        assert applier_with_params.skill_stat["sql"] == 1

    def test_increments_existing_skills(self, applier_with_params):
        applier_with_params.skill_stat = {"python": 3}
        with patch.object(applier_with_params, "_save_data_to_yaml"):
            applier_with_params._update_skill_stat(["python"])
        assert applier_with_params.skill_stat["python"] == 4

    def test_sorts_by_count_descending(self, applier_with_params):
        applier_with_params.skill_stat = {"sql": 5, "python": 1}
        with patch.object(applier_with_params, "_save_data_to_yaml"):
            applier_with_params._update_skill_stat(["python"])
        keys = list(applier_with_params.skill_stat.keys())
        assert keys[0] == "sql"
        assert keys[1] == "python"

    def test_empty_skills_list_leaves_stat_unchanged(self, applier_with_params):
        applier_with_params.skill_stat = {"python": 2}
        with patch.object(applier_with_params, "_save_data_to_yaml"):
            applier_with_params._update_skill_stat([])
        assert applier_with_params.skill_stat["python"] == 2


# ---------------------------------------------------------------------------
# _define_output_file
# ---------------------------------------------------------------------------


class TestDefineOutputFile:
    def test_returns_path_inside_output_folder(self):
        result = str(JobApplier._define_output_file("test.yaml"))
        assert "data_folder/output" in result
        assert "test.yaml" in result


# ---------------------------------------------------------------------------
# _load_seen_job_descriptions_from_file
# ---------------------------------------------------------------------------


class TestLoadSeenJobDescriptionsFromFile:
    def test_returns_empty_list_when_file_not_found(self, applier):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = applier._load_seen_job_descriptions_from_file("job_descriptions.txt")
        assert result == []

    def test_parses_single_job_block(self, applier):
        content = (
            "=" * 80 + "\n"
            "Компания: ТестКо\n"
            "Вакансия: Python Dev\n"
            "ID вакансии: vac123\n"
            "Оценка вакансии: 85\n"
            "Навыки: python, sql\n"
            "Ссылка: https://hh.ru/1\n"
            "Сопроводительное письмо:\n\n"
            "Уважаемые коллеги!\n\n"
        )
        with patch("builtins.open", mock_open(read_data=content)):
            result = applier._load_seen_job_descriptions_from_file("job_descriptions.txt")

        assert len(result) == 1
        assert result[0]["company_name"] == "ТестКо"
        assert result[0]["job_title"] == "Python Dev"
        assert result[0]["vacancy_id"] == "vac123"
        assert result[0]["job_score"] == 85
        assert result[0]["link"] == "https://hh.ru/1"

    def test_parses_skills_into_list(self, applier):
        content = (
            "=" * 80 + "\n"
            "Компания: TestCo\n"
            "Вакансия: Dev\n"
            "ID вакансии: v1\n"
            "Оценка вакансии: 70\n"
            "Навыки: python, docker, kubernetes\n"
            "Ссылка: https://hh.ru/1\n"
            "Сопроводительное письмо:\n\n"
        )
        with patch("builtins.open", mock_open(read_data=content)):
            result = applier._load_seen_job_descriptions_from_file("job_descriptions.txt")

        assert result[0]["skills"] == ["python", "docker", "kubernetes"]

    def test_skips_empty_blocks(self, applier):
        content = "=" * 80 + "\n" + "=" * 80 + "\n"
        with patch("builtins.open", mock_open(read_data=content)):
            result = applier._load_seen_job_descriptions_from_file("job_descriptions.txt")
        assert result == []

    def test_handles_invalid_job_score(self, applier):
        content = (
            "=" * 80 + "\n"
            "Компания: TestCo\n"
            "Вакансия: Dev\n"
            "ID вакансии: v1\n"
            "Оценка вакансии: не число\n"
            "Навыки: python\n"
            "Ссылка: https://hh.ru/1\n"
            "Сопроводительное письмо:\n\n"
        )
        with patch("builtins.open", mock_open(read_data=content)):
            result = applier._load_seen_job_descriptions_from_file("job_descriptions.txt")
        assert result[0]["job_score"] == 0


# ---------------------------------------------------------------------------
# scrape_vacancy
# ---------------------------------------------------------------------------


class TestScrapeVacancy:
    @pytest.mark.asyncio
    async def test_builds_job_with_all_fields(self, applier):
        applier.manager.get_vacancy_full_info = AsyncMock(
            return_value={"description": "Текст", "skills": "Python"}
        )
        result = await applier.scrape_vacancy(_make_vacancy())

        assert result["job_title"] == "Python Dev"
        assert result["vacancy_id"] == "vac1"
        assert result["company_id"] == "comp1"
        assert result["company_name"] == "TestCo"
        assert result["description"] == "Текст"

    @pytest.mark.asyncio
    async def test_handles_missing_employer(self, applier):
        applier.manager.get_vacancy_full_info = AsyncMock(return_value={})
        vacancy = {
            "name": "Python Dev",
            "id": "vac1",
            "employer": None,
            "alternate_url": "https://hh.ru/1",
        }
        result = await applier.scrape_vacancy(vacancy)

        assert result["company_name"] == "Unknown"
        assert result["company_id"] is None

    @pytest.mark.asyncio
    async def test_continues_when_full_info_fails(self, applier):
        applier.manager.get_vacancy_full_info = AsyncMock(side_effect=Exception("Ошибка сети"))
        result = await applier.scrape_vacancy(_make_vacancy())

        assert result["job_title"] == "Python Dev"
        assert result["company_name"] == "TestCo"


# ---------------------------------------------------------------------------
# apply_job
# ---------------------------------------------------------------------------


class TestApplyJob:
    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    async def test_uses_fixed_cover_letter_without_calling_llm(self, applier_with_params):
        applier_with_params.fixed_cover_letter = "Готовое письмо"
        applier_with_params.manager.apply_to_vacancy = AsyncMock(return_value=("Success", ""))

        result = await applier_with_params.apply_job(
            _make_vacancy(), "TestCo", "Python Dev", _make_job(), {"score": 80}
        )

        assert result == ("Success", "")
        applier_with_params.gpt_answerer.write_cover_letter.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    async def test_generates_cover_letter_when_no_fixed(self, applier_with_params):
        applier_with_params.fixed_cover_letter = None
        applier_with_params.gpt_answerer.write_cover_letter.return_value = "Письмо от LLM"
        applier_with_params.resume_component.deanonymize_personal_information.return_value = (
            "Письмо от LLM"
        )
        applier_with_params.manager.apply_to_vacancy = AsyncMock(return_value=("Success", ""))

        with patch.object(applier_with_params, "_save_job_description"):
            result = await applier_with_params.apply_job(
                _make_vacancy(), "TestCo", "Python Dev", _make_job(), {"score": 80}
            )

        applier_with_params.gpt_answerer.write_cover_letter.assert_called_once()
        assert result == ("Success", "")

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", True)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    async def test_search_mode_skips_and_updates_skills(self, applier_with_params):
        applier_with_params.fixed_cover_letter = None
        applier_with_params.gpt_answerer.write_cover_letter.return_value = "Письмо"
        applier_with_params.resume_component.deanonymize_personal_information.return_value = (
            "Письмо"
        )

        with (
            patch.object(applier_with_params, "_save_job_description"),
            patch.object(applier_with_params, "_update_skill_stat") as mock_update,
        ):
            result = await applier_with_params.apply_job(
                _make_vacancy(), "TestCo", "Python Dev", _make_job(), {"score": 80}
            )

        assert result == ("Skip", "SEARCH_MODE")
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", True)
    async def test_skill_stat_mode_skips_and_updates_skills(self, applier_with_params):
        applier_with_params.fixed_cover_letter = None
        applier_with_params.gpt_answerer.extract_skills_from_vacancy.return_value = ["docker"]

        with patch.object(applier_with_params, "_update_skill_stat") as mock_update:
            result = await applier_with_params.apply_job(
                _make_vacancy(),
                "TestCo",
                "Python Dev",
                _make_job(skills="python"),
                {"score": 80},
            )

        assert result == ("Skip", "SKILL_STAT_MODE")
        mock_update.assert_called_once()
        called_skills = mock_update.call_args[0][0]
        assert "python" in called_skills
        assert "docker" in called_skills

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    async def test_returns_error_on_exception(self, applier_with_params):
        applier_with_params.fixed_cover_letter = None
        applier_with_params.gpt_answerer.write_cover_letter.side_effect = Exception("LLM упал")

        result = await applier_with_params.apply_job(
            _make_vacancy(), "TestCo", "Python Dev", _make_job(), {"score": 80}
        )

        assert result[0] == "Error"
        assert "LLM упал" in result[1]


# ---------------------------------------------------------------------------
# send_repsonse
# ---------------------------------------------------------------------------


class TestSendResponse:
    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    @patch("src.job_manager.job_applier.MONKEY_MODE", False)
    @patch("src.job_manager.job_applier.time")
    @patch("src.job_manager.job_applier.sleep")
    async def test_skips_already_applied_vacancy(self, mock_sleep, mock_time, applier_with_params):
        mock_time.time.return_value = 0
        applier_with_params.success_companies = {
            "resume123": {"comp1": [{"vacancy_id": "vac1", "job_title": "Python Dev"}]}
        }
        applier_with_params.apply_once_at_company = True

        with (
            patch.object(
                applier_with_params, "scrape_vacancy", new=AsyncMock(return_value=_make_job())
            ),
            patch.object(applier_with_params, "_save_company"),
            patch("src.job_manager.job_applier.pause"),
        ):
            result = await applier_with_params.send_repsonse(_make_vacancy())

        assert result == "Skip"

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    @patch("src.job_manager.job_applier.MONKEY_MODE", True)
    @patch("src.job_manager.job_applier.time")
    @patch("src.job_manager.job_applier.sleep")
    async def test_applies_successfully_in_monkey_mode(
        self, mock_sleep, mock_time, applier_with_params
    ):
        mock_time.time.return_value = 0
        applier_with_params.success_companies = {"resume123": {}}
        applier_with_params.manager.apply_to_vacancy = AsyncMock(return_value=("Success", ""))
        applier_with_params.fixed_cover_letter = "Письмо"

        with (
            patch.object(
                applier_with_params, "scrape_vacancy", new=AsyncMock(return_value=_make_job())
            ),
            patch.object(applier_with_params, "_save_company"),
        ):
            result = await applier_with_params.send_repsonse(_make_vacancy())

        assert result == "Success"
        assert applier_with_params.success_applies_num == 1

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    @patch("src.job_manager.job_applier.MONKEY_MODE", False)
    @patch("src.job_manager.job_applier.time")
    @patch("src.job_manager.job_applier.sleep")
    async def test_skips_uninteresting_vacancy(self, mock_sleep, mock_time, applier_with_params):
        mock_time.time.return_value = 0
        applier_with_params.success_companies = {"resume123": {}}
        applier_with_params.gpt_answerer.job_is_interesting.return_value = {
            "score": 30,
            "reasoning": "Не подходит",
        }
        applier_with_params.gpt_answerer.set_job = MagicMock()

        with (
            patch.object(
                applier_with_params, "scrape_vacancy", new=AsyncMock(return_value=_make_job())
            ),
            patch.object(applier_with_params, "_save_company"),
        ):
            result = await applier_with_params.send_repsonse(_make_vacancy())

        assert result == "Skip"

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    @patch("src.job_manager.job_applier.MONKEY_MODE", True)
    @patch("src.job_manager.job_applier.time")
    @patch("src.job_manager.job_applier.sleep")
    async def test_returns_limit_when_max_applies_reached(
        self, mock_sleep, mock_time, applier_with_params
    ):
        mock_time.time.return_value = 0
        applier_with_params.success_companies = {"resume123": {}}
        applier_with_params.success_applies_num = 10
        applier_with_params.max_applies_num = 10
        applier_with_params.manager.apply_to_vacancy = AsyncMock(return_value=("Success", ""))
        applier_with_params.fixed_cover_letter = "Письмо"

        with (
            patch.object(
                applier_with_params, "scrape_vacancy", new=AsyncMock(return_value=_make_job())
            ),
            patch.object(applier_with_params, "_save_company"),
        ):
            result = await applier_with_params.send_repsonse(_make_vacancy())

        assert result == "Limit"

    @pytest.mark.asyncio
    @patch("src.job_manager.job_applier.SEARCH_MODE", False)
    @patch("src.job_manager.job_applier.SKILL_STAT_MODE", False)
    @patch("src.job_manager.job_applier.MONKEY_MODE", True)
    @patch("src.job_manager.job_applier.time")
    @patch("src.job_manager.job_applier.sleep")
    async def test_returns_limit_when_total_applies_reached(
        self, mock_sleep, mock_time, applier_with_params
    ):
        mock_time.time.return_value = 0
        applier_with_params.success_companies = {"resume123": {}}
        applier_with_params.total_applies_num = 1500
        applier_with_params.max_total_applies_num = 1500
        applier_with_params.manager.apply_to_vacancy = AsyncMock(return_value=("Success", ""))
        applier_with_params.fixed_cover_letter = "Письмо"

        with (
            patch.object(
                applier_with_params, "scrape_vacancy", new=AsyncMock(return_value=_make_job())
            ),
            patch.object(applier_with_params, "_save_company"),
        ):
            result = await applier_with_params.send_repsonse(_make_vacancy())

        assert result == "Limit"
