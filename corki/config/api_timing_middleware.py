import time
from django.http import HttpRequest, HttpResponse
from loguru import logger


class APITimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        user_id = request.user.id
        start_time = time.time()
        response: HttpResponse = self.get_response(request)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"用户ID:{user_id}, 接口:{request.path} 耗时: {elapsed_time:.4f} 秒")
        return response
