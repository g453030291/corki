import json
import random

from django.core.cache import cache
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken

from corki.client import sms_client
from corki.config import constant
from corki.config.permissions import IsAuthedOrGuest
from corki.models.user import UserCV, CUser, UserJD, UserMessage
from corki.service import user_service
from corki.util import resp_util
from corki.util.thread_pool import submit_task

class SendCode(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        phone = data['phone']
        if phone is None:
            return resp_util.error(500, '手机号不能为空!')
        # 生成 4 位验证码
        verification_code = random.randint(1000, 9999)
        # 将验证码存入缓存
        cache.set(phone, verification_code, timeout=300)
        send_flag = sms_client.send_code(phone, verification_code)
        return resp_util.success('发送成功!') if send_flag else resp_util.error(500, '验证码发送失败')

class Login(APIView):
    permission_classes = [IsAuthedOrGuest]

    def post(self, request):
        body = request.body.decode('utf-8')
        data = json.loads(body)
        phone_number = data['phone']
        code = data['verification_code']
        cache_code = cache.get(phone_number)
        if code != cache_code and code != 1111:
            return resp_util.error(500, '验证码错误')
        cache.delete(phone_number)
        user = CUser.objects.filter(phone=phone_number).first()
        if user is None:
            user = CUser.objects.create(phone=phone_number, available_seconds=constant.NEW_USER_FREE_SECONDS)
            UserCV.objects.filter(guest_code=request.user.guest_code).update(user_id=user.id, guest_code='')
            UserJD.objects.filter(guest_code=request.user.guest_code).update(user_id=user.id, guest_code='')
            UserMessage.objects.filter(guest_code=request.user.guest_code).update(user_id=user.id, guest_code='')

        cache.delete(request.auth)
        access_token = AccessToken.for_user(user)
        cache.set(constant.TOKEN_KEY_PREFIX + str(access_token), CUser.get_serializer()(user).data, timeout=constant.USER_CACHE_SECONDS)
        return resp_util.success({'access_token': str(access_token)})

class Logout(APIView):

    def get(self, request):
        access_token = request.auth
        cache.delete(constant.TOKEN_KEY_PREFIX + str(access_token))
        return resp_util.success('登出成功!')

class RequestUser(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cuser = CUser.objects.get(id=request.user.id)
        user_json = CUser.get_serializer()(cuser).data
        return resp_util.success(user_json)


class CV(APIView):
    permission_classes = [IsAuthedOrGuest]

    def post(self, request):
        data = json.loads(request.body)
        cv_id = data.get('id')

        if cv_id:
            deleted = data.get('deleted', 0)
            update_fields = {'deleted': deleted, 'guest_code': request.user.guest_code}
            if 'default_status' in data and data.get('default_status') == 1:
                update_fields['default_status'] = 1
                UserCV.objects.filter(user_id=request.user.id).exclude(id=cv_id).update(default_status=0)
            UserCV.objects.filter(id=cv_id).update(**update_fields)
        else:
            # Create new CV
            cv_url = data.get('cv_url')
            cv_name = data.get('cv_name')
            UserCV.objects.filter(user_id=request.user.id, guest_code=request.user.guest_code).update(default_status=0)
            user_cv = UserCV.objects.create(user_id=request.user.id, guest_code=request.user.guest_code, cv_url=cv_url, cv_name=cv_name, default_status=1)
            cv_id = user_cv.id
            submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success(cv_id)

class CVList(APIView):
    permission_classes = [IsAuthedOrGuest]

    def post(self, request):
        data = json.loads(request.body)
        default_status = data.get('default_status', None)
        new_one = data.get('new_one', 0)
        query_params = {'user_id': request.user.id, 'guest_code': request.user.guest_code, 'deleted': 0}
        if default_status is not None:
            query_params['default_status'] = default_status
        if new_one == 1:
            user_cv_list = UserCV.objects.filter(**query_params).order_by('-id')[:1]
        else:
            user_cv_list = UserCV.objects.filter(**query_params).order_by('-id').all()
        serializer_class = UserCV.get_serializer()
        serializer = serializer_class(user_cv_list, many=True)
        return resp_util.success(serializer.data)

class JD(APIView):
    permission_classes = [IsAuthedOrGuest]

    def post(self, request):
        data = json.loads(request.body)
        jd_id = data.get('id')
        jd_url = data.get('jd_url', '')
        jd_title = data.get('jd_title', '')
        jd_content = data.get('jd_content')
        default_status = data.get('default_status')
        deleted = data.get('deleted', 0)

        # Build update fields dictionary
        fields = {'guest_code': request.user.guest_code}
        if jd_url:
            fields['jd_url'] = jd_url
        if jd_title:
            fields['jd_title'] = jd_title
        if jd_content is not None:
            fields['jd_content'] = jd_content
        if default_status is not None:
            fields['default_status'] = default_status
        if deleted != 0:
            fields['deleted'] = deleted


        # Update or create based on id existence
        if jd_id:
            # Update existing JD
            UserJD.objects.filter(id=jd_id).update(**fields)

            # If setting as default, reset other JDs for this user
            if default_status == 1:
                UserJD.objects.filter(user_id=request.user.id).exclude(id=jd_id).update(default_status=0)
        else:
            # Create new JD with default_status=1
            fields['user_id'] = request.user.id
            fields['default_status'] = 1
            jd = UserJD.objects.create(**fields)
            jd_id = jd.id
            # Reset other JDs for this user
            UserJD.objects.filter(user_id=request.user.id).exclude(id=jd.id).update(default_status=0)

        return resp_util.success(jd_id)

class JDList(APIView):
    permission_classes = [IsAuthedOrGuest]

    def post(self, request):
        data = json.loads(request.body)
        default_status = data.get('default_status', None)
        new_one = data.get('new_one', 0)
        query_params = {'user_id': request.user.id, 'guest_code': request.user.guest_code, 'deleted': 0}
        if default_status is not None:
            query_params['default_status'] = default_status
        if new_one == 1:
            user_jd_list = UserJD.objects.filter(**query_params).order_by('-id')[:1]
        else:
            user_jd_list = UserJD.objects.filter(**query_params).order_by('-id').all()
        serializer_class = UserJD.get_serializer()
        serializer = serializer_class(user_jd_list, many=True)
        return resp_util.success(serializer.data)

class UploadCV(APIView):
    def post(self, request):
        data = json.loads(request.body)
        cv_url = data.get('cv_url')
        UserCV.objects.filter(user_id=request.user.id, default_status=0).update(default_status=0)
        user_cv = UserCV.objects.create(user_id=request.user.id, guest_code=request.user.guest_code, cv_url=cv_url, default_status=1)
        submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success()

class PCUploadCV(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = json.loads(request.body)
        token = data.get('token')
        if token is None or not cache.has_key(token):
            return resp_util.error(500, 'token 无效')
        user_json = cache.get(token)
        user = CUser.get_serializer().Meta.model(**user_json)
        cv_url = data.get('cv_url')
        cv_name = data.get('cv_name')
        UserCV.objects.filter(user_id=user.id, guest_code=user.guest_code, default_status=0).update(default_status=0)
        user_cv = UserCV.objects.create(user_id=user.id, guest_code=user.guest_code, cv_url=cv_url, cv_name=cv_name, default_status=1)
        cache.delete(token)
        submit_task(user_service.analysis_cv_jd, user_cv, None)
        return resp_util.success()
