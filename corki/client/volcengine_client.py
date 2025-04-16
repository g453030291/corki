import base64
import json
import os
import uuid

import django
import requests
from loguru import logger

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

appid = os.getenv('V_APP_ID')
access_token = os.getenv('V_ACCESS_TOKEN')
cluster = "volcano_tts"

voice_type = "BV700_streaming"
host = "openspeech.bytedance.com"
api_url = f"https://{host}/api/v1/tts"

header = {"Authorization": f"Bearer;{access_token}"}


request_json = {
    "app": {
        "appid": appid,
        "token": "access_token",
        "cluster": cluster
    },
    "user": {
        "uid": "388808087185088"
    },
    "audio": {
        "voice_type": voice_type,
        "encoding": "mp3",
        "speed_ratio": 1.0,
        "volume_ratio": 1.0,
        "pitch_ratio": 1.0,
    },
    "request": {
        "reqid": str(uuid.uuid4()),
        "text": "你好，现在面试正式开始！请先做一个自我介绍吧！",
        "text_type": "plain",
        "operation": "query",
        "with_frontend": 1,
        "frontend_type": "unitTson"

    }
}


def tts(text, voice_type="BV700_streaming"):
    request_json["request"]["text"] = text
    request_json["audio"]["voice_type"] = voice_type
    resp = requests.post(api_url, json.dumps(request_json), headers=header)
    # logger.info(f"resp body: \n{resp.text}")
    if "data" in resp.json():
        data = resp.json()["data"]
        return base64.b64decode(data)
    return None


if __name__ == '__main__':
    try:
        resp = requests.post(api_url, json.dumps(request_json), headers=header)
        print(f"resp body: \n{resp.json()}")
        if "data" in resp.json():
            data = resp.json()["data"]
            file_to_save = open("test_submit.mp3", "wb")
            file_to_save.write(base64.b64decode(data))
    except Exception as e:
        e.with_traceback()
