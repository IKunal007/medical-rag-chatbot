from docx import Document

def extract_docx_text(file_path: str):
    doc = Document(file_path)
    text_blocks = []

    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            text_blocks.append({
                "page": None,        
                "text": text
            })

    return text_blocks
