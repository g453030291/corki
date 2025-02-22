import gzip
import json
import os
import uuid

import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from loguru import logger

from corki.client.oss_client import OSSClient
from corki.models.interview import InterviewQuestion, InterviewRecord
from corki.service import conversation_service
from corki.util import volcengine_util, response_util
from corki.util.thread_pool import submit_task


class ConversationStreamWsConsumer2(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = os.getenv('V_ACCESS_TOKEN')
        self.oss_client = OSSClient()
        self.interview_record = None
        self.interview_question = None
        # 语音识别
        self.sauc_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.sauc_ws_client = None
        self.sauc_req_id = None
        self.sauc_seq = 1
        self.sauc_log_id = None


    async def connect(self):
        # 初始化连接要取到 interview id
        logger.info(f"Incoming connection from {self.scope['client'][0]} on path {self.scope['path']}")
        await self.accept()
        logger.info(f"New connection established - Channel Name: {self.channel_name}")
        await self.sauc_init()
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
        logger.info(f"sauc ws connection closed.sauc_log_id:{self.sauc_log_id}")
        logger.info(f"Connection closed - Channel Name: {self.channel_name}")

    async def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Receive message from channel {self.channel_name}: text_data: {text_data} bytes_data length: {0 if bytes_data is None else len(bytes_data)}")
        # 1. 首次连接,初始化 interview record
        if text_data:
            text_data = json.loads(text_data)
            if text_data.get('operation_type') == 'start':
                interview_id = text_data.get('interview_id')
                self.interview_record = InterviewRecord.objects.get(id=interview_id)
                self.interview_question = InterviewQuestion.objects.filter(interview_id=interview_id, parent_id=0, question_status=0).order_by('id').first()
                await self.send(text_data=response_util.success({'question_url': self.interview_question.question_url}))
            else:
                await self.send(response_util.error('99', 'Unknown operation type'))
        if bytes_data:
            await self.process_voice_bytes(bytes_data)


    async def sauc_init(self):
        # 1. 建立连接
        http_headers, self.sauc_req_id = volcengine_util.sauc1_http_header()
        self.sauc_ws_client = await websockets.connect(self.sauc_url, additional_headers=http_headers,
                                                       max_size=1000000000)
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
                logger.info(f"豆包分句: {definite_text}")
                await self.get_next_step(self.interview_record.id, self.interview_question.id, definite_text)
        if 'payload_msg' in result and 'text' in result['payload_msg']['result']:
            logger.info(f"豆包识别结果: {result['payload_msg']['result']['text']}")
            # self.answer_content += result['payload_msg']['result']['text']
            await self.send(text_data=response_util.success('voice bytes received'))
        else:
            logger.info(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")


    # 每轮问答都要经历以下过程
    # 1. 服务端下发问题url
    # 2. 客户端上传语音回答
    # 3. 服务端解析语音，生成追问
    # 4. 重复1-3(主问+追问至多 3 轮)

    # 判断当前对话进度和状态，给出下一步操作
    async def get_next_step(self, interview_id, question_id, answer_content):
        # 1. 保存用户回答
        InterviewQuestion.objects.filter(id=self.interview_question.id).update(answer_content=answer_content, question_status=1)
        # 2. 判断当前问题层级
        if self.interview_question.question_type == 0:
            # 2.1 大模型判断是否追问
            completion_json = conversation_service.follow_up_questions(self.interview_question.question_content, answer_content)
            for question in completion_json['questions']:
                question = InterviewQuestion.objects.create(interview_id=interview_id,
                                                            question_content=question['question'],
                                                            module=question['module'])
                submit_task(conversation_service.process_audio, question, self.oss_client)
        # 3. 查询下个问题(追问/下轮问答)
        new_question = InterviewQuestion.objects.filter(interview_id=interview_id,
                                                        parent_id=question_id,
                                                        question_status=0).order_by('id').first()
        if not new_question:
            new_question = InterviewQuestion.objects.filter(interview_id=interview_id,
                                                            parent_id=0,
                                                            question_status=0).order_by('id').first()
        self.interview_question = new_question
