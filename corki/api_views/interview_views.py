from rest_framework.views import APIView

from corki.config.permissions import IsAuthedOrGuest
from corki.models.interview import InterviewRecord
from corki.util import resp_util


class InterviewList(APIView):
    permission_classes = [IsAuthedOrGuest]

    def get(self, request):
        if not request.user.is_authenticated:
            return resp_util.success()
        interview_list = InterviewRecord.objects.filter(user_id=request.user.id).values('id', 'jd_title', 'average_score', 'time_consuming', 'created_at').order_by('-id').all()
        serializer_class = InterviewRecord.get_serializer(field_names=('id', 'jd_title', 'average_score', 'time_consuming', 'created_at'))
        serializer = serializer_class(interview_list, many=True)
        return resp_util.success(serializer.data)

class InterviewDetail(APIView):

    def get(self, request):
        interview_id = request.query_params.get('interview_id')
        interview = InterviewRecord.objects.get(user_id=request.user.id, id=interview_id)
        serializer_class = InterviewRecord.get_serializer()
        serializer = serializer_class(interview, many=False)
        return resp_util.success(serializer.data)
