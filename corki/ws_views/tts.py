import json
import os
import uuid
import gzip
import copy
import base64
import django
import asyncio
import websockets

from channels.generic.websocket import AsyncWebsocketConsumer

# 初始化 Django
os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

# 服务器头部数据类型定义（与原逻辑一致）
MESSAGE_TYPES = {11: "audio-only server response",
                 12: "frontend server response",
                 15: "error message from server"}
MESSAGE_TYPE_SPECIFIC_FLAGS = {0: "no sequence number",
                               1: "sequence number > 0",
                               2: "last message from server (seq < 0)",
                               3: "sequence number < 0"}
MESSAGE_SERIALIZATION_METHODS = {0: "no serialization", 1: "JSON", 15: "custom type"}
MESSAGE_COMPRESSIONS = {0: "no compression", 1: "gzip", 15: "custom compression method"}

# TTS 配置示例（原示例基础上可根据需求替换）
appid = os.getenv('V_APP_ID')
token = os.getenv('V_ACCESS_TOKEN')
cluster = "volcano_tts"
voice_type = "zh_female_linjia_mars_bigtts"
host = "openspeech.bytedance.com"
api_url = f"wss://{host}/api/v1/tts/ws_binary"

# 用于拼装数据包的默认头部
default_header = bytearray(b'\x11\x10\x11\x00')

# 基础请求 JSON（不含 text，后续在提交时会写入）
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
        "voice_type": "xxx",
        "encoding": "mp3",
        "speed_ratio": 1.0,
        "volume_ratio": 1.0,
        "pitch_ratio": 1.0
    },
    "request": {
        "reqid": "xxx",
        "text": "",
        "text_type": "plain",
        "operation": "xxx"
    }
}


def parse_response(res):
    """
    解析服务器返回的数据，并返回：
       chunk_data: 对应的音频数据（可能为空）
       is_done: 是否可以结束（True 表示结束）
       is_error: 是否出现错误（True 表示错误消息）
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    payload = res[header_size * 4:]

    # 音频数据
    if message_type == 0xb:  # 0xb -> audio-only server response
        # 如果没有 sequence number，则继续等待
        if message_type_specific_flags == 0:
            return (b'', False, False)
        sequence_number = int.from_bytes(payload[:4], "big", signed=True)
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        audio_chunk = payload[8:]
        # sequence_number < 0，说明这是最后一段音频
        return (audio_chunk, sequence_number < 0, False)

    # 错误信息
    elif message_type == 0xf:  # 0xf -> error message
        return (b'', True, True)

    # 前端服务器返回或其他类型，均不再继续
    else:
        return (b'', True, False)


async def tts_request_async(operation, text):
    """
    封装一个异步函数，根据 operation ('submit' or 'query') 向服务器发送请求，
    并实时解析返回的音频数据。每次收到一段数据后，通过 yield 返回 (chunk_data, is_done, is_error)。
    """
    # 拷贝基础 JSON 并设置对应字段
    tts_request_json = copy.deepcopy(request_json)
    tts_request_json["audio"]["voice_type"] = voice_type
    tts_request_json["request"]["reqid"] = str(uuid.uuid4())
    tts_request_json["request"]["operation"] = operation
    tts_request_json["request"]["text"] = text

    payload_bytes = str.encode(json.dumps(tts_request_json))
    # 如果不想压缩，可以注释掉下面这行
    payload_bytes = gzip.compress(payload_bytes)

    # 组装完整请求
    full_client_request = bytearray(default_header)
    full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
    full_client_request.extend(payload_bytes)

    header = {"Authorization": f"Bearer; {token}"}

    async with websockets.connect(api_url, additional_headers=header, ping_interval=None) as ws:
        # 发送组装后的数据包到 TTS 接口
        await ws.send(full_client_request)
        while True:
            resp = await ws.recv()
            chunk_data, is_done, is_error = parse_response(resp)
            yield (chunk_data, is_done, is_error)
            if is_done:
                break


class TTSAndTestWsConsumer(AsyncWebsocketConsumer):
    """
    接收客户端的 websocket 请求：
      1. 如果数据是 {"msg": "需要语音合成的内容"}，则执行：
         - 提交语音合成（operation='submit'）
         - 自动调用 query（operation='query'）不断获取语音数据分片
         - 不保存文件，直接将音频二进制（base64）发送给前端
      2. 如果不符合 JSON 格式，直接返回错误信息并拒绝处理
    """

    async def connect(self):
        print("WebSocket connected!")
        await self.accept()
        await self.send(text_data=json.dumps({
            'type': 'welcome',
            'message': 'Welcome to the TTS test interface!'
        }))

    async def disconnect(self, close_code):
        print(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        """
        接收客户端消息:
          - 如果包含 "msg" 字段，则进行 TTS 语音合成
          - 其他任何不符合要求的 JSON 请求一律拒绝
        """
        # 尝试解析 JSON
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON data'
            }))
            return

        # 如果 "msg" 不存在，则拒绝
        if "msg" not in data:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'JSON must contain "msg" field'
            }))
            return

        text_to_synthesize = data["msg"]

        # 1. 提交语音合成
        async for chunk_data, is_done, is_error in tts_request_async("submit", text_to_synthesize):
            if is_error:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Error occurred during submit operation'
                }))
                return

        # 2. 自动调用 query，不断获取语音数据
        async for chunk_data, is_done, is_error in tts_request_async("query", text_to_synthesize):
            if is_error:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Error occurred during query operation'
                }))
                return

            # 如果有音频数据，就用 base64 编码后发送，前端可直接使用 <audio> 等播放
            if chunk_data:
                b64_audio = base64.b64encode(chunk_data).decode('utf-8')
                await self.send(text_data=json.dumps({
                    'type': 'audio-chunk',
                    'audio_data': b64_audio
                }))

            if is_done:
                # 发送合成完成通知
                await self.send(text_data=json.dumps({
                    'type': 'tts_complete',
                    'message': 'TTS synthesis complete'
                }))
                break
