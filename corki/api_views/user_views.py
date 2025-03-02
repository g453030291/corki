import json
import random

from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from corki.models.user import UserCV, CUser
from corki.service import user_service
from corki.util import resp_util
from corki.util.thread_pool import submit_task

class SendCode(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        phone = data['phone']
        # 生成 4 位验证码
        verification_code = random.randint(1000, 9999)
        # 将验证码存入缓存
        cache.set(phone, verification_code, timeout=300)
        return resp_util.success({'verification_code': verification_code})

class Login(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        phone_number = data['phone']
        code = data['verification_code']
        cache_code = cache.get(phone_number)
        if code != cache_code:
            return resp_util.error(500, '验证码错误')
        cache.delete(phone_number)
        user = CUser.objects.filter(phone=phone_number).first()
        if user is None:
            user = CUser.objects.create(phone=phone_number)
        access_token = AccessToken.for_user(user)
        cache.set(str(access_token), CUser.get_serializer()(user).data, timeout=60 * 60 * 24 * 30)
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
