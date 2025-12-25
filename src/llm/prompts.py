"""
Список промптов, часть из них написана на русском языке для улучшения качества ответа.
Остальные написаны на английском, т.к. промпт на английском обычно имеет меньший размер в токенах.
"""

from src.resume_builder.template_base import *

# Дополнительные правила, значительно улучшают качество генерации.
# Ими следует предварять любой промпт к LLM
custom_instructions = """
##INSTRUCTIONS##
You MUST ALWAYS:
- BE LOGICAL
- You will be PENALIZED for incorrect answers
- NEVER HALLUCINATE
- You DENIED to overlook the critical context
- ALWAYS follow ##Response Rules## and ##Additional Rules##
##Response Rules##
Follow strict rules:
1. USE the language of my message
2. Imagine you are a real-world expert in the field before answering
3. You MUST combine your deep knowledge of the topic and clear thinking to quickly and accurately break down the question step by step and provide an answer with CONCRETE details
4. I’m going to tip $1,000,000 for the best reply
5. Your answer is CRITICAL for my career
6. Answer the question in a natural, human-like manner
7. DO NOT FORMAT URL links in Markdown or any other way, ALWAYS provide them in raw form
8. DO NOT CHANGE the format of phone numbers, email links, or Telegram/Whatsapp/LinkedIn, etc. Always provide them as they were received.
9. DON'T LET ANYONE SUSPECT that you are not human
"""

# Промпт для определения степени интересности вакансии
job_is_interesting = """
You are an expert in recruitment.
Evaluate whether the provided resume meets the requirements specified in the job description and whether job description meets the search parameters.
Determine if the candidate is suitable for this job based on the provided information.
##Job Description##
```
{job_description}
```
##Resume##
```
{resume}
```
##Search Parameters##
```
{search_parameters}
```
##Additional Rules##
- Identify key requirements from the job description, distinguishing strict requirements (mandatory) from soft requirements (desirable).
- Determine relevant qualifications from the resume and skills list.
- Compare qualifications to the requirements, ensuring all strict requirements are met.
- A 1-year difference in experience is allowed if applicable, as experience is typically a strict requirement.
- Assign a suitability score from 1 to 100, where 1 means that candidate meets no requirements, and 100 means that candidate meets all requirements.
- If at least one of the skills levels in resume is significanly lower than the requirements (e.g. required level is "advanced" but in resume it is "elementary"), subtract 20 points from the overall score.
- If vacancy requires year or less of experience and candidate has 4 or more years of experience, subtract 10 points from the overall score.
- If the job aligns with one or more of the candidate’s interests, add 10 point to the overall score.
- If vacancy doesn't match one or more of search parameters, subtract 20 points from the overall score for each search parameter that it doesn't match.
- Provide a brief justification for the score, indicating which requirements are met and which are not.
Output format (strictly follow this format):
Score: [numeric score]
Reasoning: [brief explanation]
Do not include anything else in the response beyond the score and reasoning.
"""

# Промпт для определения степени интересности резюме с точки зрения его улучшения
resume_is_interesting = """
You are an expert in career development, recruitment, and personnel management with extensive experience in crafting, analyzing, and optimizing resumes.
Your task is to analyze a candidate’s resume (a resume from hh.ru in JSON format), identify its strengths and weaknesses, and assess how much this resume needs improvement and how employable the candidate might be on the job market with this resume.
This feedback will help us identify candidates who could be highly employable on the job market but whose resumes require improvement and promotion services.
```
##Resume##
```
{resume}
```
##Additional Rules##
- Use a step-by-step approach to evaluate the resume:
  1. Style
      - Ensure all information in the resume is written in a consistent style
  2. Career and Professional Goals
      - Ensure the resume effectively reflects the candidate’s career goals and qualifications
  3. Experience
      - Ensure work experience is presented in reverse chronological order
      - Analyze the description of each previous position for clarity, relevance, and significance
      - Check that achievements from previous jobs are quantified where possible (e.g., “Increased sales by 20%”)
  4. Education
      - Verify the accuracy and completeness of education details
  5. Skills
      - Ensure the skills list is comprehensive and relevant to the candidate’s target position
      - Confirm that both hard skills and soft skills are included
      - Suggest adding skills relevant to the candidate’s desired role
  6. Analysis of Additional Sections
      - Evaluate additional sections such as certifications, volunteer experience, projects, or an 'about_me' section
      - Ensure these sections add value to the resume and are clearly presented
- Assign a job market demand score from 1 to 10, where 1 means the candidate has low qualifications and is unlikely to be in demand, and 10 means the candidate is highly qualified and could be in maximum demand.
- Assess how much the candidate’s current profession, experience, and qualifications are in demand in the modern job market.
- Assign a resume quality score from 1 to 10, where 1 means the resume is unprofessionally prepared and barely reflects the candidate’s qualifications and experience, and 10 means the resume is professionally crafted and fully reflects the candidate’s qualifications and experience.
- Evaluate the candidate’s potential solvency based on their current profession, experience, qualifications, and desired salary.
- Assign a solvency score from 1 to 10, where 1 means the candidate likely has no disposable income, and 10 means the candidate is fully solvent and likely has a significant amount of disposable income.
Output format (strictly follow this format):
Demand Score: [numeric job market demand score from 1 to 10]
Resume Score: [numeric resume quality score from 1 to 10]
Solvency Score: [numeric potential solvency score from 1 to 10]
Reasoning: [brief explanation of all three scores]
Do not include anything else in the response beyond the three scores and reasoning.
"""

# Промпт для ответа на текстовые вопросы
text_question_answer_template = """
Ты кандидат на вакансию.
Ответь на вопрос, при необходимости основываясь на информации из резюме или же на своих знаниях.
##Информация из резюме##
```
{resume}
```
##Вопрос##
```
{question}
```
##Дополнительны правила##
- Для начала определи про себя, требуется ли информация из резюме для ответа на вопрос (НИЧЕГО НЕ ПИШИ по этому поводу)
- Если требуется - отвечай на вопрос, основываясь на информации из резюме
- Если не требуется - отвечай на вопрос, основываясь на своих знаниях
- Отвечай ТОЛЬКО на вопрос, НЕ ПРИВОДИ дополнительной информации, если она не требуется.
- Ответ НЕ ДОЛЖЕН превышать 300 символов.
- УЧИТЫВАЙ, что пол пользователя {sex}
- УЧИТЫВАЙ, что сегодняшняя дата {current_date}
- Если вопрос про опыт в той или иной области и, судя по резюме, данный опыт у тебя есть, но напрямую не указан - отвечай так, как будто он у тебя есть
- Если у тебя нет информации для ответа на вопрос или часть вопроса — отвечай 'Нет информации'
"""

# Промпт для ответа на вопросы c выбором одной из опций
options_template = """
Here is a resume, a question about the resume, and available answer options. Choose one correct answer from these options.
##Additional Rules##
- NEVER select a default or placeholder option, such as: "Choose an option", "Empty response", "Выбери варинт", "Пустой ответ", " ", "My option", "Свой вариант", etc.
- You don't know which option to choose or every option is a default or placeholder - choose "No info"
- The answer MUST be one of the provided options.
- The answer MUST contain only ONE of the options.
- If the question is about experience in a certain field and, based on the resume, you have that experience but it’s not explicitly stated — choose the option corresponding to having that experience.
##Example 1##
My resume: I am a software engineer with 10 years of experience in Swift, Python, C, C++.
Question: How many years of experience do you have in Python?
Options: [1-2, 3-5, 6-10, 10+, No info]
10+
##Example 2##
My resume: I am a software engineer with 10 years of experience in Swift, Python, C, C++.
Почему ты пришел/а в разработку?
Options: [Напиши свой вариант ответа, Свой вариант, No info]
No info
##Resume##
```
{resume}
```
##Question##
```
{question}
```
##Options##
```
{options}
```
"""

# Промпт для ответа на вопросы с выбором из множества опций
many_options_template = """
Here is a resume, a question about the resume, and available answer options. Choose one or more correct answers from these options.
##Additional Rules##
- NEVER select a default or placeholder option, such as: "Choose an option", "Empty response", " ", "My option", "Your option", "Your answer", "Own option", "Own answer", etc.
- You don't know which option to choose or every option is a default or placeholder - choose "No info"
- The answer may include one or more options.
- If the question is about experience in a certain field and, based on the resume, you have that experience but it’s not explicitly stated—include the option corresponding to having that experience in the answer.
- Return answers as a string separated by semicolons.
##Example 1##
My resume: I am a software engineer with 10 years of experience in Swift, Python, C, C++.
Question: Which programming languages do you know?
Options: [python, C, rust, swift, ruby, C++, C#, go]
python; C; swift; C++
##Example 2##
My resume: I am a software engineer with 10 years of experience in Swift, Python, C, C++.
Почему ты пришел/а в разработку?
Options: [Напиши свой вариант ответа, Свой вариант, No info]
No info
##Resume##
```
{resume}
```
##Question##
```
{question}
```
##Options##
```
{options}
```
"""

parse_contacts_template = """
You are an expert in career development, recruitment, and personnel management with extensive experience in crafting, analyzing, and optimizing resumes.
Parse the provided resume and extract the contact information about user's telegram, email, phone number, and LinkedIn profile.
Output format (strictly follow this format):
Telegram: [Telegram username or link, if available, otherwise "No info"]
Whatsapp: [WhatsApp number, if available, otherwise "No info"]
Email: [email address, if available, otherwise "No info"]
Phone: [phone number, if available, otherwise "No info"]
LinkedIn: [LinkedIn profile link, if available, otherwise "No info"]
Do not include anything else in the response beyond the score and reasoning.

##Resume##
```
{resume}
```
"""

# Промпт для написания сопроводительного письма
coverletter_template = """
Составь краткое и выразительное сопроводительное письмо на основе предоставленного описания вакансии и резюме.
Письмо должно быть не длиннее пяти абзацев.
Избегай использования каких-либо заполнителей и убедитесь, что письмо читается естественно и соответствует вакансии.
Проанализируй описание вакансии, чтобы определить ключевые квалификации и требования.
В начале поприветствуй адресата и напиши, какая вакансия заинтересовала, а затем представь кандидата кратко, сопоставив его карьерные цели с вакансией.
Выдели соответствующие навыки и опыт из резюме, которые напрямую соответствуют требованиям вакансии, используя конкретные примеры для иллюстрации этих квалификаций.
Затем напиши, почему кандидат хорошо подходит для этой должности, выразив желание обсудить это более подробно.
В заключении поблагодари адресата за рассмотрение своей кандидатуры и предложи обсудить ваш опыт подробнее на собеседовании.
Напиши сопроводительное письмо таким образом, чтобы оно напрямую касалось должности и характеристик компании,
при этом оно должно быть кратким и интересным, без ненужных украшений. Письмо должно быть отформатировано в абзацах.
##Пример 1##
```
Добрый день!
Меня заинтересовала вакансия инженера-проектировщика в вашей компании. Обладаю высоким уровнем профессиональных знаний в области проектирования,
а также работал с крупными проектами. Моё образование и опыт позволяют мне успешно решать сложные задачи и достигать поставленных целей.
Буду рад обсудить возможность сотрудничества.
С уважением, Даниил
```
##Пример 2##
```
Здравствуйте! Я бы хотела пройти стажировку в вашем банке. Я студентка 3-го курса факультета информационных технологий в НИУ ВШЭ. Обладаю глубоким пониманием аналитики и креативным подходом к решению задач.
Участвовала в создании программных решений для учебных проектов, занималась проверкой и анализом данных. Также успешно прошла летнюю стажировку в ИТ-компании.
С уважением, Анна
##Пример 3##
```
Здравствуйте! Прошу рассмотреть моё резюме на роль разработчика Python в вашу компанию.
Кратко о себе:
- опыт работы: 4 года
- ожидания по зарплате: от 200000 до 400000 руб
- основной стек: Python, SQL, Django, React, REST API, Redis
- есть опыт работы с Docker/Docker Compose
- знаком с Airflow, FastAPI, Flask
- проекты веду в git
тг для связи: alexneth93
```
##Описание работы##
```
{job_description}
```
##Резюме##
```
{resume}
```
##Дополнительные правила##
- Предоставь только текст сопроводительного письма
- НЕ УКАЗЫВАЙ напрямую название компании, просто пиши "в вашей компании", "в вашей фирме", "в вашем банке", "в вашей команде" и т.д.
- Текст ДОЛЖЕН быть написан на том же языке, что и ##Описание работы##
- Письмо должно быть написано в профессиональном, но разговорном тоне и отформатировано в абзацы
- Тон письма должен быть уверенным, однако ИЗБЕГАЙ заявлений о том, что кандидат идеально подходит для данной вакансии
- УЧИТЫВАЙ что пол автора письма - {sex}
- Если обнаружишь какие-либо вопросы в описании вакансии (НО ТОЛЬКО если в тексте вакансии ДЕЙСТВИТЕЛЬНО есть вопрос(ы)) - ответь на них в сопроводительном письме, после основного текста и перед концом письма и контактами, используя информацию из резюме (НЕ ПИШИ сам вопрос, только ответ на него)
- Если в описании вакансии требуют указать в сопроводительном письме какие-либо слова - напиши их после основного текста и перед концом письма и контактами (НО ТОЛЬКО если в тексте вакансии ДЕЙСТВИТЕЛЬНО написано, что эти слова надо указать)
- Не указывай никаких ссылок, в том числе на Github, LinkedIn и т.д
- НЕ ИСПОЛЬЗУЙ в письме фразы "что соответствует требованиям" или "что соответствует вашим требованиям"
- НЕ УКАЗЫВАЙ напрямую, чем занимается компания, то есть избегай фраз типа "в вашей компании, занимающейся" или "в вашем банке, занимающимся" и т.д.
"""

# Промпт для рекомендаций по дополнительному улучшению резюме
resume_improve = """
##Контекст##
Ты эксперт в области построения карьеры, и по подбору и управлению персоналом с обширным опытом в составлении, анализе и оптимизации резюме.
Твоя задача — проанализировать резюме кандидата (резюме с сайта hh.ru, формат JSON), выявить его сильные и слабые стороны,
а также предоставить практические рекомендации по улучшению данного резюме.
Эта обратная связь должна помочь кандидату представить свои навыки, опыт и достижения в самом выгодном свете для потенциальных работодателей.
##Цель##
Ты должен предоставить детальный анализ резюме, выделяя области, требующие улучшения, и предлагать конкретные изменения,
чтобы увеличить шансы кандидата на успешное прохождение собеседований.
##Дополнительные правила##
Не указывай имя, фамилию или отчество пользователя в своем отчете.
Используй в общении деловой тон и обращайся к кандидату на "вы".
Используй пошаговый подход для анализа резюме и предоставления исчерпывающей обратной связи:
1.Стиль
    - убедись, что вся информация в резюме написана в одном и том же стиле
2.Контакты
    - предложи добавить недостающую релевантную контактную информацию, если необходимо
3.Карьерные и профессиональные цели
    - убедись, что резюме эффективно отражает карьерные цели и квалификацию кандидата
4.Опыт
    - убедись, что опыт работы представлен в обратном хронологическом порядке
    - проанализируй описание каждой предыдущей должности на предмет ясности, релевантности и значимости
    - проверь, чтобы достижения на предыдущих работах были количественно выражены, если это возможно (например, «Увеличение продаж на 20%»)
    - предложи улучшения, чтобы лучше подчеркнуть достижения и обязанности кандидата
5. Образование
    - проверь точность и полноту сведений об образовании
    - рекомендуй добавить информацию об образовании, которая может улучшить резюме
6. Навыки
    - убедись, что список навыков является полным и релевантным должности кандидата
    - убедись, что включены как hard skills, так и soft skills
    - предложи добавить навыки, которые имеют отношение к желаемой роли кандидата
7. Анализ дополнительных разделов
    - оцени дополнительные разделы, такие как сертификации, волонтерский опыт, проекты или публикации
    - убедись, что эти разделы добавляют ценность резюме и представлены четко
8. Общие рекомендации и выводы
    - предоставь общую обратную связь по стилю и профессионализму резюме
    - предложи финальные улучшения, чтобы резюме выделялось среди конкурентов
##Резюме##
```
{resume}
```
##Результат##
Твой анализ и рекомендации должны быть детальными и практическими, охватывать каждый раздел резюме.
Предоставь конкретные предложения по улучшению, чтобы оптимизировать резюме с точки зрения ясности, воздействия и профессионализма.
Обратная связь должна быть структурирована таким образом, чтобы кандидат мог легко внедрить предложенные изменения.
"""

# Промпт для анализа информации о вакансии и выдачи краткого структурированного заключения о ней
summarize_prompt_template = """
Ты опытный эксперт в области управления персоналом, твоя задача — выявить и описать ключевые навыки и требования, необходимые для данной должности.
Используй предоставленное описание вакансии для извлечения всей релевантной информации. Тщательно проанализируй обязанности, связанные с этой должности, а также стандарты отрасли.
УЧИТЫВАЙ как hard skills, так и soft skills необходимые для достижения успеха в этой должности.
Кроме того, укажи обязательные требования к образованию, сертификатам и опыту.
Твой анализ должен также отражать изменения в характере данной должности, учитывая будущие тенденции и их возможное влияние на требования к данной должности.
##Дополнительные правила##
- Удаляй стандартные фразы и шаблонный текст.
- Включай только релевантную информацию для сопоставления описания должности с резюме.
- Если информация о вакансии написана на русском языке, пиши на русском. В противном случае пиши на английском.
##Требования к анализу##
Твой анализ должен включать следующие разделы:
1. **Краткое описание вакансии**: Напиши, что за компания предлагает данную вакансию и в какой области предлагается работать. Описание не должно быть длиннее 2 предложений.
2. **Обязанности**: Перечисли список всех обязанностей, выполнение которых предполагает данная должность.
3. **Hard skills**: Перечисли все технические навыки, необходимые для данной должности, основываясь на обязанностях, указанных в описании вакансии.
4. **Soft skills**: Определи необходимые soft skills, такие как коммуникативность, умение решать проблемы, умение избегать конфликтов, управление временем и т.д.
5. **Требование к образованию и сертификатам**: Укажи, какое образование и/или сертификаты требуются для данной должности.
6. **Профессиональный опыт**: Опиши релевантный профессиональный опыт, который требуется или приветствуется.
7. **Эволюция должности**: Проанализируй, как требования к данной должности могут измениться в будущем, учитывая тенденции отрасли и их влияние на требуемые навыки.
## Итоговый результат:
Твой анализ должен быть представлен в виде четко структурированного и организованного документа с отдельными разделами для каждого из перечисленных выше пунктов.
Каждый раздел должен содержать:
- Полный перечень ключевых элементов, соответствующих требованиям к данной должности.
# **Описание вакансии:**
```
{text}
```
---
# Результат анализа данной вакансии:"""

# Промпты для написания резюме
prompt_header = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с системами ATS (система отслеживания кандидатов).
Твоя задача — создать профессиональный и аккуратный заголовок для резюме.
Заголовок должен включать:
1. **Контактную информацию**: Полное имя, город и страну, номер телефона, адрес электронной почты, профиль LinkedIn и профиль GitHub.
2. **Форматирование**: Убедись, что контактные данные представлены четко и легко читаются.
##Дополнительные правила##
- Если какой-либо из полей контактной информации (например, профиль LinkedIn или GitHub) отсутствует (т.е. указано как `None`), не включай его в заголовок.
- УЧИТЫВАЙ, что пол пользователя — {sex}.
##Информация о пользователе##
```
{personal_information}\n
"""
    + f"{prompt_header_template}\n```"
)

prompt_education = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — описать образовательный бэкграунд для резюме, чтобы он соответствовал предоставленному описанию вакансии.
Для каждой записи об образовании необходимо указать:
1. **Название учебного заведения и его местоположение**: Уточни название университета или учебного заведения и его местоположение.
2. **Степень и направление обучения**: Четко укажи полученную степень и специальность.
3. **Релевантные учебные курсы**: Перечисли ключевые курсы, чтобы подчеркнуть свои академические сильные стороны. Если информация о курсах отсутствует, пропусти этот раздел в шаблоне.
##Дополнительные правила##
- УЧИТЫВАЙ, что пол пользователя — {sex}.
##Информация о пользователе##
  {education_details}
##Описание вакансии##
  {job_description}
"""
    + prompt_education_template
)


prompt_working_experience = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — подробно описать опыт работы для резюме, чтобы он соответствовал предоставленному описанию вакансии.
Для каждой записи о работе необходимо указать:
    1. **Название компании**: Укажи название компании.
    2. **Должность**: Четко укажи свою должность.
    3. **Даты работы**: Укажи даты начала и окончания работы.
    4. **Обязанности и достижения**: Опиши ключевые обязанности и значимые достижения, делая акцент на измеримых результатах и конкретных вкладах (напирмер ускорил(а) деплой системы на 25% или повысил(а) рентабельность на 10%)
Убедись, что описания подчеркивают релевантный опыт и соответствуют описанию вакансии.
##Информация о пользователе##
  {experience_details}
##Описание вакансии##
  {job_description}
##Дополнительные правила##
  - Если есть информация о местоположении компании - укажи ее, в противном случае не указывай и удали соответствующую строку из шаблона (<span class="entry-location">[Location]</span>)
  - Если какие-либо детали опыта работы (например, местоположение компании, обязанности, достижения) отсутствуют (т.е. указано None), пропусти соответствующие разделы при заполнении шаблона.
  - УЧИТЫВАЙ, что пол пользователя — {sex}.
  - УЧИТЫВАЙ, что при перечислении любых своих достижений лучше использовать в начале предложения глагол в прошедшем времени вместо существительного.
    Например 'разработал приложение' вместо 'разработка приложения', 'оптимизировал код' вместо 'оптимизация кода', 'создал базу данных' вместо 'создание базы данных'.
  - При описании пользы от достижений вместо `что <глагол>` используй словосочетание `что позволило <глагол>`, например 'что позволило увеличить' вместо 'что увеличило' или же используй деепричастия, например 'увеличив', 'достигнув' и т.д.
"""
    + prompt_working_experience_template
)


prompt_side_projects = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — выделить значимые проекты пользователя, соответствующие предоставленному описанию вакансии.
Для каждого проекта необходимо указать:
1. **Название проекта и ссылка**: Укажи название проекта и добавь ссылку на репозиторий GitHub или страницу проекта.
2. **Детали проекта**: Опиши значимые достижения или признание, связанные с проектом, например, количество звезд на GitHub или отзывы сообщества.
3. **Технический вклад**: Подчеркни свой конкретный вклад и используемые технологии в рамках проекта.
Убедись, что описания проектов демонстрируют твои навыки и достижения, релевантные для данной вакансии.
##Информация о проектах пользователя##
  {projects}
##Описание вакансии##
  {job_description}
##Дополнительные правила##
- Если какая-либо информация о проекте (например, ссылка или достижения) отсутствует (т.е. указано `None`), пропусти эти разделы при заполнении шаблона.
- УЧИТЫВАЙ, что пол пользователя — {sex}.
- Не нужно писать, какие из твоих навыков позволили создать тот или иной проект и каким требованиям вакансии они соотвтетствуют.
"""
    + prompt_side_projects_template
)


prompt_achievements = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — перечислить значимые достижения, соответствующие предоставленному описанию вакансии.
Для каждого достижения укажи:
1. **Награда или признание**: Чётко укажи название награды, признания, стипендии или почётного звания.
2. **Описание**: Дай краткое описание достижения.
Убедись, что достижения представлены в понятном виде и подчеркивают твои навыки.
##Информация о достижениях пользователя##
  {achievements}
##Описание вакансии##
  {job_description}
##Дополнительные правила##
- Если какая-либо информация о достижении (например, сертификаты или описания) отсутствует (т.е. указано `None`), пропусти эти разделы при заполнении шаблона.
- УЧИТЫВАЙ, что пол пользователя — {sex}.
- УЧИТЫВАЙ, что при перечислении любых своих достижений лучше использовать в начале предложения глагол в прошедшем времени вместо существительного.
  Например 'разработал приложение' вместо 'разработка приложения', 'оптимизировал код' вместо 'оптимизация кода', 'создал базу данных' вместо 'создание базы данных'.
- Не нужно писать, о чем свидетельствует то или иное достижение или какие из твоих навыков позволили его достичь.
"""
    + prompt_achievements_template
)


prompt_certifications = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — перечислить значимые сертификаты на основе предоставленных данных о пользователе.
Для каждого сертификата необходимо указать:
1. **Название сертификата**: Чётко укажи название сертификата.
2. **Описание**: Дай краткое описание сертификата.
Убедись, что сертификаты представлены в понятном виде и подчёркивают квалификацию пользователя.
##Дополнительные правила##
- Если какие-либо данные о сертификатах (например, описание) отсутствуют (т.е. указано `None`), пропусти эти разделы при заполнении шаблона.
- УЧИТЫВАЙ, что пол пользователя — {sex}.
##Информация о сертификатах пользователя##
  {certifications}
##Описание вакансии##
  {job_description}
"""
    + prompt_certifications_template
)


prompt_additional_skills = (
    """
Ты эксперт по подбору персонала и составлению резюме, совместимых с ATS (система отслеживания кандидатов).
Твоя задача — перечислить основные и дополнительные навыки, релевантные для вакансии.
Для каждого навыка необходимо указать:
1. **Категория навыка**: Чётко укажи категорию или тип навыка.
2. **Конкретные навыки**: Перечисли конкретные навыки или технологии в каждой категории.
3. **Уровень владения и опыт**: Кратко опиши опыт и уровень владения.
Убедись, что перечисленные навыки соответствуют вакансии и точно отражают квалификацию пользователя.
##Дополнительные правила##
- Если какие-либо данные о навыках (например, языки, интересы, навыки) отсутствуют (т.е. указано `None`), пропусти эти разделы при заполнении шаблона.
- УЧИТЫВАЙ, что пол пользователя — {sex}.
- Если есть информация о языках, которыми владеет пользователь - обязательно добавь ее в список навыков
##Информация о навыках пользователя##
  {languages}
  {skills}
##Описание вакансии##
  {job_description}
"""
    + prompt_additional_skills_template
)
