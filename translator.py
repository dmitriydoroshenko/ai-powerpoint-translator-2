import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_ROLE = (
    "You are a professional mobile game localizer. "
    "Task: Translate ONLY the text content within <a:t> tags in the provided XML to Simplified Chinese. "
    "IMPORTANT RULES: "
    "1. STRUCTURE: Do not modify, add, or remove any XML tags (e.g., <a:r>, <a:p>, <a:t>). "
    "2. ATTRIBUTES: Never translate or change XML attributes (e.g., id, lang, dirty). "
    "3. OUTPUT: Return ONLY a valid JSON object with the key 'translated_text'."
)

def translate_all(texts):
    if not texts:
        print("Список текстов пуст.")
        return []

    start_time = time.perf_counter()
    total_texts = len(texts)
    translated_result = []
    
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    print(f"\n{'='*20}")
    print(f"🚀 НАЧАЛО ПЕРЕВОДА (ПОСТРОЧНО)")
    print(f"Всего строк: {total_texts}")
    print(f"{'='*20}\n")

    for i, text in enumerate(texts):
        original_len = len(text)
        print(f"⏳ Перевод строки {i+1}/{total_texts} | Длина: {original_len} симв.")
        
        translated_text, usage = _translate_single(text)
        translated_result.append(translated_text)
        
        if usage:
            total_prompt_tokens += usage.prompt_tokens
            total_completion_tokens += usage.completion_tokens

    end_time = time.perf_counter()
    duration = end_time - start_time
    minutes = int(duration // 60)
    seconds = int(duration % 60)

    cost = (total_prompt_tokens * 1.75 / 1_000_000) + (total_completion_tokens * 14.00 / 1_000_000)

    print(f"\n\n{'='*20}")
    print(f"✅ ПЕРЕВОД ЗАВЕРШЕН")
    print(f"Итого обработано строк: {len(translated_result)}")
    print(f"Затраченное время: {minutes} мин. {seconds} сек.")
    print(f"Токены: {total_prompt_tokens + total_completion_tokens} | Общая стоимость: ${cost:.4f}")
    print(f"{'='*20}\n")

    return translated_result

def _translate_single(text):
    try:
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": f"Translate this XML text: {text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        content = response.choices[0].message.content
        if content:
            data = json.loads(content)
            translated_text = data.get("translated_text", text)
        else:
            translated_text = text

        return translated_text, response.usage
    except Exception as e:
        print(f"Ошибка при обработке строки: {e}")
        return text, None
