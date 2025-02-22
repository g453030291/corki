from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


def extract_text_from_pdf(pdf_path):
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
    )
    rendered = converter(pdf_path)
    text, _, _ = text_from_rendered(rendered)
    return text

if __name__ == '__main__':
    pdf_path = "/Users/gemushen/test-file/简历/java开发.pdf"
    text = extract_text_from_pdf(pdf_path)
    print(text)
