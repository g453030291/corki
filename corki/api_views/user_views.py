import json

from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from corki.models.user import UserCV, CUser
from corki.service import user_service
from corki.util import resp_util
from corki.util.thread_pool import submit_task

class Login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        user = CUser.objects.filter(phone=data['phone']).first()
        if user is None:
            user = CUser.objects.create(phone=data['phone'])
        access_token = AccessToken.for_user(user)
        cache.set(str(access_token), CUser.get_serializer()(user).data, timeout=3600)
        return resp_util.success({'access_token': str(access_token)})

class RequestUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_json = CUser.get_serializer()(request.user).data
        return resp_util.success(user_json)


class CVUpload(APIView):
    def post(self, request):
        data = json.loads(request.body)
        cv_url = data.get('cv_url')
        user_cv = UserCV.objects.create(user_id=1, cv_url=cv_url)
        submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success()

class JDUpload(APIView):
    def post(self, request):
        data = json.loads(request.body)
        jd_url = data.get('jd_url')
        user_jd = UserCV.objects.create(user_id=1, jd_url=jd_url)
        submit_task(user_service.analysis_cv_jd, None, user_jd)
        return resp_util.success()
