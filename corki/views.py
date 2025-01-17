from corki.models.user import CUser
from corki.util import response_util


def get_user(request):
    return response_util.success(list(CUser.objects.all().values_list()))
