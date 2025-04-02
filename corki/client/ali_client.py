import json
import os
import sys

import django
from loguru import logger
os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()
from corki.models.interview import InterviewRecord



from typing import List, Dict, Any

from alibabacloud_ocr_api20210707.client import Client as OcrApiClient
from alibabacloud_docmind_api20220711.client import Client as DocmindApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707 import models as ocr_api_models
from alibabacloud_docmind_api20220711 import models as docmind_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient


class AliClient:
    def __init__(self):
        pass

    @staticmethod
    def create_ocr_client() -> OcrApiClient:
        """
        Create Alibaba Cloud OCR client using access keys
        @return: OCR API Client
        @throws Exception
        """
        config = open_api_models.Config(
            access_key_id=os.getenv('ALI_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALI_ACCESS_KEY_SECRET'),
        )
        config.endpoint = 'ocr-api.cn-hangzhou.aliyuncs.com'
        return OcrApiClient(config)

    @staticmethod
    def create_docmind_client() -> DocmindApiClient:
        """
        Create Alibaba Cloud DocMind client using access keys
        @return: DocMind API Client
        @throws Exception
        """
        config = open_api_models.Config(
            access_key_id=os.getenv('ALI_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALI_ACCESS_KEY_SECRET'),
        )
        config.endpoint = 'docmind-api.cn-hangzhou.aliyuncs.com'
        return DocmindApiClient(config)

    @staticmethod
    def ocr(url: str) -> str:
        """
        Perform OCR on an image URL
        @param url: URL of the image
        @return: Extracted text content
        """
        client = AliClient.create_ocr_client()
        recognize_basic_request = ocr_api_models.RecognizeBasicRequest(
            url=url,
            need_rotate=False
        )
        try:
            result = client.recognize_basic_with_options(recognize_basic_request, util_models.RuntimeOptions())
            result_dict = json.loads(result.body.data)
            return result_dict['content']
        except Exception as error:
            logger.error(error.message)
            logger.error(error.data.get("Recommend"))
            return ""

    @staticmethod
    def doc_mind(url: str, file_name: str) -> str:
        """
        Process document structure using DocMind API
        @param url: URL of the document file
        @param file_name: Name of the file
        @return: Document structure analysis result
        """
        client = AliClient.create_docmind_client()
        request = docmind_api_models.SubmitDigitalDocStructureJobRequest(
            file_url=url,
            file_name=file_name,
            reveal_markdown=True,
        )
        try:
            response = client.submit_digital_doc_structure_job(request)
            resp_dict = response.body.to_map()
            layouts_list = resp_dict.get('Data')['layouts']
            all_text = ''.join(layout.get('text', '') for layout in layouts_list)
            return all_text
        except Exception as error:
            logger.error(error.message)
            logger.error(error.data.get("Recommend"))
            return {}


if __name__ == '__main__':
    InterviewRecord.objects.create()
    # ocr_result = AliClient.ocr('https://corki-oss.oss-cn-beijing.aliyuncs.com/2025/03/31/14f6e418e3f643799361eb807d75ead5.jpg')
    # print(ocr_result)

    # Example of using doc_mind method
    # doc_result = AliClient.doc_mind(
    #     url='https://corki-oss.oss-cn-beijing.aliyuncs.com/2025/03/12/2dc6776f093049eb9d8f0cd323543c78.pdf',
    #     file_name='2dc6776f093049eb9d8f0cd323543c78.pdf'
    # )
    # print(doc_result)