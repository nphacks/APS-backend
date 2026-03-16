# redis_client.py
import os
import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = None

def init_redis():
    global redis_client
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

def get_redis():
    return redis_client


def close_redis():
    global redis_client
    if redis_client:
        redis_client.close()
