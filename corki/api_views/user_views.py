import json
import random

from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from corki.client.oss_client import OSSClient
from corki.models.user import UserCV, CUser, UserJD
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


class CV(APIView):
    def post(self, request):
        data = json.loads(request.body)
        cv_url = data.get('cv_url')
        user_cv = UserCV.objects.create(user_id=request.user.id, cv_url=cv_url)
        submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success()

    def put(self, request):
        data = json.loads(request.body)
        cv_id = data.get('cv_id')
        default_status = data.get('default_status')
        UserCV.objects.filter(id=cv_id).update(default_status=default_status)
        UserCV.objects.filter(user_id=request.user.id).exclude(id=cv_id).update(default_status=0)
        return resp_util.success()

class CVList(APIView):
    def post(self, request):
        data = json.loads(request.body)
        default_status = data.get('default_status')
        new_one = data.get('new_one')
        query_params = {'user_id': request.user.id, 'deleted': 0}
        if default_status is not None:
            query_params['default_status'] = default_status
        if new_one == 1:
            user_cv_list = UserCV.objects.filter(**query_params).all()
        else:
            user_cv_list = UserCV.objects.filter(**query_params).order_by('-id')[:1]
        serializer_class = UserCV.get_serializer()
        serializer = serializer_class(user_cv_list, many=True)
        return resp_util.success(serializer.data)

class JD(APIView):
    def post(self, request):
        data = json.loads(request.body)
        jd_url = data.get('jd_url')
        user_jd = UserJD.objects.create(user_id=request.user.id, jd_url=jd_url)
        submit_task(user_service.analysis_cv_jd, None, user_jd)
        return resp_util.success()

    def put(self, request):
        data = json.loads(request.body)
        jd_id = data.get('jd_id')
        default_status = data.get('default_status')
        UserJD.objects.filter(id=jd_id).update(default_status=default_status)
        UserJD.objects.filter(user_id=request.user.id).exclude(id=jd_id).update(default_status=0)
        return resp_util.success()

class JDList(APIView):
    def post(self, request):
        data = json.loads(request.body)
        default_status = data.get('default_status')
        new_one = data.get('new_one')
        query_params = {'user_id': request.user.id, 'deleted': 0}
        if default_status is not None:
            query_params['default_status'] = default_status
        if new_one == 1:
            user_jd_list = UserJD.objects.filter(**query_params).all()
        else:
            user_jd_list = UserJD.objects.filter(**query_params).order_by('-id')[:1]
        serializer_class = UserJD.get_serializer()
        serializer = serializer_class(user_jd_list, many=True)
        return resp_util.success(serializer.data)

class PCUploadCV(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        token = data.get('token')
        if token is None or not cache.has_key(token):
            return resp_util.error(500, 'token 无效')
        user_id = cache.get(token)
        cv_url = data.get('cv_url')
        user_cv = UserCV.objects.create(user_id=user_id, cv_url=cv_url)
        cache.delete(token)
        submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success()
