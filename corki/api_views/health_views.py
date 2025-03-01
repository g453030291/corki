from django.db import connections
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from corki.util import resp_util


class LivenessViews(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return resp_util.success({'status': 'ok'})

class ReadinessViews(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # 尝试连接数据库
            for conn in connections.all():
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return resp_util.error(500, {'status': 'error'})
        return resp_util.success({'status': 'ok'})
