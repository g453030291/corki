import json

from loguru import logger
from rest_framework.views import APIView
from sympy import false

from corki.client import doubao_client
from corki.models.interview import InterviewQuestion, InterviewRecord
from corki.models.user import UserCV, UserJD, CUser
from corki.service import conversation_service
from corki.util import resp_util


class ConversationInit(APIView):

    def post(self, request):
        # 判断可用时长
        cuser =  CUser.objects.get(id=request.user.id)
        if cuser.available_seconds <= 0:
            return resp_util.error(500, '时长耗尽,请充值!')

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

    def post(self, request):
        logger.info('conversation_feedback start')
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        InterviewRecord.objects.filter(user_id=request.user.id, id=interview_id).update(deleted=0)
        conversation_service.scoring_and_suggestion(interview_id)
        logger.info('conversation_feedback stop')
        return resp_util.success(interview_id)
