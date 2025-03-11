import os
import uuid

from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from corki.client.oss_client import OSSClient
from corki.config.permissions import IsAuthedOrGuest
from corki.util import resp_util

class FileViews(APIView):
    permission_classes = [IsAuthedOrGuest]

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
            return resp_util.success({'url': url})
        return resp_util.error(500, '上传文件失败')
