import gzip
import json
import os
import time
import uuid
from concurrent.futures import wait

import websockets
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from loguru import logger
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from sympy import false

from corki.client.oss_client import OSSClient
from corki.models.interview import InterviewQuestion, InterviewRecord
from corki.models.user import CUser
from corki.service import conversation_service
from corki.util import volcengine_util, resp_util, timing_util
from corki.util.thread_pool import submit_task


class ConversationStreamWsConsumer2(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = os.getenv('V_ACCESS_TOKEN')
        self.oss_client = OSSClient()
        self.interview_record = None
        self.interview_question = None
        self.user = None
        self.answer_content = ''
        self.answer_stop_flag = 0
        self.available_seconds = 0
        self.start_timestamp = 0
        # 语音识别
        self.sauc_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.sauc_ws_client = None
        self.sauc_ws_client_is_connected = False
        self.sauc_req_id = None
        self.sauc_seq = 1
        self.sauc_log_id = None


    async def connect(self):
        # 权限校验
        await self.permission_check()
        # 初始化连接要取到 interview id
        logger.info(f"Incoming connection from {self.scope['client'][0]} on path {self.scope['path']}")
        await self.accept()
        logger.info(f"New connection established - Channel Name: {self.channel_name}")
        await self.sauc_init()
        # await self.send(text_data=resp_util.success({'channel_name': self.channel_name, 'sauc_log_id': self.sauc_log_id}, True))
        await self.send(text_data=resp_util.success({'available_seconds': self.available_seconds, 'start_timestamp': self.start_timestamp}, True))

    async def disconnect(self, close_code):
        await self.sauc_ws_client.close()
        self.sauc_ws_client_is_connected = False
        logger.info(f"sauc ws connection closed.sauc_log_id:{self.sauc_log_id}")
        logger.info(f"Connection closed - Channel Name: {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Receive message from channel {self.channel_name}: text_data: {text_data} bytes_data length: {0 if bytes_data is None else len(bytes_data)}")
        # 1. 首次连接,初始化 interview record
        if text_data:
            text_data = json.loads(text_data)
            if text_data.get('operation_type') == 'start':
                interview_id = text_data.get('interview_id')
                self.interview_record = await database_sync_to_async(InterviewRecord.objects.get)(id=interview_id)
                self.interview_question = await database_sync_to_async(
                    lambda: InterviewQuestion.objects.filter(
                        interview_id=interview_id,
                        parent_question_id=0,
                        question_status=0
                    ).order_by('id').first()
                )()
                await self.send(text_data=resp_util.success({'question_url': self.interview_question.question_url}, True))
            elif text_data.get('operation_type') == 'stop':
                over_time = timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)
                await database_sync_to_async(CUser.objects.filter(id=self.user.id).update)(available_seconds=over_time)
                await self.send(text_data=resp_util.error(500, '已挂断!', True))
                await self.close(code=4001, reason='收到用户挂断请求!')
                await self.sauc_ws_client.close()
                self.sauc_ws_client_is_connected = False
                return
            else:
                await self.send(resp_util.error(99, 'Unknown operation type', True))
        if bytes_data:
            await self.process_voice_bytes(bytes_data)

    async def permission_check(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        query_params = dict(param.split('=') for param in query_string.split('&') if param)

        # 获取 token
        token = query_params.get("token")
        if not token:
            # 如果没有提供 token，拒绝连接
            await self.close(code=4001)
            return
        cached_data = cache.get(token)
        user = CUser(**cached_data)
        self.user = user
        user_available_seconds = await database_sync_to_async(
            CUser.objects.filter(id=user.id).values('available_seconds').first)()
        self.available_seconds = user_available_seconds['available_seconds']
        if self.available_seconds <= 0:
            # 如果用户的可用时间小于等于0，拒绝连接
            logger.info(f"ws conversation:User {user.id} has no available seconds.")
            await self.close(code=4001)
            return
        self.start_timestamp = int(time.time())

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

    async def process_voice_bytes(self, bytes_data):
        """
        处理语音数据
        :param bytes_data:
        :return:
        """
        self.sauc_seq += 1
        payload_bytes = gzip.compress(bytes_data)
        audio_request = bytearray(volcengine_util.sauc_ws_header(
            message_type=0b0010,  # AUDIO_ONLY_REQUEST
            message_type_specific_flags=0b0001
        ))
        audio_request.extend(volcengine_util.sauc_ws_before_payload(sequence=self.sauc_seq))
        audio_request.extend(len(payload_bytes).to_bytes(4, 'big'))
        audio_request.extend(payload_bytes)

        if self.sauc_ws_client_is_connected is False:
            logger.info(f"WebSocket connection is not established.")
            return
        await self.sauc_ws_client.send(audio_request)

        # 接收识别结果
        response = await self.sauc_ws_client.recv()

        # 解析响应
        result = volcengine_util.sauc_parse_response(response)
        # logger.info(json.dumps(result, indent=4, ensure_ascii=False))
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
                stop_flag, stop_reason = await self.get_next_step(self.interview_record.id, self.interview_question.id, self.answer_content)
                if stop_flag:
                    logger.info(f"stop_flag:{stop_flag},连接关闭")
                    over_time = timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)
                    await database_sync_to_async(CUser.objects.filter(id=self.user.id).update)(available_seconds=over_time)
                    await self.send(text_data=resp_util.error(500, stop_reason, True))
                    await self.close(code=4001, reason='The available time is insufficient, please recharge')
                    await self.sauc_ws_client.close()
                    self.sauc_ws_client_is_connected = False
                    return
                await self.send(
                    text_data=resp_util.success({'question_url': self.interview_question.question_url}, True))
            else:
                await self.send(text_data=resp_util.voice_success({'available_seconds': timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)}))
        else:
            logger.info(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")


    # 每轮问答都要经历以下过程
    # 1. 服务端下发问题url
    # 2. 客户端上传语音回答
    # 3. 服务端解析语音，生成追问
    # 4. 重复1-3(主问+追问至多 3 轮)

    # 判断当前对话进度和状态，给出下一步操作
    async def get_next_step(self, interview_id, question_id, answer_content):
        stop_flag, stop_reason = False, None
        # 1. 保存用户回答
        update_operation = database_sync_to_async(
            InterviewQuestion.objects.filter(id=self.interview_question.id).update)
        await update_operation(answer_content=answer_content, question_status=1)

        # 保存后先判断是否到时
        over_time = timing_util.calculate_remaining_time(self.available_seconds, self.start_timestamp)
        if over_time <= 0:
            stop_flag, stop_reason = True, '时长耗尽,请充值!'
            stop_flag = True
            return stop_flag, stop_reason

        new_question = await self.get_next_question()
        # 都没有,就结束
        if new_question is None:
            # 结束面试
            stop_flag, stop_reason = True, '面试结束!'
            stop_flag = True
            return stop_flag, stop_reason

        self.interview_question = new_question
        self.answer_content = ''
        self.answer_stop_flag = 0
        return stop_flag, stop_reason

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
