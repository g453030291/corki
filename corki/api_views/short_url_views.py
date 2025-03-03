import os
import random
import string

import django
from django.core.cache import cache

from corki.util import resp_util

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView


class ShortUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        token = ''.join(random.choices(string.ascii_letters, k=8))
        cache.set(token, request.user.id, timeout=60 * 30)
        return resp_util.success({'token': token})

if __name__ == '__main__':
    random_string = ''.join(random.choices(string.ascii_letters, k=8))
    print(random_string)