from django.http import JsonResponse
from loguru import logger
import traceback


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)

            # Interceptar respuestas de error de método HTTP
            if response.status_code == 405:  # Method Not Allowed
                return JsonResponse({
                    'code': 405,
                    'message': 'Method not allowed',
                    'data': None
                }, status=405)

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