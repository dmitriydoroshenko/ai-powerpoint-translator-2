import os
import glob
from pptx import Presentation
import logging
from logger_config import setup_logging
from translator import translate_all
from file_utils import save_presentation
import re

setup_logging()

def extract_and_replace_links(paragraph, hlink_storage, hlink_counter):
    """Заменяет текст ссылки на маркер и сохраняет объект гиперссылки."""
    for run in paragraph.runs:
        hlink = run.hyperlink
        
        if hlink.address:
            marker = f"[[HLINK_{hlink_counter}]]"
            
            hlink_info = {
                "id": hlink_counter,
                "url": hlink.address,
                "original_text": run.text,
                "font_size": run.font.size if run.font.size else None,
                "bold": run.font.bold,
                "italic": run.font.italic,
                "color": run.font.color.rgb if run.font.color and hasattr(run.font.color, 'rgb') else None
            }
            
            hlink_storage[marker] = hlink_info
            
            logging.info(f"Найдена ссылка: {marker} | Полные данные: {hlink_info}")
            
            run.hyperlink.address = None
            run.text = marker
            
            hlink_counter += 1
            
    return hlink_counter

def collect_text_data(prs):
    """Извлекает весь текст из презентации, заменяя гиперссылки маркерами."""
    all_texts = []
    text_locations = []
    hlink_storage = {}
    hlink_counter = 0

    for s_idx, slide in enumerate(prs.slides):
        for sh_idx, shape in enumerate(slide.shapes):
            
            # 1. Обработка обычных текстовых блоков
            if hasattr(shape, "text_frame"):
                for p_idx, para in enumerate(shape.text_frame.paragraphs):
                    hlink_counter = extract_and_replace_links(para, hlink_storage, hlink_counter)
                    if para.text.strip():
                        all_texts.append(para.text.strip())
                        text_locations.append(("paragraph", s_idx, sh_idx, p_idx))

            # 2. Обработка таблиц
            if shape.has_table:
                for r_idx, row in enumerate(shape.table.rows):
                    for c_idx, cell in enumerate(row.cells):
                        for p_idx, para in enumerate(cell.text_frame.paragraphs):
                            hlink_counter = extract_and_replace_links(para, hlink_storage, hlink_counter)
                            
                            if para.text.strip():
                                all_texts.append(para.text.strip())
                                text_locations.append(("table", s_idx, sh_idx, r_idx, c_idx, p_idx))
    
    return all_texts, text_locations, hlink_storage

def restore_hyperlinks(paragraph, hlink_storage):
    """Находит маркеры [[HLINK_X]] и восстанавливает их как кликабельные ссылки."""
    marker_pattern = re.compile(r"(\[\[HLINK_\d+\]\])")
    full_text = paragraph.text

    if not marker_pattern.search(full_text):
        return

    # Очищаем параграф от существующих runs
    p_element = paragraph._p
    for run in paragraph.runs:
        p_element.remove(run._r)

    # Разбиваем текст на части (маркеры и обычный текст)
    parts = marker_pattern.split(full_text)

    for part in parts:
        if not part:
            continue
        
        run = paragraph.add_run()
        
        if marker_pattern.match(part):
            info = hlink_storage.get(part)
            if info:
                run.text = info["original_text"]
                run.hyperlink.address = info["url"]
                if info["color"]:
                    run.font.color.rgb = info["color"]
                if info["font_size"]:
                    run.font.size = info["font_size"]
                run.font.bold = info["bold"]
                run.font.italic = info["italic"]
            else:
                run.text = part
        else:
            run.text = part

def _update_paragraph_formatting(paragraph, translated_text, hlink_storage):
    """Обновление текста и восстановление ссылок."""
    original_alignment = paragraph.alignment
    original_level = paragraph.level

    orig_color = None
    if paragraph.runs:
        try:
            if hasattr(paragraph.runs[0].font.color, 'rgb'):
                orig_color = paragraph.runs[0].font.color.rgb
        except: pass

    original_font_sizes = [
        run.font.size if hasattr(run, "font") and hasattr(run.font, "size") else None 
        for run in paragraph.runs
    ]
    
    paragraph.text = translated_text
    
    for idx, run in enumerate(paragraph.runs):
        run.font.name = "Microsoft YaHei"
        if idx < len(original_font_sizes) and original_font_sizes[idx] is not None:
            run.font.size = original_font_sizes[idx]
        if orig_color:
            run.font.color.rgb = orig_color

    paragraph.alignment = original_alignment
    paragraph.level = original_level

    restore_hyperlinks(paragraph, hlink_storage)

def apply_translations(prs, text_locations, translated_texts, hlink_storage):
    """Обновляет презентацию переведенным текстом."""
    for location, translated_text in zip(text_locations, translated_texts):
        if location[0] == "paragraph":
            _, slide_idx, shape_idx, para_idx = location
            shape = prs.slides[slide_idx].shapes[shape_idx]
            if hasattr(shape, "text_frame") and para_idx < len(shape.text_frame.paragraphs):
                para = shape.text_frame.paragraphs[para_idx]
                _update_paragraph_formatting(para, translated_text, hlink_storage)

        elif location[0] == "table":
            _, slide_idx, shape_idx, row_idx, cell_idx, para_idx = location
            shape = prs.slides[slide_idx].shapes[shape_idx]
            if shape.has_table:
                cell = shape.table.rows[row_idx].cells[cell_idx]
                if hasattr(cell, "text_frame") and para_idx < len(cell.text_frame.paragraphs):
                    para = cell.text_frame.paragraphs[para_idx]
                    _update_paragraph_formatting(para, translated_text, hlink_storage)

def process_presentation(input_file):
    """Основной цикл обработки файла."""
    logging.info(f"Обработка файла: {input_file}")
    print(f"\nОбработка файла: {os.path.basename(input_file)}")
    
    try:
        prs = Presentation(input_file)
        all_texts, text_locations, hlink_storage = collect_text_data(prs)
        
        if not all_texts:
            logging.info(f"В файле {input_file} текст не найден")
            return
        
        translated_texts = translate_all(all_texts)
        
        logging.info(f"--- Результаты перевода для {os.path.basename(input_file)} ---")
        for orig, trans in zip(all_texts, translated_texts):
            logging.info(f"EN: {orig}")
            logging.info(f"CN: {trans}")
            logging.info("-" * 20)

        apply_translations(prs, text_locations, translated_texts, hlink_storage)
        save_presentation(prs, input_file)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке презентации {input_file}: {str(e)}")
        raise

def main():
    input_files = glob.glob('input/*.pptx')
    
    if not input_files:
        logging.warning("В директории input не найдено файлов PowerPoint")
        print("В директории input не найдено файлов PowerPoint")
        return
    
    for input_file in input_files:
        logging.info(f"\n=== Обработка файла: {input_file} ===")
        process_presentation(input_file)
        logging.info(f"Перевод файла {input_file} завершен")

if __name__ == "__main__":
    main()