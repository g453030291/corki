import traceback

from django.http import JsonResponse
from loguru import logger

class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            logger.exception(traceback.format_exc())
            return self.handle_exception(request, e)

    def process_exception(self, request, exception):
        logger.error(traceback.format_exc())
        return self.handle_exception(request, exception)

    def handle_exception(self, request, exception):
        return JsonResponse({
            'code': 500,
            'message': 'System error',
            'data': None
        }, status=500)
