import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_ROLE = (
    "You are a professional mobile game localizer. "
    "Task: Translate ONLY the text content within <a:t> tags in the provided XML to Simplified Chinese. "
    "IMPORTANT RULES: "
    "1. STRUCTURE: You may reorder XML elements (e.g., <a:r> blocks) to match natural Chinese word order, but do not add or remove any tags."
    "2. ATTRIBUTES: Never translate or change XML attributes (e.g., id, lang, dirty). "
    "3. OUTPUT: Return ONLY a valid JSON object with the key 'translated_text'."
)

def _translate_single(text, index):
    """
    Вспомогательная функция для одного запроса. 
    Возвращает индекс, чтобы сохранить порядок строк после параллельного выполнения.
    """
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
        translated_text = json.loads(content).get("translated_text", text) if content else text
        return index, translated_text, response.usage

    except Exception as e:
        print(f"Ошибка в строке {index + 1}: {e}")
        return index, text, None

def translate_all(texts):
    if not texts:
        print("Список текстов пуст.")
        return []

    start_time = time.perf_counter()
    total_texts = len(texts)
    
    results = [None] * total_texts
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    print(f"\n{'='*20}")
    print(f"🚀 ПАРАЛЛЕЛЬНЫЙ ПЕРЕВОД (100 потоков)")
    print(f"Всего строк: {total_texts}")
    print(f"{'='*20}\n")

    with ThreadPoolExecutor(max_workers=100) as executor:
        # Создаем список задач
        futures = {executor.submit(_translate_single, text, i): i for i, text in enumerate(texts)}
        
        completed_count = 0
        for future in as_completed(futures):
            index, translated_text, usage = future.result()
            results[index] = translated_text
            
            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens
            
            completed_count += 1
            if completed_count % 5 == 0 or completed_count == total_texts:
                print(f"⏳ Готово: {completed_count}/{total_texts}")

    end_time = time.perf_counter()
    duration = end_time - start_time
    minutes, seconds = divmod(int(duration), 60)

    cost = (total_prompt_tokens * 1.75 / 1_000_000) + (total_completion_tokens * 14.00 / 1_000_000)

    print(f"\n\n{'='*20}")
    print(f"✅ ПЕРЕВОД ЗАВЕРШЕН")
    print(f"Затраченное время: {minutes} мин. {seconds} сек.")
    print(f"Токены: {total_prompt_tokens + total_completion_tokens} | Стоимость: ${cost:.4f}")
    print(f"{'='*20}\n")

    return results
