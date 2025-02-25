import json
import os
import uuid

from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.files.storage import default_storage

from corki.client.oss_client import OSSClient
from corki.models.user import CUser
from corki.service import conversation_service
from corki.util import response_util
from corki.ws_views import stt_api


def get_user(request):
    return response_util.success(list(CUser.objects.all().values_list()))

def home_page(request):
    return render(request, 'home.html')

def home2_page(request):
    return render(request, 'home2.html')

def home3_page(request):
    return render(request, 'home3.html')

def conversation_page(request):
    return render(request, 'conversation.html')


@csrf_exempt
@require_POST
def stt_test(request):
    """
    A simple HTTP interface:
    1. Receives an audio file in POST.
    2. Saves the file to disk.
    3. Calls the ASR client to connect via WebSocket and process audio.
    4. Streams the results back to the client in JSON fragments.
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return JsonResponse({"error": "No audio file provided."}, status=400)

    # Save the uploaded file temporarily
    file_extension = os.path.splitext(audio_file.name)[1]
    temp_name = default_storage.save(f"temp_upload_{uuid.uuid4()}{file_extension}", audio_file)
    temp_path = os.path.join(settings.MEDIA_ROOT, temp_name)

    # Prepare the streaming response
    async def stream_results():
        """
        Consumes the async generator from execute_one() and yields partial JSON lines.
        """
        audio_item = {
            'id': str(uuid.uuid4()),
            'path': temp_path
        }
        try:
            # Create generator for chunked responses
            generator = await stt_api.execute_one(
                audio_item,
                format=file_extension.lstrip('.'),  # e.g., "wav", "mp3", "pcm"
                streaming=True,
                seg_duration=100
            )
            async for partial_result in generator:
                # Each chunk will be serialized to JSON and followed by a newline
                yield json.dumps(partial_result, ensure_ascii=False) + "\n"
        finally:
            # Clean up the temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Return a StreamingHttpResponse to allow partial data to be sent back
    # Note: For streaming async responses, Django Channels or ASGI is typically used.
    # For simplicity, we illustrate an approach here that might require an ASGI setup.
    # If your Django project is purely WSGI, you'd adapt to a synchronous approach.
    response = StreamingHttpResponse(stream_results(), content_type="application/json")
    return response

@csrf_exempt
@require_POST
def conversation_init(request):
    data = json.loads(request.body)
    cv = data.get('cv', '') or conversation_service.test_cv
    jd = data.get('jd', '') or conversation_service.test_jd
    """
    初始化问题和语音
    :param request:
    :return:
    """
    return response_util.success(conversation_service.conversation_init(cv, jd))

@csrf_exempt
def health_liveness(request):
    return response_util.success("OK")

@csrf_exempt
def health_readiness(request):
    try:
        # 尝试连接数据库
        for conn in connections.all():
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return response_util.error("Database connection failed", 500)
    return response_util.success("OK")


@csrf_exempt
def upload_file(request):
    """
    上传文件
    :param request:
    :return:
    """
    oss_client = OSSClient()
    file = request.FILES.get('file')
    if file:
        file_name = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"
        url = oss_client.put_object(file_name, file.read())
        return response_util.success({'url': url})
    return None
