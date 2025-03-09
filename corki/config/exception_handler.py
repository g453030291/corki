from rest_framework.views import exception_handler
from rest_framework.exceptions import NotAuthenticated, AuthenticationFailed
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
    if isinstance(exc, AuthenticationFailed):
        return resp_util.error(401,
                               'Authentication failed.',
                               as_string=False,
                               error_status=status.HTTP_401_UNAUTHORIZED)
    if response is not None and response.status_code == status.HTTP_403_FORBIDDEN:
        return resp_util.error(403,
                               'You do not have permission to perform this action.',
                               as_string=False,
                               error_status=status.HTTP_403_FORBIDDEN)
    return response
