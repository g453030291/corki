import os
import time

import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

from corki.models.user import CUser


if __name__ == '__main__':
    result = CUser.objects.filter(id=3).values('available_seconds').first()
    print(result)