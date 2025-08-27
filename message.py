from __future__ import annotations
import json
from typing import Any, Dict

PROTO_ALLOWED = {"dijkstra", "flooding", "lsr", "dvr"}
TYPE_ALLOWED = {"message", "echo", "info", "hello"}

def make_packet(proto: str, type_: str, from_: str, to: str, ttl: int, payload: Any, headers=None) -> Dict[str, Any]:
    assert proto in PROTO_ALLOWED, f"proto inválido: {proto}"
    assert type_ in TYPE_ALLOWED, f"type inválido: {type_}"
    assert isinstance(ttl, int) and ttl >= 0
    return {
        "proto": proto,
        "type": type_,
        "from": from_,
        "to": to,
        "ttl": ttl,
        "headers": headers or [],
        "payload": payload,
    }

def serialize(pkt: Dict[str, Any]) -> bytes:
    return (json.dumps(pkt) + "\n").encode("utf-8")

def deserialize(data: bytes) -> Dict[str, Any]:
    return json.loads(data.decode("utf-8"))
