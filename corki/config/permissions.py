from loguru import logger
from rest_framework.permissions import BasePermission

class IsAuthedOrGuest(BasePermission):
    """
    允许已认证用户或携带有效临时token的用户访问
    """
    def has_permission(self, request, view):
        # 已登录用户
        if request.user and request.user.is_authenticated:
            logger.info(f"登录用户,id=: {request.user.id}")
            return True
        logger.info(f"匿名用户,guest_code: {request.user.guest_code}")
        # 临时用户（有 guest_code 但 is_authenticated 为 False）
        return (request.user and
                hasattr(request.user, 'guest_code') and
                request.user.guest_code and
                not request.user.is_authenticated)
