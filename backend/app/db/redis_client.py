# app/db/redis_client.py
import os
import redis
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
rc = redis.from_url(REDIS_URL, decode_responses=True)

# small convenience wrappers
def r_get(key):
    v = rc.get(key)
    return json.loads(v) if v else None

def r_set(key, value, ex=None):
    rc.set(key, json.dumps(value), ex=ex)
