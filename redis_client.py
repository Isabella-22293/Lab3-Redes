import redis
import json

HOST = "lab3.redesuvg.cloud"
PORT = 6379
PWD = "UVGRedis2025"

def get_redis():
    return redis.Redis(
        host=HOST,
        port=PORT,
        password=PWD,
        decode_responses=True 
    )

def get_pubsub(redis_conn):
    return redis_conn.pubsub()

def publish(redis_conn, channel, message_dict):
    payload = json.dumps(message_dict)
    redis_conn.publish(channel, payload)
