import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication

from corki.config import constant
from corki.models.user import CUser

class CrokiJWTAuthentication(JWTAuthentication):
    white_paths = ['/api/guest/token', '/api/user/send_code',
                   '/api/health/liveness', '/api/health/readiness',
                   '/home3']
    def authenticate(self, request):
        request_path = request.path
        header = self.get_header(request)
        # 白名单直接放行
        if request_path in self.white_paths:
            return None, None
        # header,token 为空直接报错
        if header is None:
            raise AuthenticationFailed()
        token = self.get_raw_token(header)
        if token is None:
            raise AuthenticationFailed()
        # token 从缓存中查不到也报错
        token = token.decode('utf-8')
        cached_data = cache.get(token)
        if cached_data is None:
            raise AuthenticationFailed()

        cache.set(token, cached_data, timeout=constant.USER_CACHE_SECONDS)
        user = CUser(**cached_data)
        request.user = user
        return user, token

        # payload = jwt.decode(
        #     token,
        #     settings.SECRET_KEY,
        #     algorithms=[settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')],
        #     options={"verify_signature": False}  # 只解码不验证签名
        # )

    def authenticate_header(self, request):
        return 'Bearer'
