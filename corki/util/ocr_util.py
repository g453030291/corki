import traceback

from loguru import logger
from paddleocr import PaddleOCR

def extract_text_from_image(img_path):
    """
    Extract text from an image using PaddleOCR.

    Args:
        img_path (str): The path to the image file.

    Returns:
        List[str]: A list of recognized text strings.
    """
    text_results = []
    try:
        ocr = PaddleOCR(use_angle_cls=True, lang='ch')
        result = ocr.ocr(img_path, cls=True)
        for res in result:
            for line in res:
                text_results.append(line[1][0])
    except Exception as e:
        logger.error(f"Error in OCR processing: {traceback.format_exc()}")
    return text_results

if __name__ == '__main__':
    img_path = "/Users/gen/test-file/简历/testjd.jpg"
    text = extract_text_from_image(img_path)
    print(text)
