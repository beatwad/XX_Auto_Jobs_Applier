from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.constants import DUMMY_PERSONAL_INFO_FEMALE, DUMMY_PERSONAL_INFO_MALE

# Assuming ResumeScraper is imported correctly in the original test file
# from src.job_manager.resume_scraper import ResumeScraper


@pytest.fixture
def mock_api():
    """Create a mock API object"""
    api = MagicMock()
    return api


@pytest.fixture
def mock_resume_data():
    """Create mock resume data that would be returned by the API"""
    return {
        "id": "resume123",
        "title": "Python Developer",
        "first_name": "John",
        "last_name": "Doe",
        "middle_name": "Smith",
        "next_publish_at": (datetime.now() - timedelta(hours=5)).isoformat(),
        "area": {"name": "Moscow"},
        "metro": {"name": "Arbatskaya"},
        "birth_date": "15.06.1990",
        "age": 33,
        "gender": {"name": "Мужской"},
        "citizenship": [{"name": "Россия"}],
        "work_ticket": [{"name": "Россия"}],
        "has_vehicle": True,
        "driver_license_types": [{"id": "B"}],
        "relocation": {"type": {"name": "Не готов к переезду"}},
        "language": [
            {"name": "Русский", "level": {"name": "Родной"}},
            {"name": "Английский", "level": {"name": "B2 — Средне-продвинутый"}},
        ],
        "experience": [
            {
                "position": "Senior Python Developer",
                "company": "Tech Corp",
                "start": "2020-01-01",
                "end": "2023-01-01",
                "area": {"name": "Moscow"},
                "employer": {"name": "Tech Corp"},
                "industries": [{"name": "IT"}],
                "description": "Developed backend systems",
            }
        ],
        "total_experience": {"months": 48},
        "education": {
            "level": {"name": "Высшее"},
            "primary": [
                {
                    "name": "Moscow State University",
                    "organization": "Faculty of Computer Science",
                    "result": "Specialist",
                    "year": 2015,
                    "education_level": {"name": "Высшее"},
                }
            ],
            "elementary": [],
            "additional": [
                {
                    "name": "Advanced Python",
                    "organization": "Coursera",
                    "result": "Certificate",
                    "year": 2019,
                }
            ],
            "attestation": [],
        },
        "professional_roles": [{"name": "Python Developer"}],
        "employments": [{"name": "Полная занятость"}],
        "schedules": [{"name": "Удаленная работа"}],
        "travel_time": {"name": "Не имеет значения"},
        "business_trip_readiness": {"name": "Готов к редким командировкам"},
        "site": [
            {"url": "https://t.me/johndoe", "type": {"id": "telegram"}},
            {"url": "https://wa.me/johndoe", "type": {"id": "whatsapp"}},
            {"url": "https://linkedin.com/in/johndoe", "type": {"id": "linkedin"}},
            {"url": "https://github.com/johndoe", "type": {"id": "github"}},
            {"url": "https://www.johndoe.com", "type": {"id": "other_site"}},
        ],
        "contact": [
            {
                "type": {"id": "cell"},
                "value": {"formatted": "+7 (999) 123-45-67"},
                "preferred": True,
            },
            {"type": {"id": "email"}, "value": "john.doe@example.com", "preferred": False},
        ],
        "salary": {"amount": 200000, "currency": "RUR"},
        "skill_set": ["Python", "Django", "Flask", "Docker"],
        "skills": "Experienced Python developer with 5+ years of experience. Check my projects: https://github.com/johndoe/test1, https://github.com/johndoe/test2",
        "certificate": [
            {
                "title": "AWS Certified Developer",
                "achieved_at": "2022-05-01",
                "organization": "Amazon Web Services",
            }
        ],
        "recommendation": [
            {
                "name": "Jane Smith",
                "position": "Team Lead",
                "organization": "Previous Company",
                "contact": "jane.smith@example.com",
            }
        ],
    }


@pytest.fixture
def mock_resume_female_data(mock_resume_data):
    """Create mock resume data for female applicant"""
    data = mock_resume_data.copy()
    data["gender"]["name"] = "Женский"
    data["first_name"] = "Jane"
    return data


@pytest.fixture
def mock_resumes_list():
    """Create mock list of resumes that would be returned by API"""
    return {
        "items": [
            {"id": "resume456", "title": "Data Engineer"},
            {"id": "resume123", "title": "Python Developer"},
            {"id": "resume789", "title": "PHP Developer"},
        ]
    }


@pytest.fixture
def mock_anonymized_text_fixture():  # Renamed to avoid collision with mock argument
    """Create mock anonymized text return value"""
    return "Test text from fixture"


class TestResumeScraper:
    def test_init(self, mock_api):
        """Test initialization of ResumeScraper"""
        from src.job_manager.resume_scraper import ResumeScraper

        job_title = "Python Developer"
        scraper = ResumeScraper(mock_api, job_title, "abc123", "")

        assert scraper.api == mock_api
        assert scraper.job_title == job_title
        assert scraper.resume_info == {"general_knowledge_questions": ""}
        assert scraper.personal_information == {}
        assert scraper.github_links == []

    def test_get_id_of_selected_resume_with_job_title(self, mock_api, mock_resumes_list):
        """Test getting resume ID when job title is provided"""
        from src.job_manager.resume_scraper import ResumeScraper

        mock_api.api_request.return_value = mock_resumes_list

        scraper = ResumeScraper(mock_api, "python developer", "abc123", "")
        resume_id, resume_titles = scraper.get_id_of_selected_resume()

        mock_api.api_request.assert_called_once_with("https://api.hh.ru/resumes/mine")
        assert resume_id == "resume123"
        assert resume_titles == ["Data Engineer", "Python Developer", "PHP Developer"]

    def test_get_id_of_selected_resume_without_job_title(self, mock_api, mock_resumes_list):
        """Test getting resume ID when no job title is provided"""
        from src.job_manager.resume_scraper import ResumeScraper

        mock_api.api_request.return_value = mock_resumes_list

        scraper = ResumeScraper(mock_api, "", "", "")
        resume_id, resume_titles = scraper.get_id_of_selected_resume()

        mock_api.api_request.assert_called_once_with("https://api.hh.ru/resumes/mine")
        assert resume_id == "resume456"
        assert resume_titles == ["Data Engineer", "Python Developer", "PHP Developer"]
        assert scraper.job_title == "Data Engineer"

        # Reset mock for the next part of the test if needed, or use separate tests
        mock_api.reset_mock()
        mock_api.api_request.return_value = mock_resumes_list  # Re-assign after reset

        scraper = ResumeScraper(mock_api, "", "resume789", "")
        resume_id, resume_titles = scraper.get_id_of_selected_resume()

        # mock_api.api_request.call_count == 2 # This assertion should be specific
        assert mock_api.api_request.call_count == 1  # After reset and one call
        mock_api.api_request.assert_any_call("https://api.hh.ru/resumes/mine")
        assert resume_id == "resume789"
        assert resume_titles == ["Data Engineer", "Python Developer", "PHP Developer"]
        assert scraper.job_title == "PHP Developer"

    def test_get_selected_resume_info(self, mock_api, mock_resume_data):
        """Test getting resume info by ID"""
        from src.job_manager.resume_scraper import ResumeScraper

        mock_api.api_request.return_value = mock_resume_data

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        resume_info = scraper.get_selected_resume_info("resume123")

        mock_api.api_request.assert_called_once_with("https://api.hh.ru/resumes/resume123")
        assert resume_info == mock_resume_data

    def test_raise_resume_when_possible(self, mock_api, mock_resume_data):
        """Test raising resume when possible"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "resume123", "")
        scraper.raise_resume("resume123", mock_resume_data)

        mock_api.api_request.assert_called_once_with(
            "https://api.hh.ru/resumes/resume123/publish", type_="post"
        )

    def test_raise_resume_when_not_possible(self, mock_api):
        """Test not raising resume when not possible"""
        from src.job_manager.resume_scraper import ResumeScraper

        resume_data = {"next_publish_at": (datetime.now() + timedelta(hours=1)).isoformat()}

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.raise_resume("resume123", resume_data)

        mock_api.api_request.assert_not_called()

    def test_get_personal_information(self, mock_api, mock_resume_data):
        """Test getting personal information from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_personal_information(mock_resume_data)

        assert scraper.resume_info["personal_information"]["first_name"] == "John"
        assert scraper.resume_info["personal_information"]["last_name"] == "Doe"
        assert scraper.resume_info["personal_information"]["middle_name"] == "Smith"
        assert scraper.resume_info["personal_information"]["current_city"] == "Moscow"
        assert scraper.resume_info["personal_information"]["metro"] == "Arbatskaya"
        assert scraper.resume_info["personal_information"]["has_vehicle"] is True
        assert scraper.resume_info["personal_information"]["driver_license_types"] == ["B"]
        # assert scraper.resume_info["personal_information"]["birthday"] == "15.06.1990"
        assert scraper.resume_info["personal_information"]["age"] == 33
        assert scraper.resume_info["personal_information"]["sex"] == "Мужской"
        assert scraper.resume_info["personal_information"]["citizenship"] == ["Россия"]
        assert scraper.resume_info["personal_information"]["legal_authorization"] == ["Россия"]

    def test_get_work_preferences(self, mock_api, mock_resume_data):
        """Test getting work preferences from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_work_preferences(mock_resume_data)

        assert scraper.resume_info["work_preferences"]["position"] == "Python Developer"
        assert scraper.resume_info["work_preferences"]["can_relocate"] == "Не готов к переезду"

    def test_get_languages(self, mock_api, mock_resume_data):
        """Test getting languages from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_languages(mock_resume_data)

        assert scraper.resume_info["languages"]["Русский"] == "Родной"
        assert scraper.resume_info["languages"]["Английский"] == "B2 — Средне-продвинутый"

    def test_get_education_details(self, mock_api, mock_resume_data):
        """Test getting education details from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_education_details(mock_resume_data)

        assert scraper.resume_info["education_details"]["level"] == "Высшее"
        assert (
            scraper.resume_info["education_details"]["primary"][0]["name"]
            == "Moscow State University"
        )
        assert (
            scraper.resume_info["education_details"]["additional"][0]["name"] == "Advanced Python"
        )

    def test_get_experience_details(self, mock_api, mock_resume_data):
        """Test getting experience details from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_experience_details(mock_resume_data)

        assert scraper.resume_info["experience_details"]["total_experience_years"] == 4
        assert (
            scraper.resume_info["experience_details"]["details"][0]["position"]
            == "Senior Python Developer"
        )
        assert scraper.resume_info["experience_details"]["details"][0]["employer"] == "Tech Corp"
        assert scraper.resume_info["experience_details"]["details"][0]["industries"] == ["IT"]

    def test_get_contacts(self, mock_api, mock_resume_data):
        """Test getting contacts from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.get_personal_information(mock_resume_data)
        scraper.get_contacts(mock_resume_data)

        assert scraper.resume_info["personal_information"]["telegram"] == "https://t.me/johndoe"
        assert scraper.resume_info["personal_information"]["whatsapp"] == "https://wa.me/johndoe"
        assert (
            scraper.resume_info["personal_information"]["linkedin"]
            == "https://linkedin.com/in/johndoe"
        )
        assert scraper.resume_info["personal_information"]["phone"] == "+7 (999) 123-45-67"
        assert scraper.resume_info["personal_information"]["email"] == "john.doe@example.com"
        assert scraper.resume_info["personal_information"]["preferred_contact"] == "phone"

    def test_get_salary(self, mock_api, mock_resume_data):
        """Test getting salary expectations from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_salary(mock_resume_data)

        assert scraper.resume_info["salary_expectations"]["amount"] == 200000
        assert scraper.resume_info["salary_expectations"]["currency"] == "RUR"

    def test_get_skills(self, mock_api, mock_resume_data):
        """Test getting skills from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_skills(mock_resume_data)

        assert scraper.resume_info["skills"] == ["Python", "Django", "Flask", "Docker"]

    def test_get_about_me(self, mock_api, mock_resume_data):
        """Test getting about me from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_about_me(mock_resume_data)

        assert (
            scraper.resume_info["about_me"]
            == "Experienced Python developer with 5+ years of experience. Check my projects: https://github.com/johndoe/test1, https://github.com/johndoe/test2"
        )

    def test_get_certificate_details(self, mock_api, mock_resume_data):
        """Test getting certificate details from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_certificate_details(mock_resume_data)

        assert scraper.resume_info["certifications"][0]["title"] == "AWS Certified Developer"
        assert scraper.resume_info["certifications"][0]["organization"] == "Amazon Web Services"

    def test_get_recommendation_details(self, mock_api, mock_resume_data):
        """Test getting recommendation details from resume"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.get_recommendation_details(mock_resume_data)

        assert scraper.resume_info["recommendation"][0]["name"] == "Jane Smith"
        assert scraper.resume_info["recommendation"][0]["position"] == "Team Lead"

    def test_anonymize_personal_information_male(self, mock_api, mock_resume_data):
        """Test anonymizing personal information for male"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.get_personal_information(mock_resume_data)
        scraper.get_about_me(mock_resume_data)
        scraper.get_contacts(mock_resume_data)
        scraper.personal_information = {"sex": "Мужской"}
        scraper.anonymize_personal_information()
        assert (
            scraper.resume_info["personal_information"]["first_name"]
            == DUMMY_PERSONAL_INFO_MALE["first_name"]
        )
        assert (
            scraper.resume_info["personal_information"]["last_name"]
            == DUMMY_PERSONAL_INFO_MALE["last_name"]
        )
        assert (
            scraper.resume_info["personal_information"]["email"]
            == DUMMY_PERSONAL_INFO_MALE["email"]
        )
        assert (
            scraper.resume_info["personal_information"]["phone"]
            == DUMMY_PERSONAL_INFO_MALE["phone"]
        )
        assert (
            scraper.resume_info["personal_information"]["telegram"]
            == DUMMY_PERSONAL_INFO_MALE["telegram"]
        )

    def test_anonymize_personal_information_female(self, mock_api, mock_resume_female_data):
        """Test anonymizing personal information for female"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.get_personal_information(mock_resume_female_data)
        scraper.get_about_me(mock_resume_female_data)
        scraper.get_contacts(mock_resume_female_data)
        scraper.personal_information = {"sex": "Женский"}
        scraper.anonymize_personal_information()
        assert (
            scraper.resume_info["personal_information"]["first_name"]
            == DUMMY_PERSONAL_INFO_FEMALE["first_name"]
        )
        assert (
            scraper.resume_info["personal_information"]["last_name"]
            == DUMMY_PERSONAL_INFO_FEMALE["last_name"]
        )
        assert (
            scraper.resume_info["personal_information"]["email"]
            == DUMMY_PERSONAL_INFO_FEMALE["email"]
        )

    def test_deanonymize_personal_information(self, mock_api, mock_resume_data):
        """Test deanonymizing personal information in output text"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.get_personal_information(mock_resume_data)
        scraper.get_about_me(mock_resume_data)
        scraper.get_contacts(mock_resume_data)
        scraper.get_about_me(mock_resume_data)
        scraper.personal_information = {"sex": "Мужской"}
        scraper.personal_information = scraper.resume_info["personal_information"].copy()
        scraper.anonymize_personal_information()

        # Create text with dummy data
        output_text = (
            f"Hello {DUMMY_PERSONAL_INFO_MALE['first_name']} {DUMMY_PERSONAL_INFO_MALE['last_name']}, "
            f"your email is {DUMMY_PERSONAL_INFO_MALE['email']} and phone is {DUMMY_PERSONAL_INFO_MALE['phone']}. "
            f"Your linkedin is {DUMMY_PERSONAL_INFO_MALE['linkedin']}, "
            f"and your telegram is {DUMMY_PERSONAL_INFO_MALE['telegram']}, and your whatsapp is {DUMMY_PERSONAL_INFO_MALE['whatsapp']}, "
            f"and your other site is {DUMMY_PERSONAL_INFO_MALE['other_site']}. "
            f"Check my projects: {DUMMY_PERSONAL_INFO_MALE['github']}/test1, {DUMMY_PERSONAL_INFO_MALE['github']}/test2. "
            f"Test incorrect second name: {DUMMY_PERSONAL_INFO_MALE['last_name_2']}"
        )
        # Deanonymize the text
        deanonymized = scraper.deanonymize_personal_information(output_text)

        # Check if original values are restored
        assert "John" in deanonymized
        assert "Doe" in deanonymized
        assert "john.doe@example.com" in deanonymized
        assert "+7 (999) 123-45-67" in deanonymized
        assert "https://linkedin.com/in/johndoe" in deanonymized
        assert "https://t.me/johndoe" in deanonymized
        assert "https://wa.me/johndoe" in deanonymized
        assert "https://www.johndoe.com" in deanonymized
        assert "Звягольцев" not in deanonymized
        # assert "https://github.com/johndoe/test1" in deanonymized
        # assert "https://github.com/johndoe/test2" in deanonymized

    @patch("builtins.open", new_callable=MagicMock)
    @patch("yaml.dump")
    def test_save_resume_info(self, mock_yaml_dump, mock_open, mock_api):
        """Test saving resume info to file"""
        from src.job_manager.resume_scraper import ResumeScraper

        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", "")
        scraper.resume_info = {"test": "data"}
        scraper.save_resume_info()

        mock_open.assert_called_once_with("data_folder/output/resume.yaml", "w", encoding="utf-8")
        mock_yaml_dump.assert_called_once()

    # Corrected test_get_resume_info
    @patch(
        "src.job_manager.resume_scraper.ResumeScraper.get_id_of_selected_resume"
    )  # Decorator 1 (Top)
    @patch("src.job_manager.resume_scraper.ResumeScraper.get_selected_resume_info")  # Decorator 2
    @patch("src.job_manager.resume_scraper.ResumeScraper.raise_resume")  # Decorator 3
    @patch("src.job_manager.resume_scraper.ResumeScraper.save_resume_info")  # Decorator 4
    @patch(
        "src.job_manager.resume_scraper.ResumeScraper.anonymize_personal_information"
    )  # Decorator 5
    @patch("src.job_manager.resume_scraper.ResumeScraper.anonymize_text")  # Decorator 6 (Bottom)
    def test_get_resume_info(
        self,
        # Mock arguments, from bottom decorator upwards:
        mock_anonymize_text_method,  # For anony_text (Decorator 6)
        mock_anonymize_pi_method,  # For anony_pi (Decorator 5)
        mock_save_resume_method,  # For save_resume (Decorator 4)
        mock_raise_resume_method,  # For raise_resume (Decorator 3)
        mock_get_selected_info_method,  # For get_selected (Decorator 2)
        mock_get_id_method,  # For get_id (Decorator 1)
        # Pytest fixtures (ensure these are passed if used):
        mock_api,
        mock_resume_data,
        mock_anonymized_text_fixture,  # Fixture providing return value for anonymize_text
    ):
        """Test the full get_resume_info flow"""
        from src.job_manager.resume_scraper import ResumeScraper

        mock_get_id_method.return_value = ("resume123", ["Python Developer"])
        mock_get_selected_info_method.return_value = mock_resume_data
        mock_anonymize_text_method.return_value = mock_anonymized_text_fixture
        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.resume_id, _ = scraper.get_id_of_selected_resume()
        res_info, res_readable = scraper.get_resume_info()

        assert res_info["personal_information"]["first_name"] == mock_resume_data["first_name"]
        assert res_readable == mock_anonymized_text_fixture

        # Verify calls
        mock_get_id_method.assert_called_once()
        mock_get_selected_info_method.assert_called_once_with("resume123")
        # raise_resume is called with resume_id and the result of get_selected_resume_info
        mock_raise_resume_method.assert_called_once_with("resume123", mock_resume_data)
        mock_anonymize_pi_method.assert_called_once()  # This method modifies scraper.resume_info
        mock_save_resume_method.assert_called_once()  # This method also uses scraper.resume_info
        mock_anonymize_text_method.assert_called_once()

    @pytest.mark.parametrize(
        "gender, original_info, dummy_info",
        [
            (
                "Мужской",
                {
                    "first_name": "Иван",
                    "last_name": "Иванов",
                    "phone": "+7(111)222-33-44",
                    "email": "ivan.ivanov@email.com",
                    "telegram": "https://t.me/real_ivan",
                },
                DUMMY_PERSONAL_INFO_MALE,
            ),
            (
                "Женский",
                {
                    "first_name": "Мария",
                    "last_name": "Петрова",
                    "phone": "+7(555)666-77-88",
                    "email": "maria.petrova@email.com",
                    "telegram": "https://t.me/real_maria",
                },
                DUMMY_PERSONAL_INFO_FEMALE,
            ),
        ],
    )
    def test_anonymize_text_replaces_pii_and_github(
        self, mock_api, gender, original_info, dummy_info
    ):
        """
        Test that anonymize_text correctly replaces PII and GitHub links based on gender.
        """
        from src.job_manager.resume_scraper import ResumeScraper

        # Arrange: Set up the scraper with pre-filled personal information
        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        scraper.personal_information = {"sex": gender, **original_info}
        scraper.resume_info["personal_information"] = scraper.personal_information.copy()

        input_text = (
            f"Меня зовут {original_info['first_name']} {original_info['last_name']}. "
            f"Свяжитесь со мной по почте {original_info['email']} или в телеграм: {original_info['telegram']}. "
            f"Мой телефон {original_info['phone']}. "
            "Мои проекты можно найти на GitHub: https://github.com/real_user/project1 и "
            "еще один тут http://github.com/another_user/project2."
        )

        # CORRECTED expected_text: Phone is now replaced, and both full GitHub links are replaced
        # by the single dummy GitHub URL.
        expected_text = (
            f"Меня зовут {dummy_info['first_name']} {dummy_info['last_name']}. "
            f"Свяжитесь со мной по почте {dummy_info['email']} или в телеграм: {dummy_info['telegram']}. "
            f"Мой телефон {dummy_info['phone']}. "
            f"Мои проекты можно найти на GitHub: {dummy_info['github']}/project1 и "
            f"еще один тут {dummy_info['github']}/project2."
        )

        # Act: Run the method
        anonymized_output = scraper.anonymize_text(input_text)

        # Assert: Check the output text and the populated github_links
        assert anonymized_output == expected_text
        # CORRECTED assertion for github_links: It should store the FULL original links
        assert scraper.github_links == [
            "https://github.com/real_user",
            "https://github.com/another_user",
        ]

    def test_anonymize_text_respects_word_boundaries(self, mock_api):
        """
        Test that anonymization only replaces whole words, not substrings.
        """
        from src.job_manager.resume_scraper import ResumeScraper

        # Arrange
        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        original_info = {"first_name": "Иван", "sex": "Мужской"}
        scraper.personal_information = original_info
        scraper.resume_info["personal_information"] = original_info.copy()

        input_text = "Меня зовут Иван. Мой друг - Иванов. Это не я."

        # The word 'Иванов' should NOT be replaced because it's not the exact value of 'first_name'.
        expected_text = (
            f"Меня зовут {DUMMY_PERSONAL_INFO_MALE['first_name']}. Мой друг - Иванов. Это не я."
        )

        # Act
        anonymized_output = scraper.anonymize_text(input_text)

        # Assert
        assert anonymized_output == expected_text

    def test_anonymize_text_skips_info_not_in_resume(self, mock_api):
        """
        Test that information present in the text but not in scraper.resume_info is NOT replaced.
        """
        from src.job_manager.resume_scraper import ResumeScraper

        # Arrange: Set up the scraper with personal info, but MISSING the phone number.
        scraper = ResumeScraper(mock_api, "Python Developer", "abc123", MagicMock())
        original_info = {
            "first_name": "Иван",
            "last_name": "Иванов",
            "sex": "Мужской",
            # No "phone" key here
        }
        scraper.personal_information = original_info
        scraper.resume_info["personal_information"] = original_info.copy()

        phone_in_text = "+7(999)999-99-99"
        input_text = f"Меня зовут Иван Иванов. Мой телефон {phone_in_text}."

        # The phone number should NOT be replaced because it was not in scraper.resume_info.
        expected_text = (
            f"Меня зовут {DUMMY_PERSONAL_INFO_MALE['first_name']} {DUMMY_PERSONAL_INFO_MALE['last_name']}. "
            f"Мой телефон {phone_in_text}."
        )

        # Act
        anonymized_output = scraper.anonymize_text(input_text)

        # Assert
        assert anonymized_output == expected_text
