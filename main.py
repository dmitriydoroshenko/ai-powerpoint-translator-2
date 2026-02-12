import glob
from pptx import Presentation
from pptx.oxml import parse_xml
from wakepy import keep
from translator import translate_all
from file_utils import save_presentation
from xml_handler import XMLMetadataHandler

def collect_translatable_items(prs):
    """Собирает все объекты для перевода и их типы в плоский список."""
    items = []
    
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        if cell.text_frame.text.strip():
                            items.append((cell.text_frame, "frame"))
            
            elif shape.has_chart:
                chart = shape.chart
                nodes = chart._element.xpath('.//c:v | .//a:t') 
                
                for node in nodes:
                    if node.text and node.text.strip():
                        if not node.text.replace('.', '', 1).isdigit():
                            items.append((node, "xml_node"))

                if chart.has_title and chart.chart_title.has_text_frame:
                    items.append((chart.chart_title.text_frame, "frame"))
                
                for axis_type in ['category_axis', 'value_axis']:
                    try:
                        axis = getattr(chart, axis_type)
                        if axis.has_title and axis.axis_title.has_text_frame:
                            items.append((axis.axis_title.text_frame, "frame"))
                    except (ValueError, AttributeError):
                        continue
            
            elif hasattr(shape, "text_frame") and shape.text_frame:
                if shape.text_frame.text.strip():
                    items.append((shape.text_frame, "frame"))
                    
    return items

def process_presentation(input_file):
    """
    Выполняет полный цикл обработки PPTX: извлечение текста, 
    перевод фреймов и элементов графиков, сохранение результата.
    """
    try:
        prs = Presentation(input_file)
        work_items = collect_translatable_items(prs)
        
        if not work_items:
            print(f"Нет текста для перевода в {input_file}")
            return

        to_translate = []
        handlers = []

        for obj, kind in work_items:
            if kind == "frame":
                h = XMLMetadataHandler(obj._txBody.xml)
                handlers.append(h)
                to_translate.append(h.strip())
            else:
                to_translate.append(obj.text)
                handlers.append(None)

        translated_results = translate_all(to_translate)

        for (obj, kind), handler, translated_text in zip(work_items, handlers, translated_results):
            if not translated_text:
                continue
            try:
                if kind == "frame" and handler:
                    new_xml = handler.restore(translated_text)
                    new_txBody = parse_xml(new_xml)
                    obj._txBody.getparent().replace(obj._txBody, new_txBody)
                else:
                    obj.text = translated_text
            except Exception as e:
                print(f"❌ Ошибка применения перевода: {e}")

        save_presentation(prs, input_file)
        
    except Exception as e:
        print(f"❌ Критическая ошибка в {input_file}: {e}")

def main():
    for input_file in glob.glob('input/*.pptx'):
        process_presentation(input_file)

if __name__ == "__main__":
    with keep.running():
        main()
