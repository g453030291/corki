"""
URL configuration for corki project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import handler404
from django.contrib import admin
from django.urls import path

from corki import views
from corki.api_views import empty_views
from corki.api_views.conversation_views import ConversationInit
from corki.api_views.file_views import FileViews
from corki.api_views.health_views import LivenessViews, ReadinessViews
from corki.api_views.ocr_views import OCRViews
from corki.api_views.short_url_views import ShortUrlView
from corki.api_views.user_views import CV, JD, Login, RequestUser, SendCode, PCUploadCV, CVList, JDList
from corki.page_views.test_page import Home3
from corki.ws_views.conversation import ConversationStreamWsConsumer
from corki.ws_views.conversation2 import ConversationStreamWsConsumer2
from corki.ws_views.stt_ws import STTStreamWsConsumer
from corki.ws_views.test import WsConsumer
from corki.ws_views.tts import TTSAndTestWsConsumer
from corki.ws_views.tts_stream import TTSStreamWsConsumer

handler404 = empty_views.custom_404

urlpatterns = [
    # path("admin/", admin.site.urls),

    # health
    path("api/health/liveness", LivenessViews.as_view(), name="health-liveness"),
    path("api/health/readiness", ReadinessViews.as_view(), name="health-readiness"),

    # user
    path("api/user/send_code", SendCode.as_view(), name="send-code"),
    path("api/user/login", Login.as_view(), name="user-login"),
    path("api/user/request", RequestUser.as_view(), name="request-user"),
    path("api/user/cv", CV.as_view(), name="cv-upload"),
    path("api/user/cv_list", CVList.as_view(), name="cv-list"),
    path("api/user/pc_upload_cv", PCUploadCV.as_view(), name="pc-upload-cv"),
    path("api/user/jd", JD.as_view(), name="jd-upload"),
    path("api/user/jd_list", JDList.as_view(), name="jd-list"),

    # home
    path("home3", Home3.as_view(), name="home-page3"),

    # stt
    # path("api/stt", views.stt_test, name="stt"),

    # release api
    path("api/conversation_init", ConversationInit.as_view(), name="conversation-init"),

    # file
    path("api/upload", FileViews.as_view(), name="file-upload"),

    # short url
    path("api/short_url", ShortUrlView.as_view(), name="short-url"),

    # ocr
    path("api/ocr", OCRViews.as_view(), name="ocr"),
]

websocket_urlpatterns = [
    # test
    # path("test/", WsConsumer.as_asgi()),
    # path("test/tts", TTSAndTestWsConsumer.as_asgi()),
    # path("test/stt", STTStreamWsConsumer.as_asgi()),
    # path("test/tts_stream", TTSStreamWsConsumer.as_asgi()),
    # path("conversation", ConversationStreamWsConsumer.as_asgi()),
    path("conversation2", ConversationStreamWsConsumer2.as_asgi()),
]
