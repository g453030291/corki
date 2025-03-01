import json

from rest_framework.views import APIView

from corki.service import conversation_service
from corki.util import resp_util


class ConversationInit(APIView):

    def post(self, request):
        data = json.loads(request.body)
        cv = data.get('cv', '') or conversation_service.test_cv
        jd = data.get('jd', '') or conversation_service.test_jd
        result = conversation_service.conversation_init(cv, jd)
        return resp_util.success(result)
    