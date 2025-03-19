import json

from rest_framework.views import APIView

from corki.config.permissions import IsAuthedOrGuest
from corki.models.user import UserMessage
from corki.util import resp_util


class Message(APIView):
    permission_classes = [IsAuthedOrGuest]

    def get(self, request):
        """
        获取消息列表
        """
        message_list = UserMessage.objects.filter(user_id=request.user.id, guest_code=request.user.guest_code).values('message').order_by('-id')[:30]
        message_list = list(message_list)
        return resp_util.success(message_list)

    def post(self, request):
        body = json.loads(request.body)
        """添加消息保存"""
        UserMessage.objects.create(
            user_id=request.user.id,
            guest_code=request.user.guest_code,
            message=body.get('message', ''),
        )
        return resp_util.success('ok')
