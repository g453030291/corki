import base64
import gzip
import json
import os
import uuid

import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from loguru import logger

from corki.service import conversation_service
from corki.util import volcengine_util


class ConversationStreamWsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_prompts = None
        self.token = os.getenv('V_ACCESS_TOKEN')
        # 语音识别
        self.sauc_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.sauc_ws_client = None
        self.sauc_req_id = None
        self.sauc_seq = 1
        self.sauc_log_id = None
        # 语音合成
        self.tts_url = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
        self.tts_ws_client = None

    """
    语音会话 ws 接口
    """
    async def connect(self):
        client_ip = self.scope['client'][0]
        path = self.scope['path']
        logger.info(f"Incoming connection from {client_ip} on path {path}")
        await self.accept()
        logger.info(f"New connection established - Channel Name: {self.channel_name}")
        # 1. 建立连接
        http_headers, self.sauc_req_id = volcengine_util.sauc1_http_header()
        self.sauc_ws_client = await websockets.connect(self.sauc_url, additional_headers=http_headers, max_size=1000000000)
        self.tts_ws_client = await websockets.connect(self.tts_url, additional_headers={"Authorization": f"Bearer; {self.token}"}, ping_interval=None)
        # 2. 准备 init 数据
        init_param = volcengine_util.sauc2_full_client_request_param(uuid.uuid4().hex)
        payload_bytes = str.encode(json.dumps(init_param))
        payload_bytes = gzip.compress(payload_bytes)
        initial_request = bytearray(volcengine_util.sauc_ws_header(message_type_specific_flags=0b0001))
        initial_request.extend(volcengine_util.sauc_ws_before_payload(self.sauc_seq))
        initial_request.extend(len(payload_bytes).to_bytes(4, 'big'))
        initial_request.extend(payload_bytes)
        # 3. 发送 init 数据
        await self.sauc_ws_client.send(initial_request)

        # 接收初始响应
        response = await self.sauc_ws_client.recv()
        result = volcengine_util.sauc_parse_response(response)
        logger.info(f"Initial response: {result}")
        self.sauc_log_id = result['payload_msg']['result']['additions']['log_id']
        print(json.dumps(result, indent=4))
        await self.send(text_data=json.dumps({
            'code': 0,
            'msg': 'Welcome to the conversation interface!',
            'data': {
                'channel_name': self.channel_name,
                'sauc_log_id': self.sauc_log_id
            }
        }))

    async def disconnect(self, close_code):
        await self.sauc_ws_client.close()
        await self.tts_ws_client.close()
        logger.info(f"Disconnected - Channel Name: {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Receive message from channel {self.channel_name}: text_data: {text_data} bytes_data length: {0 if bytes_data is None else len(bytes_data)}")
        # await self.send(text_data=text_data)
        if text_data:
            logger.info(f"Receive text data: {text_data}")
            text_json_data = json.loads(text_data)
            self.system_prompts = text_json_data['systemPrompts']
        if bytes_data:
            self.sauc_seq += 1
            payload_bytes = gzip.compress(bytes_data)
            audio_request = bytearray(volcengine_util.sauc_ws_header(
                message_type=0b0010,  # AUDIO_ONLY_REQUEST
                message_type_specific_flags=0b0001
            ))
            audio_request.extend(volcengine_util.sauc_ws_before_payload(sequence=self.sauc_seq))
            audio_request.extend(len(payload_bytes).to_bytes(4, 'big'))
            audio_request.extend(payload_bytes)
            await self.sauc_ws_client.send(audio_request)

            # 接收识别结果
            response = await self.sauc_ws_client.recv()

            # 解析响应
            result = volcengine_util.sauc_parse_response(response)
            logger.info(json.dumps(result, indent=4, ensure_ascii=False))

            # 断句识别
            if 'utterances' in result['payload_msg']['result']:
                definite = result['payload_msg']['result']['utterances'][0]['definite']
                # print(f"Definite: {definite}")
                if definite:
                    definite_text = result['payload_msg']['result']['utterances'][0]['text']
                    await self.send(text_data=json.dumps({
                        'code': 0,
                        'msg': 'success',
                        'data': f'豆包分句: {definite_text}'
                    }, ensure_ascii=False))
                    # 请求大模型接口
                    # 使用异步任务处理大模型请求和语音合成请求
                    asyncio.create_task(self.process_llm_and_tts(definite_text))

            if 'payload_msg' in result and 'text' in result['payload_msg']['result']:
                await self.send(text_data=json.dumps({
                    'code': 0,
                    'msg': 'success',
                    'data': result['payload_msg']['result']['text']
                }, ensure_ascii=False))
            else:
                print(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")

    async def process_llm_and_tts(self, definite_text):
        llm_resp = conversation_service.completions_by_key(self.channel_name, self.system_prompts, definite_text)
        await self.send(text_data=json.dumps({
            'code': 0,
            'msg': 'success',
            'data': llm_resp
        }, ensure_ascii=False))
        # 请求语音合成接口
        full_submit_request = volcengine_util.tts_full_client_request(self.channel_name, llm_resp, 'submit')
        await self.tts_ws_client.send(full_submit_request)
        while True:
            res = await self.tts_ws_client.recv()
            # print(res)
            chunk_data, is_done, is_error = volcengine_util.tts_parse_response(res)
            if is_done:
                logger.info("TTS Request done.")
                break
        full_query_request = volcengine_util.tts_full_client_request(self.channel_name, llm_resp, 'query')
        await self.tts_ws_client.send(full_query_request)
        while True:
            res = await self.tts_ws_client.recv()
            chunk_data, is_done, is_error = volcengine_util.tts_parse_response(res)
            if chunk_data:
                b64_audio = base64.b64encode(chunk_data).decode('utf-8')
                await self.send(text_data=json.dumps({
                    'code': 0,
                    'msg': 'success',
                    'data': {'data_type': 'audio-chunk', 'base64': b64_audio}
                }))
            if is_done:
                logger.info("TTS Query done.")
                break
