import json

from channels.generic.websocket import AsyncWebsocketConsumer


class TTSStreamWsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("TTSStreamWsConsumer connect")
        await self.send(text_data=json.dumps({
            'message': 'Welcome to the TTS stream interface!'
        }))

    async def disconnect(self, close_code):
        print("TTSStreamWsConsumer disconnect")

    async def receive(self, text_data=None, bytes_data=None):
        print("TTSStreamWsConsumer receive")
        data = json.loads(text_data)
        message = data['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))
