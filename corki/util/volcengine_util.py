"""
火山引擎API 相关工具类
"""
import gzip
import json
import os
from uuid import uuid4

from loguru import logger
from sympy import false

from corki.test.tts_websocket_demo import appid

app_id = os.getenv('V_APP_ID')
access_token = os.getenv('V_ACCESS_TOKEN')

def sauc1_http_header():
    """
    1. 生成asr API请求头
    :return: 请求头, 请求ID
    """
    req_id = uuid4().hex
    headers = {
        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        "X-Api-Access-Key": access_token,
        "X-Api-App-Key": app_id,
        "X-Api-Request-Id": req_id
    }
    return headers, req_id

def sauc2_full_client_request_param(user_id):
    """
    2. 生成建联的请求参数
    :param user_id:
    :return:
    """
    param = {
        "user": {
            "uid": user_id
        },
        "audio": {
            "format": "pcm"
        },
        "request": {
            "model_name": "bigmodel",
            "enable_ddc": True, # 启用顺滑
            "show_utterances": True, # 输出语音停顿、分句、分词信息
            "result_type": "single" # 默认为"full",全量返回。设置为"single"则为增量结果返回，即不返回之前分句的结果。
            # "end_window_size": 800 # 强制判停时间(静音时长超过该值，会直接判停，输出definite)
        }
    }
    return param


PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type:
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

# Message Type Specific Flags
NO_SEQUENCE = 0b0000  # no check sequence
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011
NEG_SEQUENCE_1 = 0b0011

# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001

# Message Compression
NO_COMPRESSION = 0b0000
GZIP = 0b0001

def sauc_ws_header(
        message_type=FULL_CLIENT_REQUEST,
        message_type_specific_flags=NO_SEQUENCE,
        serial_method=JSON,
        compression_type=GZIP,
        reserved_data=0x00
):
    """
    生成 websocket 连接的 header(豆包大模型流式语音识别API)
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    """
    header = bytearray()
    header_size = 1
    header.append((PROTOCOL_VERSION << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header

def sauc_ws_before_payload(sequence: int):
    """
    生成 websocket 连接的序列 payload(豆包大模型流式语音识别API)
    :param sequence:
    :return:
    """
    before_payload = bytearray()
    before_payload.extend(sequence.to_bytes(4, 'big', signed=True))  # sequence
    return before_payload

def sauc_parse_response(res):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    payload 类似与http 请求体
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
        # receive frame with sequence
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['payload_sequence'] = seq
        payload = payload[4:]

    if message_type_specific_flags & 0x02:
        # receive last package
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
    logger.info(f"sauc_parse_response: {json.dumps(result)}")
    return result

def tts_full_client_request(user_id, text, operation):
    """
    生成TTS请求的完整数据包
    :param user_id:
    :param text:
    :param operation:
    :return:
    """
    default_header = bytearray(b'\x11\x10\x11\x00')
    request_json = {
        "app": {
            "appid": appid,
            "token": access_token,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": user_id
        },
        "audio": {
            "voice_type": "zh_female_linjia_mars_bigtts",
            "encoding": "mp3",
            "speed_ratio": 1.0
        },
        "request": {
            "reqid": uuid4().hex,
            "text": text,
            "operation": operation
        }
    }
    full_client_request = bytearray(default_header)
    payload_bytes = str.encode(json.dumps(request_json))
    payload_bytes = gzip.compress(payload_bytes)  # if no compression, comment this line
    full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
    full_client_request.extend(payload_bytes)  # payload
    return full_client_request

def tts_parse_response(res):
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    if header_size != 1:
        print(f"           Header extensions: {header_extensions}")
    if message_type == 0xb:  # audio-only server response
        # 如果没有 sequence number，则继续等待
        if message_type_specific_flags == 0:
            return (b'', False, False)
        sequence_number = int.from_bytes(payload[:4], "big", signed=True)
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        audio_chunk = payload[8:]
        # sequence_number < 0，说明这是最后一段音频
        return (audio_chunk, sequence_number < 0, False)
    elif message_type == 0xf:
        code = int.from_bytes(payload[:4], "big", signed=False)
        msg_size = int.from_bytes(payload[4:8], "big", signed=False)
        error_msg = payload[8:]
        if message_compression == 1:
            error_msg = gzip.decompress(error_msg)
        error_msg = str(error_msg, "utf-8")
        print(f"          Error message code: {code}")
        print(f"          Error message size: {msg_size} bytes")
        print(f"               Error message: {error_msg}")
        return (b'', True, True)
    elif message_type == 0xc:
        msg_size = int.from_bytes(payload[:4], "big", signed=False)
        payload = payload[4:]
        if message_compression == 1:
            payload = gzip.decompress(payload)
        print(f"            Frontend message: {payload}")
    else:
        print("undefined message type!")
        return (b'', True, false)


# def tts_http(user_id, text):
#     req_id = uuid4().hex
#     url = "https://openspeech.bytedance.com/api/v1/tts"
#     param = {
#         "app": {
#             "appid": app_id,
#             "token": access_token,
#             "cluster": "volcano_tts",
#         },
#         "user": {
#             "uid": user_id
#         },
#         "audio": {
#             "voice_type": "zh_female_linjia_mars_bigtts",
#             "encoding": "pcm",
#             "speed_ratio": 1.0,
#         },
#         "request": {
#             "reqid": req_id,
#             "text": text,
#             "operation": "query",
#         }
#     }
