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

from django.contrib import admin
from django.urls import path

from corki import views
from corki.ws_views.conversation import ConversationStreamWsConsumer
from corki.ws_views.conversation2 import ConversationStreamWsConsumer2
from corki.ws_views.stt_ws import STTStreamWsConsumer
from corki.ws_views.test import WsConsumer
from corki.ws_views.tts import TTSAndTestWsConsumer
from corki.ws_views.tts_stream import TTSStreamWsConsumer

urlpatterns = [
    path("admin/", admin.site.urls),

    # health
    path("api/health/liveness", views.health_liveness, name="health-liveness"),
    path("api/health/readiness", views.health_readiness, name="health-readiness"),

    # user
    path("api/user/", views.get_user, name="get-user"),

    # home
    path("home", views.home_page, name="home-page"),
    path("home2", views.home2_page, name="home-page2"),
    path("home3", views.home3_page, name="home-page3"),

    # page
    path("conversation", views.conversation_page, name="conversation-page"),

    # stt
    path("api/stt", views.stt_test, name="stt"),

    # release api
    path("api/conversation_init", views.conversation_init, name="conversation-init"),
]

websocket_urlpatterns = [
    # test
    path("test/", WsConsumer.as_asgi()),
    path("test/tts", TTSAndTestWsConsumer.as_asgi()),
    path("test/stt", STTStreamWsConsumer.as_asgi()),
    path("test/tts_stream", TTSStreamWsConsumer.as_asgi()),
    path("conversation", ConversationStreamWsConsumer.as_asgi()),
    path("conversation2", ConversationStreamWsConsumer2.as_asgi()),
]
