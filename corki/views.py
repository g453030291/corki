from corki.util import response_util


def get_user(request):
    return response_util.success(data={"name": "corki"})