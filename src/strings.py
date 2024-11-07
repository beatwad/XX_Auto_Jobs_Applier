# Personal Information Template
personal_information_template = """
Answer the following question based on the provided personal information.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.

## Example
My resume: John Doe, born on 01/01/1990, living in Milan, Italy.
Question: What is your city?
 Milan

Personal Information: {resume_section}
Question: {question}
"""

# Legal Authorization Template
legal_authorization_template = """
Answer the following question based on the provided legal authorization details.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.

## Example
My resume: Authorized to work in the EU, no US visa required.
Question: Are you legally allowed to work in the EU?
Yes

Legal Authorization: {resume_section}
Question: {question}
"""

# Work Preferences Template
work_preferences_template = """
Answer the following question based on the provided work preferences.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.

## Example
My resume: Open to remote work, willing to relocate.
Question: Are you open to remote work?
Yes

Work Preferences: {resume_section}
Question: {question}
"""

# Education Details Template
education_details_template = """
Answer the following question based on the provided education details.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- If it seems likely that you have the experience, even if not explicitly defined, answer as if you have the experience.
- If unsure, respond with "I have no experience with that, but I learn fast" or "Not yet, but willing to learn."
- Keep the answer under 140 characters.

## Example
My resume: Bachelor's degree in Computer Science with experience in Python.
Question: Do you have experience with Python?
Yes, I have experience with Python.

Education Details: {resume_section}
Question: {question}
"""

# Experience Details Template
experience_details_template = """
Answer the following question based on the provided experience details.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- If it seems likely that you have the experience, even if not explicitly defined, answer as if you have the experience.
- If unsure, respond with "I have no experience with that, but I learn fast" or "Not yet, but willing to learn."
- Keep the answer under 140 characters.

## Example
My resume: 3 years as a software developer with leadership experience.
Question: Do you have leadership experience?
Yes, I have 3 years of leadership experience.

Experience Details: {resume_section}
Question: {question}
"""

# Projects Template
projects_template = """
Answer the following question based on the provided project details.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- If it seems likely that you have the experience, even if not explicitly defined, answer as if you have the experience.
- Keep the answer under 140 characters.

## Example
My resume: Led the development of a mobile app, repository available.
Question: Have you led any projects?
Yes, led the development of a mobile app

Projects: {resume_section}
Question: {question}
"""

# Availability Template
availability_template = """
Answer the following question based on the provided availability details.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- Keep the answer under 140 characters.
- Use periods only if the answer has multiple sentences.

## Example
My resume: Available to start immediately.
Question: When can you start?
I can start immediately.

Availability: {resume_section}
Question: {question}
"""

# Salary Expectations Template
salary_expectations_template = """
Answer the following question based on the provided salary expectations.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- Keep the answer under 140 characters.
- Use periods only if the answer has multiple sentences.

## Example
My resume: Looking for a salary in the range of 50k-60k USD.
Question: What are your salary expectations?
From 50000 to 60000.

Salary Expectations: {resume_section}
Question: {question}
"""

# Certifications Template
certifications_template = """
Answer the following question based on the provided certifications.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- If it seems likely that you have the experience, even if not explicitly defined, answer as if you have the experience.
- If unsure, respond with "I have no experience with that, but I learn fast" or "Not yet, but willing to learn."
- Keep the answer under 140 characters.

## Example
My resume: Certified in Project Management Professional (PMP).
Question: Do you have PMP certification?
Yes, I am PMP certified.

Certifications: {resume_section}
Question: {question}
"""

# Languages Template
languages_template = """
Answer the following question based on the provided language skills.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- If it seems likely that you have the experience, even if not explicitly defined, answer as if you have the experience.
- If unsure, respond with "I have no experience with that, but I learn fast" or "Not yet, but willing to learn."
- Keep the answer under 140 characters. Do not add any additional languages what is not in my experience

## Example
My resume: Fluent in Italian and English.
Question: What languages do you speak?
Fluent in Italian and English.

Languages: {resume_section}
Question: {question}
"""

# Interests Template
interests_template = """
Answer the following question based on the provided interests.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- Keep the answer under 140 characters.
- Use periods only if the answer has multiple sentences.

## Example
My resume: Interested in AI and data science.
Question: What are your interests?
AI and data science.

Interests: {resume_section}
Question: {question}
"""

# Previous Job Template
previous_job_template = """
Answer the following question based on the previous job experience.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- Keep the answer under 140 characters.

## Example
My resume: Left previous job due to lack of career prospects
Question: Why do you leave your previous job?
Due to lack of career prospects

Previous Job Details: {resume_section}
Question: {question}
"""

# Previous Job Template
general_knowledge_template = """
Answer the following question based on the general knowledge of things you will encounter in your work.

## Rules
- Answer questions directly.
- If question's language is Russian - answer in Russian. Else answer in English.
- Answer briefly, try to keep answer length under 140 characters.

## Example
Question: What is the difference between linear regression and logistic regression? 
Answer: Linear regression predicts continuous values; logistic regression predicts probabilities for categorical outcomes (typically binary).

Question: {question}
"""


numeric_question_template = """
Read the following resume carefully and answer the specific questions regarding the candidate's experience with a number of years. Follow these strategic guidelines when responding:

1. **Related and Inferred Experience:**
   - **Similar Technologies:** If experience with a specific technology is not explicitly stated, but the candidate has experience with similar or related technologies, provide a plausible number of years reflecting this related experience. For instance, if the candidate has experience with Python and projects involving technologies similar to Java, estimate a reasonable number of years for Java.
   - **Projects and Studies:** Examine the candidate’s projects and studies to infer skills not explicitly mentioned. Complex and advanced projects often indicate deeper expertise.

2. **Indirect Experience and Academic Background:**
   - **Type of University and Studies:** Consider the type of university and course followed.
   - **Exam Grades:** Consider exam grades achieved. High grades in relevant subjects can indicate stronger proficiency and understanding.
   - **Relevant thesis:** Consider the thesis of the candidate has worked. Advanced projects suggest deeper skills.
   - **Roles and Responsibilities:** Evaluate the roles and responsibilities held to estimate experience with specific technologies or skills.


3. **Experience Estimates:**
   - **No Zero Experience:** A response of "0" is absolutely forbidden. If direct experience cannot be confirmed, provide a minimum of "2" years based on inferred or related experience.
   - **For Low Experience (up to 5 years):** Estimate experience based on inferred bacherol, skills and projects, always providing at least "2" years when relevant.
   - **For High Experience:** For high levels of experience, provide a number based on clear evidence from the resume. Avoid making inferences for high experience levels unless the evidence is strong.

4. **Rules:**
   - Answer the question directly with a number, avoiding "0" entirely.

## Example 1
```
## Curriculum

I had a degree in computer science. I have worked  years with  MQTT protocol.

## Question

How many years of experience do you have with IoT?

## Answer

4
```
## Example 1
```
## Curriculum

I had a degree in computer science. 

## Question

How many years of experience do you have with Bash?

## Answer

2
```

## Example 2
```
## Curriculum

I am a software engineer with 5 years of experience in Swift and Python. I have worked on an AI project.

## Question

How many years of experience do you have with AI?

## Answer

2
```

## Resume:
```
{resume_educations}
{resume_jobs}
{resume_projects}
```
        
## Question:
{question}

---

When responding, consider all available information, including projects, work experience, and academic background, to provide an accurate and well-reasoned answer. Make every effort to infer relevant experience and avoid defaulting to 0 if any related experience can be estimated.

"""

options_template = """The following is a resume and a question about the resume, the answer is one of the options.

## Rules
- Never choose the default/placeholder option, examples are: 'Select an option', 'None', 'Choose from the options below', 'My option', 'Your own option', 'Your own answer', 'Свой вариант', 'Свой ответ', etc.
- The answer must be one of the options.
- The answer must exclusively contain one of the options.

## Example
My resume: I'm a software engineer with 10 years of experience on swift, python, C, C++.
Question: How many years of experience do you have on python?
Options: [1-2, 3-5, 6-10, 10+]
10+

-----

## My resume:
```
{resume}
```

## Question:
{question}

## Options:
{options}

## """

many_options_template = """The following is a resume and a question about the resume, the answer is one or more of the options.

## Rules
- Never choose the default/placeholder option, examples are: 'Select an option', 'None', 'Choose from the options below', 'My option', 'Your own option', 'Your own answer', 'Свой вариант', 'Свой ответ', etc.
- The answer can be one or more options.
- Return answers as a comma separated string.

## Example
My resume: I'm a software engineer with 10 years of experience on swift, python, C, C++.
Question: What programming languages do you know?
Options: [python, C, rust, swift, ruby, C++, C#, go]
python, C, swift, C++

-----

## My resume:
```
{resume}
```

## Question:
{question}

## Options:
{options}

## """

try_to_fix_template = """\
The objective is to fix the text of a form input on a web page.

## Rules
- Use the error to fix the original text.
- The error "Please enter a valid answer" usually means the text is too large, shorten the reply to less than a tweet.
- For errors like "Enter a whole number between 3 and 30", just need a number.

-----

## Form Question
{question}

## Input
{input} 

## Error
{error}  

## Fixed Input
"""


summarize_prompt_template = """
As a seasoned HR expert, your task is to identify and outline the key skills and requirements necessary for the position of this job. Use the provided job description as input to extract all relevant information. This will involve conducting a thorough analysis of the job's responsibilities and the industry standards. You should consider both the technical and soft skills needed to excel in this role. Additionally, specify any educational qualifications, certifications, or experiences that are essential. Your analysis should also reflect on the evolving nature of this role, considering future trends and how they might affect the required competencies.

Rules:
Remove boilerplate text
Include only relevant information to match the job description against the resume

# Analysis Requirements
Your analysis should include the following sections:
Technical Skills: List all the specific technical skills required for the role based on the responsibilities described in the job description.
Soft Skills: Identify the necessary soft skills, such as communication abilities, problem-solving, time management, etc.
Educational Qualifications and Certifications: Specify the essential educational qualifications and certifications for the role.
Professional Experience: Describe the relevant work experiences that are required or preferred.
Role Evolution: Analyze how the role might evolve in the future, considering industry trends and how these might influence the required skills.

# Final Result:
Your analysis should be structured in a clear and organized document with distinct sections for each of the points listed above. Each section should contain:
This comprehensive overview will serve as a guideline for the recruitment process, ensuring the identification of the most qualified candidates.

# Job Description:
```
{text}
```

---

# Job Description Summary"""

func_summarize_prompt_template = """
        Following are two texts, one with placeholders and one without, the second text uses information from the first text to fill the placeholders.
        
        ## Rules
        - A placeholder is a string like "[[placeholder]]". E.g. "[[company]]", "[[job_title]]", "[[years_of_experience]]"...
        - The task is to remove the placeholders from the text.
        - If there is no information to fill a placeholder, remove the placeholder, and adapt the text accordingly.
        - No placeholders should remain in the text.
        
        ## Example
        Text with placeholders: "I'm a software engineer engineer with 10 years of experience on [placeholder] and [placeholder]."
        Text without placeholders: "I'm a software engineer with 10 years of experience."
        
        -----
        
        ## Text with placeholders:
        {text_with_placeholders}
        
        ## Text without placeholders:"""


# job_is_interesting = """
# Ты ищешь работу в сфере IT на сайте по поиску работы. Твоя задача, исходя из текста вакансии, текста резюме и списка навыков 
# опеределить, интересна ли данная работа тебе или нет. 
# Работа считается интересной, если в вакансии предлагают заниматься в той же области или теми же вещами, которыми ты занимался до этого,
# либо если больше половины указанных в вакансии навыков тебе известны, либо если то, чем предлагают заниматься на данной работе,
# находится в списке твоих интересов.
# ## Описание работы:
# ```
# {job_description}
# ```
# ## Твое резюме:
# ```
# {resume}
# ```
# ## Список твоих навыков:
# ```
# {skills}
# ```
# ## Список твоих интересов:
# ```
# {interests}
# ```
# В качестве ответа верни либо 'Yes', если считаешь, что вакансия тебе интересна, либо 'No' в противном случае.
# """

job_is_interesting = """
   Evaluate whether the provided resume meets the requirements outlined in the job description. Determine if the candidate is suitable for the job based on the information provided.

## Job Description:
```
{job_description}
```
## Resume:
```
{resume}
```
## Your skills:
```
{skills}
```
## Your interests:
```
{interests}
```

Instructions:
1. Extract the key requirements from the job description, identifying hard requirements (must-haves) and soft requirements (nice-to-haves).
2. Identify the relevant qualifications from the resume and skill list.
3. Compare the qualifications against the requirements, ensuring all hard requirements are met. Allow for a 1-year experience gap if applicable, as experience is usually a hard requirement.
4. Provide a suitability score from 1 to 10. where 1 indicates the candidate does not meet any requirements and 10 indicates the candidate meets all requirements.
5. If the job matches one or more of canditate's interests - add 1 point to the overall score.
6. Provide a brief reasoning for the score, highlighting which requirements are met and which are not.
7. If job description language is Russian - answer in Russian. Else answer in English.

Output Format (Strictly follow this format):
Score: [numerical score]
Reasoning: [brief explanation]
Do not output anything else in the response other than the score and reasoning.
"""

coverletter_template = """
Составь краткое и выразительное сопроводительное письмо на основе предоставленного описания вакансии и резюме. 
Письмо должно быть не длиннее пяти абзацев и должно быть написано в профессиональном, но разговорном тоне. 
Избегай использования каких-либо заполнителей и убедитесь, что письмо читается естественно и соответствует вакансии.
Проанализируй описание вакансии, чтобы определить ключевые квалификации и требования. 
В начале поприветствуй адресата и напиши, какая вакансия заинтересовала, а затем представь кандидата кратко, сопоставив его карьерные цели с вакансией. 
Выдели соответствующие навыки и опыт из резюме, которые напрямую соответствуют требованиям вакансии, используя конкретные примеры для иллюстрации этих квалификаций. 
Затем напиши, почему кандидат хорошо подходит для этой должности, выразив желание обсудить это более подробно.
В заключении поблагодари адресата за рассмотрение своей кандидатуры и предложи обсудить ваш опыт подробнее на собеседовании.
Напиши сопроводительное письмо таким образом, чтобы оно напрямую касалось должности и характеристик компании, 
при этом оно должно быть кратким и интересным, без ненужных украшений. Письмо должно быть отформатировано в абзацах.
Если описание вакансии написано на русском языке - напиши сопроводительное письмо также на русском языке. В противном случае напишите его на английском языке.

## Правила:
- Предоставь только текст сопроводительного письма.
- Письмо должно быть отформатировано в абзацы.
- Не упоминай имя компании в сопроводительном письме, в зависимости от описания вакансии, пиши 'ваша компания', 'ваша организация' или 'ваш банк'.
- Если обнаружишь какие-либо вопросы в описании вакансии - ответь на них в сопроводительном письме, после основного текста, используя информацию из резюме.
- Если в описании вакансии требуют указать в сопроводительном письме какие-либо слова - напиши их после основного текста (но только если такое требование действительно есть в тексте вакансии!).
- Не указывай никаких ссылок, в том числе на Github, LinkedIn и т.д.
- В конце указывай свой Telegram для связи (или телефон, но только в случае отсутствия Telegram!)

## Пример 1:
```
Добрый день!

Меня заинтересовала вакансия инженера-проектировщика в вашей компании. Обладаю высоким уровнем профессиональных знаний в области проектирования, 
а также работал с крупными проектами. Моё образование и опыт позволяют мне успешно решать сложные задачи и достигать поставленных целей.

Буду рад обсудить возможность сотрудничества.

С уважением, Даниил
```

## Пример 2:
```
Здравствуйте! Я бы хотел пройти стажировку в вашем банке. Я студент 3-го курса факультета информационных технологий в НИУ ВШЭ. Обладаю глубоким пониманием аналитики и креативным подходом к решению задач. 

Участвовал в создании программных решений для учебных проектов, занимался проверкой и анализом данных. Также успешно прошёл летнюю стажировку в ИТ-компании.

С уважением, Андрей


## Пример 3:
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

## Описание работы:
```
{job_description}
```
## Мое резюме:
```
{resume}
```
"""

fixed_cover_letter = """
Здравствуйте! Прошу рассмотреть моё резюме на роль разработчика Python в вашу компанию.

Кратко о себе:
- опыт работы: 4 года
- ожидания по зарплате: от 200000 до 400000 руб
- основной стек: Python, SQL, Django, React, REST API, Redis
- есть опыт работы с Docker/Docker Compose
- знаком с Airflow, FastAPI, Flask
- проекты веду в git

тг для связи: alexneth93
"""
