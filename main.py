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
from xml_handler import XMLMetadataHandler, NAMESPACES

setup_logging()

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

def process_presentation(input_file):
    logging.info(f"Обработка файла: {input_file}")
    print(f"\nОбработка файла: {os.path.basename(input_file)}")
    
    try:
        prs = Presentation(input_file)
        xml_contents, locations = collect_xml_data(prs)
        
        if not xml_contents:
            logging.info(f"В файле {input_file} текст не найден")
            return

        handlers = []
        stripped_xmls = []
        
        for xml_content in xml_contents:
            handler = XMLMetadataHandler(xml_content)
            clean_xml = handler.strip()
            handlers.append(handler)
            stripped_xmls.append(clean_xml)

        logging.info(f"ПОДГОТОВКА: Найдено элементов: {len(stripped_xmls)}")
        for i, (loc, xml) in enumerate(zip(locations, stripped_xmls)):
            loc_info = f"Тип: {loc[0]}, Слайд: {loc[1]+1}"
            logging.info(f"Элемент #{i} [{loc_info}] | ПОЛНЫЙ XML ДЛЯ ПЕРЕВОДА: {xml}\n")

        translated_stripped_xmls = translate_all(stripped_xmls)
        
        logging.info(f"ОТВЕТ ПОЛУЧЕН: Переведено элементов: {len(translated_stripped_xmls)}")

        final_xmls = []
        for handler, t_xml in zip(handlers, translated_stripped_xmls):
            try:
                restored_xml = handler.restore(t_xml)
                final_xmls.append(restored_xml)
            except Exception as e:
                logging.error(f"Ошибка при восстановлении метаданных: {e}")
                final_xmls.append(t_xml)

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
