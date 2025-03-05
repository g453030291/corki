import json

from rest_framework import status
from rest_framework.response import Response

class CommonResponse:
    def __init__(self):
        self.code = 0
        self.msg = ''
        self.data = {}

def success(data=None, as_string=False):
    response = CommonResponse()
    response.msg = 'success'
    response.data = data
    response_data = response.__dict__
    if as_string:
        return json.dumps(response_data)
    return Response(response_data, status=status.HTTP_200_OK)

def voice_success(data=None):
    response = CommonResponse()
    response.msg = 'voice bytes received'
    response.data = data
    response_data = response.__dict__
    return json.dumps(response_data)

def error(code, msg, as_string=False, error_status=status.HTTP_500_INTERNAL_SERVER_ERROR):
    response = CommonResponse()
    response.code = code
    response.msg = msg
    response_data = response.__dict__
    if as_string:
        return json.dumps(response_data)
    return Response(response_data, status=error_status)
