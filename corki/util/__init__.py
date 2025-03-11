import threading
import time
import traceback

from loguru import logger
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from corki.settings import IS_PROD

# Initialize as None
pdf_converter = None

def initialize_pdf_converter():
    """Initialize the PDF converter in a background thread after a delay."""
    global pdf_converter
    # Wait for 10 seconds
    time.sleep(30)
    try:
        logger.info("Starting PDF converter initialization...")
        pdf_converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        logger.info("PDF converter initialization complete")
    except Exception as e:
        logger.error(f"Error initializing PDF converter: {traceback.format_exc()}")

# Start the delayed initialization only in production
if IS_PROD:
    # Start the initialization in a background thread
    init_thread = threading.Thread(target=initialize_pdf_converter, daemon=True)
    init_thread.start()

def get_pdf_converter():
    """Get the PDF converter, initializing it if necessary."""
    global pdf_converter
    if pdf_converter is None:
        logger.info("PDF converter not initialized yet, initializing now...")
        pdf_converter = PdfConverter(
            artifact_dict=create_model_dict()
        )
        logger.info("PDF converter initialization complete")
    return pdf_converter
