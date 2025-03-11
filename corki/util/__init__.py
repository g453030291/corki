# Pre-initialize the PDF converter on module import
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from corki.settings import IS_PROD

# Global cached converter that will be initialized when this module is imported
if IS_PROD:
    pdf_converter = PdfConverter(
        artifact_dict=create_model_dict(),
    )
else:
    pdf_converter = None

def get_pdf_converter():
    global pdf_converter
    if pdf_converter is None:
        pdf_converter = PdfConverter(
            artifact_dict=create_model_dict()
        )
    return pdf_converter
