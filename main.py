import glob
import logging
from pptx import Presentation
from pptx.oxml import parse_xml
from wakepy import keep
from logger_config import setup_logging
from translator import translate_all
from file_utils import save_presentation
from xml_handler import XMLMetadataHandler

setup_logging()

def get_text_frames(prs):
    """Генератор, возвращающий все текстовые фреймы и их метаданные."""
    for s_idx, slide in enumerate(prs.slides):
        for sh_idx, shape in enumerate(slide.shapes):
            frames = []
            
            if shape.has_table:
                for r_idx, row in enumerate(shape.table.rows):
                    for c_idx, cell in enumerate(row.cells):
                        frames.append((cell.text_frame, ("table_cell", s_idx, sh_idx, r_idx, c_idx)))
            
            elif shape.has_chart:
                chart = shape.chart
                if chart.has_title and chart.chart_title.has_text_frame:
                    frames.append((chart.chart_title.text_frame, ("chart_title", s_idx, sh_idx)))
                
                for axis_type in ['category_axis', 'value_axis']:
                    try:
                        axis = getattr(chart, axis_type)
                        if axis.has_title:
                            frames.append((axis.axis_title.text_frame, (f"chart_{axis_type}", s_idx, sh_idx)))
                    except (ValueError, AttributeError):
                        continue
            
            elif hasattr(shape, "text_frame") and shape.text_frame:
                frames.append((shape.text_frame, ("text_frame", s_idx, sh_idx)))

            for tf, loc in frames:
                if tf and tf.text.strip():
                    yield tf, loc

def process_presentation(input_file):
    """
    Выполняет полный цикл обработки PPTX файла: извлечение текста, 
    перевод через XML-хендлеры с сохранением форматирования и сохранение результата.
    """
    logging.info(f"Обработка файла: {input_file}")
    try:
        prs = Presentation(input_file)
        
        items = list(get_text_frames(prs))
        if not items:
            return

        text_frames, locations = zip(*items)
        handlers = [XMLMetadataHandler(tf._txBody.xml) for tf in text_frames]
        stripped_xmls = [h.strip() for h in handlers]

        translated_xmls = translate_all(stripped_xmls)

        for tf, handler, t_xml, loc in zip(text_frames, handlers, translated_xmls, locations):
            try:
                restored_xml = handler.restore(t_xml)
                new_txBody = parse_xml(restored_xml)
                old_txBody = tf._txBody
                old_txBody.getparent().replace(old_txBody, new_txBody)
            except Exception as e:
                logging.error(f"Ошибка в {loc}: {e}")

        save_presentation(prs, input_file)
        
    except Exception as e:
        logging.error(f"Ошибка в {input_file}: {e}")

def main():
    for input_file in glob.glob('input/*.pptx'):
        process_presentation(input_file)

if __name__ == "__main__":
    with keep.running():
        main()
