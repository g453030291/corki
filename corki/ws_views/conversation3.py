import gzip
import json
import os
import time
import traceback
import uuid

import asyncio
from concurrent.futures import wait

import websockets
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from django.db import models
from loguru import logger

from corki.client.oss_client import OSSClient
from corki.models.interview import InterviewRecord, InterviewQuestion
from corki.models.user import CUser
from corki.service import ws_con_service, conversation_service
from corki.util import volcengine_util, resp_util, timing_util
from corki.util.distributed_lock import DistributedLock
from corki.util.thread_pool import submit_task


class ConversationStreamWsConsumer3(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = os.getenv('V_ACCESS_TOKEN')
        self.oss_client = OSSClient()
        self.interview_record = None
        self.interview_question = None
        self.user_id = None
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
        await self.clear_and_close_conn('收到前端 disconnect 事件,关闭连接')
        logger.info(f"sauc ws connection closed.sauc_log_id:{self.sauc_log_id}")
        logger.info(f"Connection closed - Channel Name: {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Receive message from channel {self.channel_name}: text_data: {text_data} bytes_data length: {0 if bytes_data is None else len(bytes_data)}")
        if bytes_data:
            await self.process_voice_bytes(bytes_data)
        if text_data:
            text_json = json.loads(text_data)
            await self.process_text(text_json)

    async def process_voice_bytes(self, bytes_data):
        """
        处理语音数据
        :param bytes_data:
        :return:
        """
        # ------------------------- 豆包语音识别start ------------------------- #
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
        # ------------------------- 豆包语音识别end ------------------------- #
        # ------------------------- 业务逻辑start ------------------------- #
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
            if self.answer_stop_flag >= 2:
                lock = DistributedLock(self.answer_stop_key, timeout=60)
                if lock.acquire(blocking=False, retry_interval=0, retry_times=0):
                    asyncio.create_task(self.get_next_step(self.answer_content, lock))
                else:
                    logger.info("获取锁失败,问题在处理中.跳过")
            await self.send(text_data=resp_util.voice_success({'available_seconds': timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)}))
        else:
            logger.info(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        # ------------------------- 业务逻辑end ------------------------- #


    async def get_next_step(self, answer_content, lock):
        # 1. 保存用户回答
        update_operation = database_sync_to_async(
            InterviewQuestion.objects.filter(id=self.interview_question.id).update)
        await update_operation(answer_content=answer_content, question_status=1)

        # 保存后先判断是否到时
        over_time = timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)
        if over_time <= 0:
            await self.clear_and_close_conn('时长耗尽,请充值!')
            return

        new_question = await self.get_next_question()
        # 都没有,就结束面试
        if new_question is None:
            await self.clear_and_close_conn('面试结束!')
            return

        self.interview_question = new_question
        self.answer_content = ''
        self.answer_stop_flag = 0
        await self.send(text_data=resp_util.success({'question_url': self.interview_question.question_url}, True))
        lock.release()

    async def get_next_question(self):
        filter_questions = database_sync_to_async(InterviewQuestion.objects.filter)
        create_questions = database_sync_to_async(InterviewQuestion.objects.create)
        first_question = database_sync_to_async(lambda qs: qs.order_by('id').first())
        last_question = database_sync_to_async(lambda qs: qs.order_by('-id').first())
        # 根据当前的问题状态判断直接返回下一个问题,还是生成追问,再返回下一个问题
        # 先判断主问还是追问
        # 主问判断是否生成过追问 没有就去生成追问,并且查询追问问题返回。查询不到就返回下一轮问题
        # 追问判断是否还有下一个追问 有就返回下一个,没有就返回下一轮问题
        if self.interview_question.question_type == 0:
            if self.interview_question.question_closely_status == 0:
                # 生成追问
                completion_json = conversation_service.follow_up_questions(self.interview_question.question_content,
                                                                           self.answer_content)
                # 修改当前 question的question_closely_status=1
                await database_sync_to_async(InterviewQuestion.objects.filter(id=self.interview_question.id).update)(question_closely_status=1)
                if len(completion_json) > 0:
                    sub_questions = []
                    for question in completion_json['questions']:
                        new_question = await create_questions(interview_id=self.interview_record.id,
                                                             question_content=question['question'],
                                                             module=question['module'],
                                                             question_type=1,
                                                             parent_question_id=self.interview_question.id)
                        sub_questions.append(new_question)
                    futures = [submit_task(conversation_service.process_audio, sub_question, self.oss_client) for sub_question in sub_questions]
                    wait(futures)
        # 查询有没有未回答的追问
        questions = await filter_questions(interview_id=self.interview_record.id,
                                           question_type=1,
                                           question_status=0)
        new_question = await first_question(questions)
        # 没有追问就取下轮问题
        if new_question is None:
            questions = await filter_questions(interview_id=self.interview_record.id,
                                               parent_question_id=0,
                                               question_status=0)
            new_question = await first_question(questions)
        return new_question

    async def process_text(self, text_json):
        """
        处理文本数据(开启连接,结束对话)
        :param text_json:
        :return:
        """
        operation_type = text_json.get('operation_type')
        if operation_type == 'start':
            interview_id = text_json.get('interview_id')
            self.interview_record = await database_sync_to_async(InterviewRecord.objects.get)(id=interview_id)
            self.interview_question = await database_sync_to_async(
                lambda: InterviewQuestion.objects.filter(
                    interview_id=interview_id,
                    parent_question_id=0,
                    question_status=0
                ).order_by('id').first()
            )()
            await self.send(text_data=resp_util.success({'question_url': self.interview_question.question_url}, True))
        elif operation_type == 'stop':
            await self.clear_and_close_conn('收到用户挂断请求,连接关闭!')
        else:
            await self.send(resp_util.error(99, 'Unknown operation type', True))

    # 初始建立连接的前置校验
    async def pre_check(self):
        self.start_timestamp = int(time.time())
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        all_conn_flag, self.available_seconds, self.user_id = await ws_con_service.permission_check(query_string)
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

    async def clear_and_close_conn(self, stop_reason):
        logger.info("触发服务端主动关闭连接")
        # 更新用户剩余时间
        over_time = timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)
        await database_sync_to_async(CUser.objects.filter(id=self.user_id).update)(available_seconds=over_time)
        # 更新面试记录时间
        update_time_consuming = database_sync_to_async(InterviewRecord.objects.filter(id=self.interview_record.id).update)
        timing = timing_util.get_time_difference(self.start_timestamp)
        await update_time_consuming(time_consuming=models.F('time_consuming') + timing)
        # 关闭连接
        await self.send(text_data=resp_util.error(500, stop_reason, True))
        await self.close(code=4001, reason='The available time is insufficient, please recharge')
        await self.sauc_ws_client.close()
        self.sauc_ws_client_is_connected = False
