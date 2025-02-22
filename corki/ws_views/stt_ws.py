# consumers.py
import json
import asyncio
import base64
import gzip
import os
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
import websockets

from corki.test import simplex_websocket_demo


class STTStreamWsConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.external_ws = None
        self.seq = 1
        self.reqid = None

    def generate_header(self, message_type=0b0001, message_type_specific_flags=0b0001,
                        serial_method=0b0001, compression_type=0b0001, reserved_data=0x00):
        header = bytearray()
        header_size = 1
        header.append((0b0001 << 4) | header_size)  # protocol_version and header_size
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        return header

    def generate_before_payload(self, sequence: int):
        before_payload = bytearray()
        before_payload.extend(sequence.to_bytes(4, 'big', signed=True))
        return before_payload

    async def connect(self):
        await self.accept()
        self.reqid = str(uuid.uuid4())

        # 构建初始请求
        request_params = {
            "user": {
                "uid": "test",
            },
            "audio": {
                'format': "pcm",
                "sample_rate": 16000,
                "bits": 16,
                "channel": 1,
                "codec": "raw",
            },
            "request": {
                "model_name": "bigmodel",
                "enable_punc": True,
            }
        }

        try:
            # 连接外部语音识别服务
            headers = {
                "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
                "X-Api-Access-Key": os.getenv('V_ACCESS_TOKEN'),
                "X-Api-App-Key": os.getenv('V_APP_ID'),
                "X-Api-Request-Id": self.reqid
            }

            self.external_ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                max_size=1000000000
            )

            # 发送初始请求
            payload_bytes = str.encode(json.dumps(request_params))
            payload_bytes = gzip.compress(payload_bytes)

            initial_request = bytearray(self.generate_header(message_type_specific_flags=0b0001))
            initial_request.extend(self.generate_before_payload(sequence=self.seq))
            initial_request.extend(len(payload_bytes).to_bytes(4, 'big'))
            initial_request.extend(payload_bytes)

            await self.external_ws.send(initial_request)

            # 接收初始响应
            response = await self.external_ws.recv()
            # 处理响应...

        except Exception as e:
            print(f"Connection error: {e}")
            await self.close()

    async def disconnect(self, close_code):
        if self.external_ws:
            await self.external_ws.close()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                # 处理控制命令
                data = json.loads(text_data)
                if data.get('command') == 'stop':
                    self.seq = -abs(self.seq)  # 使序号变为负数表示结束

            elif bytes_data:
                # 处理音频数据
                self.seq += 1

                # 压缩音频数据
                payload_bytes = gzip.compress(bytes_data)

                # 构建音频请求
                audio_request = bytearray(self.generate_header(
                    message_type=0b0010,  # AUDIO_ONLY_REQUEST
                    message_type_specific_flags=0b0001 if self.seq > 0 else 0b0011
                ))
                audio_request.extend(self.generate_before_payload(sequence=self.seq))
                audio_request.extend(len(payload_bytes).to_bytes(4, 'big'))
                audio_request.extend(payload_bytes)

                # 发送到语音识别服务
                await self.external_ws.send(audio_request)

                # 接收识别结果
                response = await self.external_ws.recv()

                # 解析响应
                result = self.parse_response(response)

                # 发送结果给前端
                if 'payload_msg' in result and 'text' in result['payload_msg']['result']:
                    await self.send(text_data=json.dumps({
                        'type': 'transcription',
                        'text': result['payload_msg']['result']['text']
                    }))
                else:
                    print(f"Error parsing response: {json.dumps(result, indent=2, ensure_ascii=False)}")

        except Exception as e:
            print(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    def parse_response(self, res):
        return simplex_websocket_demo.parse_response(res)
