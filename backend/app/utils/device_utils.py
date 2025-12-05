from fastapi import Request
import hashlib

def get_device_id(request: Request) -> str:
    user_agent = request.headers.get("User-Agent", "unknown-device")
    hashed = hashlib.md5(user_agent.encode()).hexdigest()
    return f"DEV-{hashed[:10]}"
