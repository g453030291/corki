import time

from channels.db import database_sync_to_async
from django.core.cache import cache
from loguru import logger
from sympy import false

from corki.config import constant
from corki.models.user import CUser


async def permission_check(query_string):
    allow_conn_flag, available_seconds = True, 0
    query_params = dict(param.split('=') for param in query_string.split('&') if param)
    # 获取 token
    token = query_params.get("token")

    cached_data = cache.get(constant.TOKEN_KEY_PREFIX + token)
    user = CUser(**cached_data)
    user_available_seconds = await database_sync_to_async(
        CUser.objects.filter(id=user.id).values('available_seconds').first)()
    available_seconds = user_available_seconds['available_seconds']
    if available_seconds <= 0:
        # 如果用户的可用时间小于等于0，拒绝连接
        logger.info(f"ws conversation:User {user.id} has no available seconds.")
        allow_conn_flag = False
    return allow_conn_flag, available_seconds, user.id
