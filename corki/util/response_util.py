import json
from django.http import JsonResponse


class CommonResponse:
    def __init__(self):
        self.code = 0
        self.msg = ''
        self.data = {}


def success(data=None, as_string=False):
    response = CommonResponse()
    response.msg = 'success'
    response.data = data
    if as_string:
        return json.dumps(response.__dict__)
    return JsonResponse(response.__dict__)


def error(code, msg, as_string=False):
    response = CommonResponse()
    response.code = code
    response.msg = msg
    if as_string:
        return json.dumps(response.__dict__)
    return JsonResponse(response.__dict__)