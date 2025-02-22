import json

from channels.generic.websocket import AsyncWebsocketConsumer


class WsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        处理 WebSocket 连接建立
        """
        print("WebSocket connected!")
        await self.accept()

        # 发送欢迎消息
        await self.send(text_data=json.dumps({
            'type': 'welcome',
            'message': 'Welcome to the WebSocket test interface!'
        }))

    async def disconnect(self, close_code):
        """
        处理 WebSocket 连接断开
        """
        print(f"WebSocket disconnected with code: {close_code}")

    async def receive(self, text_data):
        """
        处理收到的 WebSocket 消息
        """
        try:
            # 尝试解析接收到的JSON数据
            data = json.loads(text_data)

            # 回显收到的消息
            response = {
                'type': 'echo',
                'message': f'Received your message: {data.get("message", "no message")}',
                'original_data': data
            }

            await self.send(text_data=json.dumps(response))

        except json.JSONDecodeError:
            # 如果收到的不是有效的JSON数据，返回错误消息
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Please send valid JSON data'
            }))
