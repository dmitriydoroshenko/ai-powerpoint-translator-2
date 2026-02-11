import xml.etree.ElementTree as ET

NAMESPACES = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
}

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)

class XMLMetadataHandler:
    def __init__(self, xml_string):
        self.root = ET.fromstring(xml_string)
        self.metadata = {}

    def strip(self):
        """Удаляет технические теги (bodyPr, lstStyle) и возвращает чистый XML."""
        tags_to_save = {
            'body_pr': 'a:bodyPr',
            'lst_style': 'a:lstStyle'
        }
        
        for key, tag in tags_to_save.items():
            element = self.root.find(tag, NAMESPACES)
            if element is not None:
                self.metadata[key] = element
                self.root.remove(element)
                
        return ET.tostring(self.root, encoding='unicode')

    def restore(self, translated_xml_string):
        """Вставляет сохраненные теги обратно в переведенный XML."""
        new_root = ET.fromstring(translated_xml_string)
        
        if self.metadata.get('lst_style') is not None:
            new_root.insert(0, self.metadata['lst_style'])
        if self.metadata.get('body_pr') is not None:
            new_root.insert(0, self.metadata['body_pr'])
            
        return ET.tostring(new_root, encoding='unicode')
