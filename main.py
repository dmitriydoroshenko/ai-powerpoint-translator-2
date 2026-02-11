import os
import glob
from pptx import Presentation
from pptx.oxml import parse_xml
import logging
from logger_config import setup_logging
from translator import translate_all
from file_utils import save_presentation
from wakepy import keep
import xml.etree.ElementTree as ET

setup_logging()

# Регистрируем пространства имен, чтобы ElementTree не переименовывал их в ns0, ns1 и т.д.
NAMESPACES = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)

def collect_xml_data(prs):
    """Извлекает XML текстовых блоков и таблиц."""
    xml_contents = []
    locations = []

    for s_idx, slide in enumerate(prs.slides):
        for sh_idx, shape in enumerate(slide.shapes):
            
            if hasattr(shape, "text_frame") and shape.text_frame:
                xml_contents.append(shape.text_frame._txBody.xml)
                locations.append(("text_frame", s_idx, sh_idx))

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
            new_element = parse_xml(new_xml)
            
            if location[0] == "text_frame":
                _, s_idx, sh_idx = location
                shape = prs.slides[s_idx].shapes[sh_idx]
                old_body = shape.text_frame._txBody
                old_body.getparent().replace(old_body, new_element)
                
            elif location[0] == "table_cell":
                _, s_idx, sh_idx, r_idx, c_idx = location
                cell = prs.slides[s_idx].shapes[sh_idx].table.rows[r_idx].cells[c_idx]
                old_body = cell.text_frame._txBody
                old_body.getparent().replace(old_body, new_element)
        except Exception as e:
            logging.error(f"Ошибка при вставке XML в {location}: {e}")

def strip_and_store_metadata(xml_string):
    """Вырезает служебные теги и возвращает чистый XML для перевода + объект метаданных."""
    root = ET.fromstring(xml_string)
    
    body_pr = root.find('a:bodyPr', NAMESPACES)
    lst_style = root.find('a:lstStyle', NAMESPACES)
    
    metadata = {
        'body_pr': body_pr,
        'lst_style': lst_style
    }

    if body_pr is not None:
        root.remove(body_pr)
    if lst_style is not None:
        root.remove(lst_style)
        
    return ET.tostring(root, encoding='unicode'), metadata

def restore_metadata(translated_xml_string, metadata):
    """Вставляет служебные теги обратно в переведенный XML."""
    root = ET.fromstring(translated_xml_string)
    
    if metadata['lst_style'] is not None:
        root.insert(0, metadata['lst_style'])
    if metadata['body_pr'] is not None:
        root.insert(0, metadata['body_pr'])
        
    return ET.tostring(root, encoding='unicode')

def process_presentation(input_file):
    logging.info(f"Обработка файла: {input_file}")
    print(f"\nОбработка файла: {os.path.basename(input_file)}")
    
    try:
        prs = Presentation(input_file)
        xml_contents, locations = collect_xml_data(prs)
        
        if not xml_contents:
            logging.info(f"В файле {input_file} текст не найден")
            return

        # --- Очистка XML перед отправкой ---
        stripped_xmls = []
        metadata_store = []
        
        for xml_content in xml_contents:
            clean_xml, meta = strip_and_store_metadata(xml_content)
            stripped_xmls.append(clean_xml)
            metadata_store.append(meta)

        logging.info(f"ПОДГОТОВКА: Найдено элементов: {len(stripped_xmls)}")
        for i, (loc, s_xml) in enumerate(zip(locations, stripped_xmls)):
            logging.info(f"--- ОТПРАВЛЯЕМЫЙ ОЧИЩЕННЫЙ XML (Элемент {i}, Локация {loc}) ---")
            logging.info(f"\n{s_xml}\n" + "-"*50)
        # ----------------------------------------------

        translated_stripped_xmls = translate_all(stripped_xmls)
        
        logging.info(f"ОТВЕТ ПОЛУЧЕН: Переведено элементов: {len(translated_stripped_xmls)}")

        # --- Восстановление метаданных ---
        final_xmls = []
        for t_xml, meta in zip(translated_stripped_xmls, metadata_store):
            try:
                restored_xml = restore_metadata(t_xml, meta)
                final_xmls.append(restored_xml)
            except Exception as e:
                logging.error(f"Ошибка при восстановлении метаданных: {e}")
                # Если восстановление не удалось, пробуем использовать то, что пришло
                final_xmls.append(t_xml)
        # ----------------------------------------------

        apply_xml_translations(prs, locations, final_xmls)
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
   with keep.running():
        main()
