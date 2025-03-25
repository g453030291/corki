import gzip
import json
import time
import traceback
import uuid

import asyncio
import websockets
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from loguru import logger

from corki.models.user import CUser
from corki.service import ws_con_service
from corki.util import volcengine_util, resp_util, timing_util
from corki.util.distributed_lock import DistributedLock


class ConversationStreamWsConsumer3(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.available_seconds = 0
        self.start_timestamp = 0
        self.answer_content = ''
        self.answer_stop_flag = 0
        self.answer_stop_key = ''
        # 语音识别
        self.sauc_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.sauc_ws_client = None
        self.sauc_ws_client_is_connected = False
        self.sauc_req_id = None
        self.sauc_seq = 1
        self.sauc_log_id = None

    async def connect(self):
        logger.info("WebSocket connection established")
        await self.pre_check()
        # 初始化连接要取到 interview id
        logger.info(f"Incoming connection from {self.scope['client'][0]} on path {self.scope['path']}")
        await self.accept()
        logger.info(f"New connection established - Channel Name: {self.channel_name}")
        await self.sauc_init()
        await self.send(text_data=resp_util.success({'available_seconds': self.available_seconds, 'start_timestamp': self.start_timestamp}, True))

    async def disconnect(self, close_code):
        await self.sauc_ws_client.close()
        self.sauc_ws_client_is_connected = False
        logger.info(f"sauc ws connection closed.sauc_log_id:{self.sauc_log_id}")
        logger.info(f"Connection closed - Channel Name: {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Receive message from channel {self.channel_name}: text_data: {text_data} bytes_data length: {0 if bytes_data is None else len(bytes_data)}")
        if bytes_data:
            await self.process_voice_bytes(bytes_data)
        if text_data:
            text_data = json.loads(text_data)
            if text_data.get('operation_type') == 'start':
                interview_id = text_data.get('interview_id')
                self.answer_stop_key = interview_id + '_answer_stop'
                pass
            elif text_data.get('operation_type') == 'stop':
                pass
            else:
                await self.send(resp_util.error(99, 'Unknown operation type', True))

    async def process_voice_bytes(self, bytes_data):
        """
        处理语音数据
        :param bytes_data:
        :return:
        """
        # ------------------------- 豆包语音识别 ------------------------- #
        self.sauc_seq += 1
        audio_request = volcengine_util.pack_request_data(bytes_data, self.sauc_seq)
        if self.sauc_ws_client_is_connected is False:
            logger.info(f"WebSocket connection is not established.")
            return
        await self.sauc_ws_client.send(audio_request)
        # 接收识别结果
        response = await self.sauc_ws_client.recv()
        # 解析响应
        result = volcengine_util.sauc_parse_response(response)
        # logger.info(json.dumps(result, indent=4, ensure_ascii=False))
        # ------------------------- 豆包语音识别 ------------------------- #
        # ------------------------- 业务逻辑 ------------------------- #
        sauc_text = result['payload_msg']['result']['text']
        logger.info(f'doubao_sauc_text:{sauc_text}')
        # 断句识别
        if 'utterances' in result['payload_msg']['result']:
            definite = result['payload_msg']['result']['utterances'][0]['definite']
            if definite:
                definite_text = result['payload_msg']['result']['utterances'][0]['text']
                logger.info(f"豆包分句: {definite_text}")
                self.answer_content += definite_text
        if 'payload_msg' in result and 'text' in result['payload_msg']['result']:
            content_text = result['payload_msg']['result']['text']
            logger.info(f"豆包识别结果: {content_text}")
            if self.answer_content and len(content_text) == 0:
                self.answer_stop_flag += 1
            if self.answer_stop_flag >= 3:
                asyncio.create_task(self.get_next_step())
                await self.send(text_data=resp_util.voice_success({'available_seconds': timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)}))
        else:
            logger.info(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        # ------------------------- 业务逻辑 ------------------------- #

    async def get_next_step(self):
        lock = DistributedLock(self.answer_stop_key, timeout=60)
        try:
            if lock.acquire(blocking=False, retry_interval=0, retry_times=0):
                await asyncio.sleep(10)
                logger.info('睡了 10 秒,执行耗时操作')
            else:
                return
        except Exception as e:
            logger.error(f"get_next_step error: {traceback.format_exc()}")
            return
        finally:
            lock.release()

    # 初始建立连接的前置校验
    async def pre_check(self):
        self.start_timestamp = int(time.time())
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        all_conn_flag, self.available_seconds = await ws_con_service.permission_check(query_string)
        if not all_conn_flag:
            logger.info("WebSocket connection refused due to permission check failure")
            await self.close()

    async def sauc_init(self):
        # 1. 建立连接
        http_headers, self.sauc_req_id = volcengine_util.sauc1_http_header()
        self.sauc_ws_client = await websockets.connect(self.sauc_url, additional_headers=http_headers,
                                                       max_size=1000000000)
        self.sauc_ws_client_is_connected = True
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
        logger.info(f'sauc_init_resp:{json.dumps(result, indent=4)}')
