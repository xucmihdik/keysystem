import uuid
from datetime import datetime, timedelta

KEYS = {}

def generate_key():
    key = f"valid-{uuid.uuid4().hex[:10]}"
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    KEYS[key] = expires_at
    return key, expires_at
