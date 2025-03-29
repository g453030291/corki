from urllib.parse import parse_qs

from django.core.cache import cache
from loguru import logger

from corki.config import constant
from corki.models.user import CUser


class WSAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 只在WebSocket连接时处理认证
        if scope["type"] != "websocket":
            return await self.app(scope, receive, send)

        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_key = params.get("token", [None])[0]

        if token_key and cache.has_key(constant.TOKEN_KEY_PREFIX + token_key):
            logger.info(f"Token {token_key} validating")
            cached_data = cache.get(constant.TOKEN_KEY_PREFIX + token_key)
            user = CUser(**cached_data)
            if user.id == 0:
                logger.error(f"Token {token_key} is invalid")
                # 关闭WebSocket连接
                await send({"type": "websocket.close", "code": 4001})
                return
            # 可以在这里添加更多信息到scope中，比如用户信息
            # scope["token"] = token_key
            # scope["authenticated"] = True
            # 调用下一个中间件或应用
            return await self.app(scope, receive, send)
        else:
            logger.error(f"Token {token_key} is invalid")
            # 关闭WebSocket连接
            await send({"type": "websocket.close", "code": 4001})
            return
