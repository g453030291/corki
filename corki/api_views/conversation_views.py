import json

from loguru import logger
from rest_framework.views import APIView
from sympy import false

from corki.client import doubao_client
from corki.models.interview import InterviewQuestion, InterviewRecord
from corki.models.user import UserCV, UserJD
from corki.service import conversation_service
from corki.util import resp_util


class ConversationInit(APIView):

    def post(self, request):
        data = json.loads(request.body)

        # Handle CV data
        cv_id = data.get('cv_id', 0)
        if cv_id != 0:
            user_cv = UserCV.objects.get(id=cv_id, user_id=request.user.id)
            cv = user_cv.cv_content
        else:
            cv = data.get('cv', '') or conversation_service.test_cv

        # Handle JD data
        jd_id = data.get('jd_id', 0)
        jd_title = None
        if jd_id != 0:
            user_jd = UserJD.objects.get(id=jd_id, user_id=request.user.id)
            jd_title = user_jd.jd_title
            jd = user_jd.jd_title + '\n' + user_jd.jd_content
        else:
            jd = data.get('jd', '') or conversation_service.test_jd

        result = conversation_service.conversation_init(cv, jd, cv_id, jd_id, jd_title, request.user)
        return resp_util.success(result)

class ConversationScoring(APIView):
    def get(self, request):
        interview_id = request.query_params.get('interview_id')
        interview = InterviewRecord.objects.get(id=interview_id)
        serializer_class = InterviewRecord.get_serializer()
        serializer = serializer_class(interview, many=False)
        return resp_util.success(serializer.data)

    def post(self, request):
        logger.info('conversation_feedback start')
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        conversation_service.scoring_and_suggestion(interview_id)
        logger.info('conversation_feedback stop')
        return resp_util.success()