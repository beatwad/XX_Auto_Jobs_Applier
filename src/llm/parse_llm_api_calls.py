"""
Данный файл предназначен для того, чтобы вытаскивать описания вакансии
и соответствующие им сопроводительные письма из логов LLM API и выводить
их в терминал.
"""

import json

with open("data_folder/output/llm_api_calls.json", "r", encoding="utf-8") as f:
    json_list = json.load(f)

def get_job_description(json_list: list, idx: int = 0):
    prompt = json_list[idx]["prompts"]["prompt_1"]
    begin = prompt.find("## Описание работы:\n```")
    end = prompt.find("```\n## Мое резюме:")
    if end < 0:
        return ""
    job_description = prompt[begin:end]
    return job_description[24:-1]

rec_num = 1

for idx in range(len(json_list)):
    job_description = get_job_description(json_list, idx)
    if not job_description:
        continue
    reply = json_list[idx]['replies']
    print(f"Номер записи {rec_num}")
    print(80 * "#")
    print("Описание работы")
    print(80 * "#")
    print(job_description)
    print(80 * "#")
    if reply in ["Yes", "No"]:
        print("Интересует вакансия?")
        print(80 * "#")
        print("Да" if reply == "Yes" else "Нет")
    else:
        print("Сопроводительное письмо")
        print(80 * "#")
        print(reply)
    print(2 * "\n")
    rec_num += 1