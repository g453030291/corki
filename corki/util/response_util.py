from django.http import JsonResponse


class CommonResponse:
    def __init__(self):
        self.code = 0
        self.msg = ''
        self.data = {}

def success(data=None):
    response = CommonResponse()
    response.msg = 'success'
    response.data = data
    return JsonResponse(response.__dict__)

def error(code, msg):
    response = CommonResponse()
    response.code = code
    response.msg = msg
    return JsonResponse(response.__dict__)
