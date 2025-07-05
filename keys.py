from datetime import datetime, timedelta
import uuid

KEYS = {}
USED_IPS = {}

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:8]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expires_at.isoformat()
    USED_IPS[ip] = key
    return key, expires_at.isoformat()
