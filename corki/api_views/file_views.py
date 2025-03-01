import os
import uuid

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from corki.client.oss_client import OSSClient
from corki.util import resp_util

class FileViews(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        上传文件
        :param request:
        :return:
        """
        oss_client = OSSClient()
        file = request.FILES.get('file')
        if file:
            file_name = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"
            url = oss_client.put_object(file_name, file.read())
            return response_util.success({'url': url})
        return None
