import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

client = None

def set_api_key(api_key):
    """Инициализирует клиента OpenAI."""
    global client
    client = OpenAI(api_key=api_key)

def validate_api_key(api_key):
    """Проверка ключа без списания токенов за генерацию."""
    try:
        test_client = OpenAI(api_key=api_key)
        test_client.models.list()
        return True, ""
    except Exception as e:
        return False, str(e)

TECHNICAL_INSTRUCTIONS = (
    "## Technical Role\n"
    "You are a JSON-to-JSON translation engine. Your task is to process game data strings while preserving metadata.\n\n"
    "## Data Handling\n"
    "1. Input Format: A JSON array of objects with 'id' and 'xml'.\n"
    "2. XML Integrity: You MUST preserve all XML tags (e.g., <a:t>, <c:v>, <br/>) exactly as they are. Only translate the text content inside the tags.\n"
    "3. Output Format: Return a JSON object with the key 'translations'. Each item must contain the original 'id' and the 'translated_text'.\n"
    "4. Format Strictness: Use ONLY valid JSON in your response.\n"
)

LOCALIZATION_GUIDELINES = (
    "## Localization (L10N) Specialist Role\n"
    "You are a professional mobile game localizer (EN to Simplified Chinese).\n\n"
    "## Style & Jargon\n"
    "- Tone: Professional, analytical, and concise. Use native 'Game-speak'.\n"
    "- Do Not Translate Game Titles: Keep all game names/titles in their original English form.\n"
    "- No Literalism: Avoid word-for-word translations. Use industry-standard terms.\n\n"
    "## Terminology Mapping\n"
    "- 'Non-paying players' -> 非付费玩家 or 零氪玩家 (depending on context)\n"
    "- 'Spending real money' -> 付费 or 氪金\n"
    "- 'Global schedule' -> 全服统一日程 / 固定档期\n"
    "- 'Progress in events' -> 推进活动进度\n"
)

SYSTEM_ROLE = f"{TECHNICAL_INSTRUCTIONS}\n{LOCALIZATION_GUIDELINES}"

def translate_all(texts, batch_size=10, status_callback=None):
    def log(message):
        if status_callback:
            status_callback(message)

    if client is None:
        log("❌ Ошибка: API клиент не настроен.")
        return texts

    if not texts:
        log("⚠️ Нет текста для перевода.")
        return []

    start_time = time.perf_counter()
    total_texts = len(texts)

    batches = [texts[i:i + batch_size] for i in range(0, total_texts, batch_size)]
    total_batches = len(batches)
    
    results = [None] * total_texts
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    log(f"\n{'='*40}")
    log(f"🚀 ЗАПУСК ПЕРЕВОДА (Батчинг: {batch_size} стр/запрос)")
    log(f"Всего строк: {total_texts} | Батчей: {total_batches}")
    log(f"{'='*40}\n")

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch = {
            executor.submit(_translate_batch, [(i + start, texts[i + start]) 
            for i in range(len(batches[b_idx]))], log): b_idx 
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
            log(f"⏳ Батч {completed_batches}/{total_batches} завершен ({percent:.1f}%) | "
                f"Строк обработано: {min(completed_batches * batch_size, total_texts)}")

    end_time = time.perf_counter()
    duration = end_time - start_time
    minutes, seconds = divmod(int(duration), 60)

    cost = (total_prompt_tokens * 1.75 / 1_000_000) + (total_completion_tokens * 14.00 / 1_000_000)

    log(f"\n{'='*40}")
    log(f"✅ ПЕРЕВОД ЗАВЕРШЕН")
    log(f"⏱ Время: {minutes} мин. {seconds} сек.")
    log(f"📊 Токены: Промпт: {total_prompt_tokens} | Ответ: {total_completion_tokens}")
    log(f"💰 Ориентировочная стоимость: ${cost:.4f}")
    log(f"{'='*40}\n")

    return results

def _translate_batch(batch, log_func):
    """Выполняет перевод батча"""
    if client is None:
        log_func("❌ Ошибка: клиент не инициализирован")
        return batch, None

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
        
        content_raw = response.choices[0].message.content
        if content_raw is None:
            return batch, response.usage

        res_data = json.loads(content_raw)
        translations = res_data.get("translations", [])
        t_map = {item['id']: item['translated_text'] for item in translations}
        
        return [(idx, t_map.get(idx, original)) for idx, original in batch], response.usage
        
    except Exception as e:
        log_func(f"❌ Ошибка в батче: {str(e)}")
        return batch, None
