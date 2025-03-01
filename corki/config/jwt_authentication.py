import jwt
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication

from corki.models.user import CUser

class CrokiJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None
        token = self.get_raw_token(header)
        if token is None:
            return None
        token = token.decode('utf-8')
        # payload = jwt.decode(
        #     token,
        #     settings.SECRET_KEY,
        #     algorithms=[settings.SIMPLE_JWT.get('ALGORITHM', 'HS256')],
        #     options={"verify_signature": False}  # 只解码不验证签名
        # )

        cached_data = cache.get(token)

        if cached_data:
            user = CUser(**cached_data)
            request.user = user
            return user, token
        else:
            raise AuthenticationFailed()

    def authenticate_header(self, request):
        return 'Bearer'
