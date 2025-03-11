from marker.output import text_from_rendered
from corki.util import pdf_converter


def extract_text_from_pdf(pdf_path):
    rendered = pdf_converter(pdf_path)
    text, _, _ = text_from_rendered(rendered)
    return text

if __name__ == '__main__':
    pdf_path = "/Users/gemushen/test-file/简历/java开发.pdf"
    text = extract_text_from_pdf(pdf_path)
    print(text)
