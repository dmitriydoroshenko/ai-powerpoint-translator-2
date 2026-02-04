import os
import glob
from pptx import Presentation
from pptx.oxml import parse_xml
import logging
from logger_config import setup_logging
from translator import translate_all
from file_utils import save_presentation

setup_logging()

def collect_xml_data(prs):
    """Извлекает XML текстовых блоков и таблиц."""
    xml_contents = []
    locations = []

    for s_idx, slide in enumerate(prs.slides):
        for sh_idx, shape in enumerate(slide.shapes):
            
            # Обработка текстовых фреймов
            if hasattr(shape, "text_frame") and shape.text_frame:
                xml_contents.append(shape.text_frame._txBody.xml)
                locations.append(("text_frame", s_idx, sh_idx))

            # Обработка таблиц
            if shape.has_table:
                for r_idx, row in enumerate(shape.table.rows):
                    for c_idx, cell in enumerate(row.cells):
                        if hasattr(cell, "text_frame") and cell.text_frame:
                            xml_contents.append(cell.text_frame._txBody.xml)
                            locations.append(("table_cell", s_idx, sh_idx, r_idx, c_idx))
    
    return xml_contents, locations

def apply_xml_translations(prs, locations, translated_xmls):
    """Заменяет оригинальные XML элементы переведенными."""
    for location, new_xml in zip(locations, translated_xmls):
        try:
            # Парсим полученную строку обратно в XML объект
            new_element = parse_xml(new_xml)
            
            if location[0] == "text_frame":
                _, s_idx, sh_idx = location
                shape = prs.slides[s_idx].shapes[sh_idx]
                # Заменяем старый _txBody на новый переведенный
                old_body = shape.text_frame._txBody
                old_body.getparent().replace(old_body, new_element)
                
            elif location[0] == "table_cell":
                _, s_idx, sh_idx, r_idx, c_idx = location
                cell = prs.slides[s_idx].shapes[sh_idx].table.rows[r_idx].cells[c_idx]
                old_body = cell.text_frame._txBody
                old_body.getparent().replace(old_body, new_element)
        except Exception as e:
            logging.error(f"Ошибка при вставке XML в {location}: {e}")

def process_presentation(input_file):
    logging.info(f"Обработка файла: {input_file}")
    print(f"\nОбработка файла: {os.path.basename(input_file)}")
    
    try:
        prs = Presentation(input_file)
        
        # Шаг 1: Сбор XML
        xml_contents, locations = collect_xml_data(prs)
        
        if not xml_contents:
            logging.info(f"В файле {input_file} текст не найден")
            return
        
        # Шаг 2: Перевод
        translated_xmls = translate_all(xml_contents)
        
        # Шаг 3: Применение
        apply_xml_translations(prs, locations, translated_xmls)
        
        # Шаг 4: Сохранение
        save_presentation(prs, input_file)
        
    except Exception as e:
        logging.error(f"Ошибка при обработке презентации {input_file}: {str(e)}")
        raise

def main():
    input_files = glob.glob('input/*.pptx')
    if not input_files:
        print("В директории input не найдено файлов PowerPoint")
        return
    
    for input_file in input_files:
        process_presentation(input_file)
        logging.info(f"Перевод файла {input_file} завершен")

if __name__ == "__main__":
    main()