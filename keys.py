import uuid
from datetime import datetime, timedelta

KEYS = {}       # Stores: key -> expiry
USED_IPS = {}   # Stores: ip -> key

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:10]}"
    expiry = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expiry.isoformat()
    USED_IPS[ip] = key
    return key, expiry.isoformat()
