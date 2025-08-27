import json
import time

DEFAULT_HEADERS = []

def make_packet(p_type, frm, to, payload, hops=0, headers=None):
    return {
        'type': p_type,
        'from': frm,
        'to': to,
        'hops': hops,
        'headers': headers or DEFAULT_HEADERS,
        'payload': payload,
        'ts': time.time()
    }

def decode_message(msg_data):
    # Redis devuelve bytes (si no se configuró decode_responses)
    if isinstance(msg_data, bytes):
        msg_data = msg_data.decode('utf-8')
    return json.loads(msg_data)

