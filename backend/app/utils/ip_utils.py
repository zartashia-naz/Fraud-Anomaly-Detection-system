from fastapi import Request

def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from the request.
    Works even behind proxies.
    """
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # Sometimes the header contains multiple IPs -> take first
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host

    return ip



