import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SYSTEM_ROLE = (
    "## Role\n"
    "You are an expert Game Localization (L10N) Specialist and professional mobile game localizer. "
    "Your goal is to translate English mobile gaming market reports and game text into Simplified Chinese, "
    "ensuring the output is natural and uses industry-standard jargon used by developers and publishers.\n\n"

    "## Task\n"
    "1. Input: A JSON array of objects with 'id' and 'xml'.\n"
    "2. Action: Translate ONLY the text content within <a:t> tags in the provided XML to Simplified Chinese.\n"
    "3. Output: Return a JSON object with a key 'translations' containing the array of objects, "
    "each having the original 'id' and the 'translated_text' containing the modified XML.\n\n"

    "## Terminology & Style Guidelines\n"
    "- Do Not Translate Game Titles: Keep all game names/titles in their original English form.\n"
    "- Avoid Literalism: Do not translate word-for-word. Focus on industry 'jargon.'\n"
    "- Spending/Monetization:\n"
    "  * 'Non-paying players' -> 非付费玩家 / 零氪玩家\n"
    "  * 'Spending real money' -> 付费 / 氪金\n"
    "- Events & Scheduling:\n"
    "  * 'Global schedule' -> 全服统一日程 / 固定档期\n"
    "  * 'Progress in events' -> 推进活动进度\n"
    "- Tone: Professional, concise, and analytical. Use 'Game-speak.'\n"
)

def translate_all(texts, batch_size=10):
    if not texts:
        print("❌ Список текстов пуст.")
        return []

    start_time = time.perf_counter()
    total_texts = len(texts)

    batches = [texts[i:i + batch_size] for i in range(0, total_texts, batch_size)]
    total_batches = len(batches)
    
    results = [None] * total_texts
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    print(f"\n{'='*40}")
    print(f"🚀 ЗАПУСК ПЕРЕВОДА (Батчинг: {batch_size} стр/запрос)")
    print(f"Всего строк: {total_texts} | Батчей: {total_batches}")
    print(f"{'='*40}\n")

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch = {
            executor.submit(_translate_batch, [(i + start, texts[i + start]) 
            for i in range(len(batches[b_idx]))]): b_idx 
            for b_idx, start in enumerate(range(0, total_texts, batch_size))
        }
        
        completed_batches = 0
        for future in as_completed(future_to_batch):
            batch_results, usage = future.result()
            
            for idx, trans_text in batch_results:
                results[idx] = trans_text
            
            if usage:
                total_prompt_tokens += usage.prompt_tokens
                total_completion_tokens += usage.completion_tokens
            
            completed_batches += 1

            percent = (completed_batches / total_batches) * 100
            print(f"⏳ Батч {completed_batches}/{total_batches} завершен ({percent:.1f}%) | "
                  f"Строк обработано: {min(completed_batches * batch_size, total_texts)}")

    end_time = time.perf_counter()
    duration = end_time - start_time
    minutes, seconds = divmod(int(duration), 60)

    cost = (total_prompt_tokens * 1.75 / 1_000_000) + (total_completion_tokens * 14.00 / 1_000_000)

    print(f"\n{'='*40}")
    print(f"✅ ПЕРЕВОД ЗАВЕРШЕН")
    print(f"⏱ Время: {minutes} мин. {seconds} сек.")
    print(f"📊 Токены: Промпт: {total_prompt_tokens} | Ответ: {total_completion_tokens}")
    print(f"💰 Ориентировочная стоимость: ${cost:.4f}")
    print(f"{'='*40}\n")

    return results

def _translate_batch(batch):
    """
    Принимает список кортежей [(index, text), ...]
    Возвращает список [(index, translated_text), ...] и статистику токенов.
    """
    try:
        payload = [{"id": idx, "xml": text} for idx, text in batch]
        
        response = client.chat.completions.create(
            model="gpt-5.2",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        raw_content = response.choices[0].message.content
        
        if raw_content is None:
            print("⚠️ API вернул пустой ответ (None)")
            return [(idx, text) for idx, text in batch], response.usage

        content = json.loads(raw_content)
        translated_data = content.get("translations", [])
        
        translations_map = {item['id']: item['translated_text'] for item in translated_data}
        
        result_batch = []
        for idx, original_text in batch:
            translated_text = translations_map.get(idx, original_text)
            result_batch.append((idx, translated_text))
            
        return result_batch, response.usage

    except Exception as e:
        print(f"\n❌ Ошибка при обработке батча: {e}")
        return [(idx, text) for idx, text in batch], None