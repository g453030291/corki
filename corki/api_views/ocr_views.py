import json
import os

import json_repair
from rest_framework.views import APIView

from corki.client import doubao_client
from corki.config.constant import TMP_PATH
from corki.config.permissions import IsAuthenticatedOrGuest
from corki.util import file_util, ocr_util, resp_util


class OCRViews(APIView):
    permission_classes = [IsAuthenticatedOrGuest]
    allow_guest = True

    def post(self, request):
        data = json.loads(request.body)
        jd_url = data.get('jd_url')
        path = TMP_PATH + os.path.basename(jd_url)
        file_util.download_file(path, jd_url)
        text = ocr_util.extract_text_from_image(path)
        completion_response = doubao_client.completions(
            system_prompts="下面是一个 ocr 识别的结果,我需要你去掉无意义的符号,帮我整理为json格式返回给我。分为两部分,职位名称和职位描述(工作职责,任职资格)"
                           "output_format: json,"
                           "schema: {'jd_title':'', 'jd_content':''}",
            user_prompts="".join(text)
        )
        decoded_object = json_repair.loads(completion_response.replace("```", "").replace("json", ""))
        os.remove(path)
        return resp_util.success(decoded_object)
