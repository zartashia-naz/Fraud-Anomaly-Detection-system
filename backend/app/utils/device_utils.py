# from fastapi import Request
# import hashlib

# def get_device_id(request: Request) -> str:
#     user_agent = request.headers.get("User-Agent", "unknown-device")
#     hashed = hashlib.md5(user_agent.encode()).hexdigest()
#     return f"DEV-{hashed[:10]}"


# =================CLAUDE CODE BELOW-========================


# backend/app/utils/device_utils.py

import hashlib
import json
from typing import Dict, Any
from user_agents import parse

def generate_device_fingerprint(device_data: Dict[str, Any]) -> str:
    """
    Generate unique device ID from actual device characteristics
    This is NOT randomly generated - it's based on real device properties
    Same device = Same fingerprint (even across browser restarts)
    """
    # Extract key components for fingerprinting
    fingerprint_components = [
        device_data.get("fingerprint_id", ""),  # FingerprintJS ID (most reliable)
        device_data.get("user_agent", ""),
        device_data.get("screen_resolution", ""),
        device_data.get("timezone", ""),
        device_data.get("language", ""),
        device_data.get("platform", ""),
        str(device_data.get("hardware_concurrency", "")),
        device_data.get("device_memory", ""),
        str(device_data.get("color_depth", "")),
        str(device_data.get("pixel_ratio", "")),
        device_data.get("canvas_fingerprint", ""),
        device_data.get("webgl_vendor", ""),
        device_data.get("webgl_renderer", ""),
    ]
    
    # Create stable hash
    fingerprint_string = "|".join(str(c) for c in fingerprint_components)
    device_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    # Return short but unique ID
    return f"device-{device_hash[:16]}"


def parse_device_info(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract human-readable device information
    """
    user_agent = device_data.get("user_agent", "")
    ua_parsed = parse(user_agent)
    
    return {
        "device_id": generate_device_fingerprint(device_data),
        "device_name": f"{ua_parsed.browser.family} on {ua_parsed.os.family}",
        "browser": {
            "name": ua_parsed.browser.family,
            "version": ua_parsed.browser.version_string,
        },
        "os": {
            "name": ua_parsed.os.family,
            "version": ua_parsed.os.version_string,
        },
        "device_type": "mobile" if ua_parsed.is_mobile else "tablet" if ua_parsed.is_tablet else "desktop",
        "is_bot": ua_parsed.is_bot,
        "screen_resolution": device_data.get("screen_resolution", "unknown"),
        "timezone": device_data.get("timezone", "unknown"),
        "language": device_data.get("language", "unknown"),
        "fingerprint_data": device_data,  # Store full data for future analysis
    }


def get_device_risk_indicators(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract risk indicators from device data
    """
    ua_parsed = parse(device_data.get("user_agent", ""))
    
    return {
        "is_bot": ua_parsed.is_bot,
        "is_headless": "headless" in device_data.get("user_agent", "").lower(),
        "has_touch": device_data.get("touch_support", False),
        "screen_anomaly": _check_screen_anomaly(device_data),
        "timezone_mismatch": False,  # Will be checked against IP geolocation later
    }


def _check_screen_anomaly(device_data: Dict[str, Any]) -> bool:
    """Check for unusual screen configurations"""
    try:
        resolution = device_data.get("screen_resolution", "0x0")
        width, height = map(int, resolution.split("x"))
        
        # Flag extremely small or unusually large screens
        if width < 800 or height < 600:  # Too small for normal use
            return True
        if width > 7680 or height > 4320:  # Larger than 8K
            return True
            
        return False
    except:
        return False