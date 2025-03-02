import json

from django.http import HttpResponse

def custom_404(request, exception):
    error_message = {
        'code': 404,
        'msg': 'The requested URL was not found.',
        'data': ''
    }
    response = HttpResponse(json.dumps(error_message), content_type='application/json')
    response.status_code = 404
    return response
