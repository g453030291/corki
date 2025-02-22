import json
import uuid
import struct
import os
import time
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

# Constants
PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_RESPONSE = 0b1011
FULL_SERVER_RESPONSE = 0b1001
ERROR_INFORMATION = 0b1111

# Message Type Specific Flags
MsgTypeFlagNoSeq = 0b0000
MsgTypeFlagPositiveSeq = 0b0001
MsgTypeFlagLastNoSeq = 0b0010
MsgTypeFlagNegativeSeq = 0b0011
MsgTypeFlagWithEvent = 0b0100

# Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001

# Compression
COMPRESSION_NO = 0b0000
COMPRESSION_GZIP = 0b0001

# Events
EVENT_NONE = 0
EVENT_Start_Connection = 1
EVENT_FINISHED_Connection = 2
EVENT_ConnectionStarted = 50
EVENT_ConnectionFailed = 51
EVENT_ConnectionFinished = 52
EVENT_StartSession = 100
EVENT_FinishSession = 102
EVENT_SessionStarted = 150
EVENT_SessionFinished = 152
EVENT_SessionFailed = 153
EVENT_TaskRequest = 200
EVENT_TTSSentenceStart = 350
EVENT_TTSSentenceEnd = 351
EVENT_TTSResponse = 352

class Header:
    def __init__(self):
        self.protocol_version = 0
        self.header_size = 0
        self.message_type = 0
        self.message_type_specific_flags = 0
        self.serialization_method = 0
        self.message_compression = 0
        self.reserved = 0

class Optional:
    def __init__(self):
        self.size = 0
        self.event = EVENT_NONE
        self.sessionId = ""
        self.errorCode = 0
        self.connectionSize = 0
        self.connectionId = ""
        self.response_meta_json = ""
        self.sequence = 0

    def isEmpty(self):
        return self.size == 0

class TTSResponse:
    def __init__(self):
        self.header = Header()
        self.optional = Optional()
        self.payloadSize = 0
        self.payload = bytearray()

def bytes_to_int(b):
    return int.from_bytes(b, byteorder='big')

def int_to_bytes(i):
    return i.to_bytes(4, byteorder='big')

def get_header(message_type, message_type_specific_flags, serial_method, compression_type, reserved_data):
    header = bytearray()
    header.append((PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header

def parser_response(res):
    if not res:
        return None

    response = TTSResponse()
    header = response.header

    header.protocol_version = (res[0] >> 4) & 0x0F
    header.header_size = res[0] & 0x0F
    header.message_type = (res[1] >> 4) & 0x0F
    header.message_type_specific_flags = res[1] & 0x0F
    header.serialization_method = (res[2] >> 4) & 0x0F
    header.message_compression = res[2] & 0x0F
    header.reserved = res[3]

    offset = 4
    optional = response.optional
    response.optional = optional

    if header.message_type in [FULL_SERVER_RESPONSE, AUDIO_ONLY_RESPONSE]:
        offset += read_event(res, header.message_type_specific_flags, response)
        event = response.optional.event

        if event == EVENT_ConnectionStarted:
            read_connect_started(res, response, offset)
        elif event == EVENT_ConnectionFailed:
            read_connect_failed(res, response, offset)
        elif event in [EVENT_SessionStarted, EVENT_SessionFailed, EVENT_SessionFinished]:
            offset += read_session_id(res, response, offset)
            read_meta_json(res, response, offset)
        else:
            offset += read_session_id(res, response, offset)
            offset += read_sequence(res, response, offset)
            read_payload(res, response, offset)
    elif header.message_type == ERROR_INFORMATION:
        offset += read_error_code(res, response, offset)
        read_payload(res, response, offset)

    return response

def read_connect_started(res, response, start):
    b = res[start:start+4]
    start += 4
    response.optional.size += 4
    response.optional.connectionSize = bytes_to_int(b)
    b = res[start:start+response.optional.connectionSize]
    start += response.optional.connectionSize
    response.optional.size += response.optional.connectionSize
    response.optional.connectionId = b.decode('utf-8')
    read_payload(res, response, start)

def read_connect_failed(res, response, start):
    b = res[start:start+4]
    response.optional.size += 4
    start += 4
    response.optional.connectionSize = bytes_to_int(b)
    read_meta_json(res, response, start)

def read_sequence(res, response, start):
    header = response.header
    optional = response.optional
    if header.message_type_specific_flags in [MsgTypeFlagNegativeSeq, MsgTypeFlagPositiveSeq]:
        temp = res[start:start+4]
        optional.sequence = bytes_to_int(temp)
        optional.size += 4
        return 4
    return 0

def read_meta_json(res, response, start):
    b = res[start:start+4]
    start += 4
    response.optional.size += 4
    size = bytes_to_int(b)
    b = res[start:start+size]
    response.optional.size += size
    response.optional.response_meta_json = b.decode('utf-8')

def read_payload(res, response, start):
    b = res[start:start+4]
    start += 4
    size = bytes_to_int(b)
    response.payloadSize += size
    b = res[start:start+size]
    response.payload = b
    return 4 + size

def read_error_code(res, response, start):
    b = res[start:start+4]
    response.optional.errorCode = bytes_to_int(b)
    response.optional.size += 4
    return 4

def read_event(res, masTypeFlag, response):
    if masTypeFlag == MsgTypeFlagWithEvent:
        temp = res[4:8]
        event = bytes_to_int(temp)
        response.optional.event = event
        response.optional.size += 4
        return 4
    return 0

def read_session_id(res, response, start):
    b = res[start:start+4]
    start += 4
    size = bytes_to_int(b)
    session_id_bytes = res[start:start+size]
    response.optional.sessionId = session_id_bytes.decode('utf-8')
    return 4 + size

def start_connection(websocket):
    header = get_header(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent, JSON, COMPRESSION_NO, 0)
    return send_event(websocket, header, EVENT_Start_Connection, None, None, json.dumps({}).encode('utf-8'))

def finish_connection(websocket):
    header = get_header(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent, JSON, COMPRESSION_NO, 0)
    return send_event(websocket, header, EVENT_FINISHED_Connection, None, None, json.dumps({}).encode('utf-8'))

def finish_session(websocket, session_id):
    header = get_header(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent, JSON, COMPRESSION_NO, 0)
    return send_event(websocket, header, EVENT_FinishSession, session_id, None, json.dumps({}).encode('utf-8'))

def start_tts_session(websocket, session_id, speaker):
    event = EVENT_StartSession
    payload = {
        "user": {"uid": "123456"},
        "event": event,
        "namespace": "BidirectionalTTS",
        "req_params": {
            "speaker": speaker,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000
            }
        }
    }
    header = get_header(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent, JSON, COMPRESSION_NO, 0)
    return send_event(websocket, header, event, session_id, None, json.dumps(payload).encode('utf-8'))

def send_tts_message(websocket, speaker, session_id, text):
    return send_message_with_seq(websocket, speaker, session_id, text, -1)

def send_message_with_seq(websocket, speaker, session_id, text, seq):
    payload = {
        "user": {"uid": "123456"},
        "event": EVENT_TaskRequest,
        "namespace": "BidirectionalTTS",
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000
            }
        }
    }
    sequence = int_to_bytes(seq) if seq >= 0 else None
    header = get_header(FULL_CLIENT_REQUEST, MsgTypeFlagWithEvent, JSON, COMPRESSION_NO, 0)
    return send_event(websocket, header, EVENT_TaskRequest, session_id, sequence, json.dumps(payload).encode('utf-8'))

def send_event(websocket, header, event, session_id, sequence, payload):
    full_client_request_size = len(header)
    event_bytes = int_to_bytes(event) if event != EVENT_NONE else None
    if event_bytes:
        full_client_request_size += len(event_bytes)
    session_id_bytes = session_id.encode('utf-8') if session_id else None
    session_id_size = int_to_bytes(len(session_id_bytes)) if session_id_bytes else None
    if session_id_bytes:
        full_client_request_size += len(session_id_bytes) + len(session_id_size)
    if sequence:
        full_client_request_size += len(sequence)
    payload_size = int_to_bytes(len(payload))
    full_client_request_size += len(payload_size) + len(payload)

    full_client_request = bytearray(full_client_request_size)
    dest_pos = 0
    full_client_request[dest_pos:dest_pos+len(header)] = header
    dest_pos += len(header)
    if event_bytes:
        full_client_request[dest_pos:dest_pos+len(event_bytes)] = event_bytes
        dest_pos += len(event_bytes)
    if session_id_bytes:
        full_client_request[dest_pos:dest_pos+len(session_id_size)] = session_id_size
        dest_pos += len(session_id_size)
        full_client_request[dest_pos:dest_pos+len(session_id_bytes)] = session_id_bytes
        dest_pos += len(session_id_bytes)
    if sequence:
        full_client_request[dest_pos:dest_pos+len(sequence)] = sequence
        dest_pos += len(sequence)
    full_client_request[dest_pos:dest_pos+len(payload_size)] = payload_size
    dest_pos += len(payload_size)
    full_client_request[dest_pos:dest_pos+len(payload)] = payload
    websocket.send(full_client_request)
    return True

def main():
    appid = os.getenv('V_APP_ID')
    token = os.getenv('V_ACCESS_TOKEN')
    url = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    test_text = "明朝开国皇帝朱元璋也称这本书为,万物之根"
    speaker = "zh_female_shuangkuaisisi_moon_bigtts"
    output_file = "output.mp3"

    if os.path.exists(output_file):
        os.remove(output_file)

    with connect(url, additional_headers={
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": "volc.service_type.10029",
        "X-Api-Connect-Id": str(uuid.uuid4())
    }) as websocket:
        has_finished_session = False
        session_id = str(uuid.uuid4()).replace("-", "")

        def on_open():
            print("===>onOpen")
            has_finished_session = False
            start_connection(websocket)

        def on_message(message):
            has_finished_session = False
            response = parser_response(message)
            if not response:
                return

            event = response.optional.event
            if event in [EVENT_ConnectionFailed, EVENT_SessionFailed]:
                print(f"===>response error: {event}")
                exit(-1)
            elif event == EVENT_ConnectionStarted:
                start_tts_session(websocket, session_id, speaker)
            elif event == EVENT_SessionStarted:
                send_tts_message(websocket, speaker, session_id, test_text)
            elif event == EVENT_TTSSentenceStart:
                print(f"===>response TTSSentenceStart: {event}")
            elif event == EVENT_TTSResponse:
                if response.payload:
                    if response.header.message_type == AUDIO_ONLY_RESPONSE:
                        with open(output_file, "ab") as f:
                            f.write(response.payload)
                    elif response.header.message_type == FULL_SERVER_RESPONSE:
                        print(f"===> payload: {response.payload.decode('utf-8')}")
            elif event == EVENT_TTSSentenceEnd:
                if not has_finished_session:
                    print(f"===>response TTSSentenceEnd: {event}")
                    has_finished_session = finish_session(websocket, session_id)
            elif event == EVENT_ConnectionFinished:
                print(f"===>response ConnectionFinished: {event}")
                exit(0)
            elif event == EVENT_SessionFinished:
                print(f"===>response SessionFinished: {event}")
                finish_connection(websocket)
            else:
                print(f"===>response default: {event}")

        on_open()
        while True:
            try:
                message = websocket.recv()
                on_message(message)
            except ConnectionClosed:
                break

if __name__ == "__main__":
    main()