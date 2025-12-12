# app/core/dsa/redis_dsa.py
import json
import time
from datetime import datetime
from app.db.redis_client import rc

"""
Redis DSA primitives used by routes/services:

- Recent queue (LIST) for last N transactions/logins
- Sliding window (LIST + TTL) for login attempts per minute
- Priority queue (ZSET) for anomaly scores
- Simple hash (HSET) to store last_device / last_ip
"""

# RECENT QUEUE keys (per-user)
def push_recent_txn(user_id: str, txn: dict, limit: int = 10):
    key = f"user:{user_id}:recent_txn"
    rc.lpush(key, json.dumps(txn))
    rc.ltrim(key, 0, limit - 1)
    rc.expire(key, 60 * 60 * 24 * 7)  # keep 7 days by default

def get_recent_txns(user_id: str):
    key = f"user:{user_id}:recent_txn"
    raw = rc.lrange(key, 0, -1)
    return [json.loads(r) for r in raw]

def push_recent_login(user_id: str, log: dict, limit: int = 10):
    key = f"user:{user_id}:recent_logins"
    rc.lpush(key, json.dumps(log))
    rc.ltrim(key, 0, limit - 1)
    rc.expire(key, 60 * 60 * 24 * 7)

def get_recent_logins(user_id: str):
    key = f"user:{user_id}:recent_logins"
    raw = rc.lrange(key, 0, -1)
    return [json.loads(r) for r in raw]


# SLIDING WINDOW: record attempts in list and rely on TTL/purge for windowing
def record_login_attempt(user_id: str, ttl_seconds: int = 60):
    key = f"user:{user_id}:attempts"
    now = time.time()
    rc.lpush(key, now)
    rc.expire(key, ttl_seconds)
    # return current count in the list
    return rc.llen(key)

def count_login_attempts(user_id: str):
    key = f"user:{user_id}:attempts"
    return rc.llen(key)  # attempts within window (TTL applied)


# PRIORITY QUEUE FOR ANOMALIES (ZSET)
def push_anomaly_score(anomaly_id: str, score: float, payload: dict, payload_ttl: int = 3600):
    # store score in sorted set and payload in hash
    rc.zadd("anomalies:queue", {anomaly_id: score})
    rc.hset("anomalies:payloads", anomaly_id, json.dumps(payload))
    rc.expire("anomalies:payloads", payload_ttl)

def peek_top_anomalies(limit: int = 10):
    # return list of (id, score)
    return rc.zrevrange("anomalies:queue", 0, limit - 1, withscores=True)

def pop_top_anomalies(limit: int = 10):
    items = rc.zrevrange("anomalies:queue", 0, limit - 1, withscores=True)
    results = []
    for aid, score in items:
        payload_raw = rc.hget("anomalies:payloads", aid)
        payload = json.loads(payload_raw) if payload_raw else None
        results.append((aid, float(score), payload))
        # remove
        rc.zrem("anomalies:queue", aid)
        rc.hdel("anomalies:payloads", aid)
    return results

# last device/ip quick access
def set_last_device(user_id: str, device_id: str):
    rc.hset("user:last_device", user_id, device_id)

def get_last_device(user_id: str):
    return rc.hget("user:last_device", user_id)

def set_last_ip(user_id: str, ip: str):
    rc.hset("user:last_ip", user_id, ip)

def get_last_ip(user_id: str):
    return rc.hget("user:last_ip", user_id)
