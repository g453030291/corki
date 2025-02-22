# views.py
import os
import json
import gzip
import time
import uuid
import wave
import asyncio
import datetime
from io import BytesIO

import aiofiles
import websockets
import django
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.files.storage import default_storage

# Initialize Django (if not already initialized elsewhere)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corki.settings')
django.setup()

# --- Original constants and helper functions ---
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011
NEG_SEQUENCE_1 = 0b0011

NO_SERIALIZATION = 0b0000
JSON = 0b0001

NO_COMPRESSION = 0b0000
GZIP = 0b0001

def generate_header(
        message_type=FULL_CLIENT_REQUEST,
        message_type_specific_flags=NO_SEQUENCE,
        serial_method=JSON,
        compression_type=GZIP,
        reserved_data=0x00
):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits),
    serialization_method(4 bits), message_compression(4 bits),
    reserved(8bits)
    """
    header = bytearray()
    header_size = 1
    header.append((PROTOCOL_VERSION << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header

def generate_before_payload(sequence: int):
    before_payload = bytearray()
    before_payload.extend(sequence.to_bytes(4, 'big', signed=True))  # sequence
    return before_payload

def parse_response(res):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits),
    serialization_method(4 bits), message_compression(4 bits),
    reserved(8 bits)
    header_extensions: size = 8 * 4 * (header_size - 1)
    payload: similar to HTTP request body
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    result = {
        'is_last_package': False,
    }
    payload_msg = None
    payload_size = 0
    if message_type_specific_flags & 0x01:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['payload_sequence'] = seq
        payload = payload[4:]
    if message_type_specific_flags & 0x02:
        result['is_last_package'] = True
    if message_type == FULL_SERVER_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result['payload_msg'] = payload_msg
    result['payload_size'] = payload_size
    return result

def read_wav_info(data: bytes = None) -> (int, int, int, int, bytes):
    with BytesIO(data) as _f:
        wave_fp = wave.open(_f, 'rb')
        nchannels, sampwidth, framerate, nframes = wave_fp.getparams()[:4]
        wave_bytes = wave_fp.readframes(nframes)
    return nchannels, sampwidth, framerate, nframes, wave_bytes

def judge_wav(ori_date):
    if len(ori_date) < 44:
        return False
    if ori_date[0:4] == b"RIFF" and ori_date[8:12] == b"WAVE":
        return True
    return False

class AsrWsClient:
    def __init__(self, audio_path, **kwargs):
        """
        :param audio_path: path to audio file
        """
        self.audio_path = audio_path
        self.success_code = 1000
        self.seg_duration = int(kwargs.get("seg_duration", 100))
        self.ws_url = kwargs.get("ws_url", "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel")
        self.uid = kwargs.get("uid", "test")
        self.format = kwargs.get("format", "wav")
        self.rate = kwargs.get("rate", 16000)
        self.bits = kwargs.get("bits", 16)
        self.channel = kwargs.get("channel", 1)
        self.codec = kwargs.get("codec", "raw")
        self.auth_method = kwargs.get("auth_method", "none")
        self.hot_words = kwargs.get("hot_words", None)
        self.streaming = kwargs.get("streaming", True)
        self.mp3_seg_size = kwargs.get("mp3_seg_size", 1000)
        self.req_event = 1

    def construct_request(self, reqid, data=None):
        req = {
            "user": {
                "uid": self.uid,
            },
            "audio": {
                'format': self.format,
                "sample_rate": self.rate,
                "bits": self.bits,
                "channel": self.channel,
                "codec": self.codec,
            },
            "request": {
                "model_name": "bigmodel",
                "enable_punc": True
            }
        }
        return req

    @staticmethod
    def slice_data(data: bytes, chunk_size: int):
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset: offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset: data_len], True

    async def segment_data_processor(self, wav_data: bytes, segment_size: int):
        reqid = str(uuid.uuid4())
        seq = 1
        request_params = self.construct_request(reqid)
        payload_bytes = str.encode(json.dumps(request_params))
        payload_bytes = gzip.compress(payload_bytes)
        full_client_request = bytearray(generate_header(message_type_specific_flags=POS_SEQUENCE))
        full_client_request.extend(generate_before_payload(sequence=seq))
        full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
        full_client_request.extend(payload_bytes)
        header = {
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Access-Key": os.getenv('V_ACCESS_TOKEN'),
            "X-Api-App-Key": os.getenv('V_APP_ID'),
            "X-Api-Request-Id": reqid
        }
        try:
            async with websockets.connect(self.ws_url, additional_headers=header, max_size=1000000000) as ws:
                await ws.send(full_client_request)
                res = await ws.recv()
                result = parse_response(res)
                # Stream chunk responses
                yield {
                    "type": "init_response",
                    "content": result
                }
                for _, (chunk, last) in enumerate(AsrWsClient.slice_data(wav_data, segment_size), 1):
                    seq += 1
                    if last:
                        seq = -seq
                    start = time.time()
                    payload_bytes = gzip.compress(chunk)
                    if last:
                        flags = NEG_WITH_SEQUENCE
                    else:
                        flags = POS_SEQUENCE
                    audio_only_request = bytearray(
                        generate_header(message_type=AUDIO_ONLY_REQUEST, message_type_specific_flags=flags))
                    audio_only_request.extend(generate_before_payload(sequence=seq))
                    audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))
                    audio_only_request.extend(payload_bytes)
                    await ws.send(audio_only_request)
                    res = await ws.recv()
                    result = parse_response(res)
                    yield {
                        "type": "chunk_response",
                        "content": result
                    }
                    if self.streaming:
                        sleep_time = max(0, (self.seg_duration / 1000.0 - (time.time() - start)))
                        await asyncio.sleep(sleep_time)
        except websockets.exceptions.ConnectionClosedError as e:
            yield {"error": f"WebSocket connection closed with status code: {e.code}, reason: {e.reason}"}
        except websockets.exceptions.WebSocketException as e:
            msg = f"WebSocket connection failed: {e}"
            if hasattr(e, "status_code"):
                msg += f", status_code: {e.status_code}"
            if hasattr(e, "headers"):
                msg += f", headers: {e.headers}"
            yield {"error": msg}
        except Exception as e:
            yield {"error": f"Unexpected error: {e}"}

    async def execute(self):
        async with aiofiles.open(self.audio_path, mode="rb") as _f:
            data = await _f.read()
        audio_data = bytes(data)
        if self.format == "mp3":
            segment_size = self.mp3_seg_size
            return self.segment_data_processor(audio_data, segment_size)
        if self.format == "wav":
            nchannels, sampwidth, framerate, nframes, wav_len = read_wav_info(audio_data)
            size_per_sec = nchannels * sampwidth * framerate
            segment_size = int(size_per_sec * self.seg_duration / 1000)
            return self.segment_data_processor(audio_data, segment_size)
        if self.format == "pcm":
            segment_size = int(self.rate * 2 * self.channel * self.seg_duration / 500)
            return self.segment_data_processor(audio_data, segment_size)
        else:
            raise Exception("Unsupported format")

def execute_one(audio_item, **kwargs):
    audio_id = audio_item['id']
    audio_path = audio_item['path']
    asr_ws_client = AsrWsClient(audio_path=audio_path, **kwargs)
    # Return the async generator to be consumed by the caller
    return asr_ws_client.execute()

# --- Django View to handle POST requests with an audio file ---

