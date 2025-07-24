from datetime import datetime, timedelta
import uuid

KEYS = {}
USED_IPS = {}

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)  # Set expiration to 24 hours from now
    KEYS[key] = expires_at.isoformat()  # Store the expiration time in ISO format
    USED_IPS[ip] = key
    return key, expires_at.isoformat()
