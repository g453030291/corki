from uuid import uuid4

from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from corki.config import constant
from corki.models.user import CUser
from corki.util import resp_util


class GuestTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = CUser(id=0, guest_code=uuid4().hex, phone='', available_seconds=0)
        access_token = AccessToken.for_user(user)
        cache.set(str(access_token), CUser.get_serializer()(user).data, timeout=constant.USER_CACHE_SECONDS)
        return resp_util.success({'access_token': str(access_token)})
