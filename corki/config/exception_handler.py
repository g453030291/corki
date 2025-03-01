from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated
from rest_framework import status

from corki.util import resp_util

def auth_exception_handler(exc, context):
    # 调用 DRF 的默认异常处理器，获取默认的响应
    response = exception_handler(exc, context)

    if isinstance(exc, NotAuthenticated):
        return resp_util.error(401,
                               'Authentication credentials were not provided.',
                               as_string=False,
                               error_status=status.HTTP_401_UNAUTHORIZED)

    return response
