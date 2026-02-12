import os

def save_presentation(prs, original_filename, callback=None):
    """Сохраняет презентацию в ту же папку, где лежит оригинал."""

    output_dir = os.path.dirname(os.path.abspath(original_filename))
    
    base_name = os.path.basename(original_filename)
    name_without_ext = os.path.splitext(base_name)[0]
    
    counter = 1
    while True:
        suffix = "" if counter == 1 else f" ({counter})"
        output_filename = os.path.join(output_dir, f"{name_without_ext}_cn{suffix}.pptx")
        
        if not os.path.exists(output_filename):
            break
        counter += 1

    try:
        prs.save(output_filename)
        message = f"💾 Файл сохранен рядом с оригиналом: {output_filename}"
        print(message)
        if callback:
            callback(message)
        return output_filename
    except Exception as e:
        error_msg = f"❌ Ошибка при записи {output_filename}: {e}"
        print(error_msg)
        if callback:
            callback(error_msg)
        raise e