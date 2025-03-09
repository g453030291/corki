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
    white_paths = ['/api/login', '/api/health/liveness', '/api/health/readiness']
    def authenticate(self, request):
        request_path = request.path
        header = self.get_header(request)
        if request_path in self.white_paths:
            return None, None
        if header is None and request_path not in self.white_paths:
            raise AuthenticationFailed()
        token = self.get_raw_token(header)
        if token is None:
            raise AuthenticationFailed()
        token = token.decode('utf-8')
        # payload = jwt.decode(
        #     token,
        #     settings.SECRET_KEY,
        #     algorithms=[settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')],
        #     options={"verify_signature": False}  # 只解码不验证签名
        # )

        cached_data = cache.get(token)

        if cached_data:
            cache.set(token, cached_data, timeout=constant.USER_CACHE_SECONDS)
            user = CUser(**cached_data)
            request.user = user
            return user, token
        else:
            raise AuthenticationFailed()

    def authenticate_header(self, request):
        return 'Bearer'
