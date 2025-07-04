import uuid
from datetime import datetime, timedelta

# In-memory storage of keys
KEYS = {}

def generate_key():
    # Create a key with clark- prefix
    key = f"clark-{uuid.uuid4().hex[:10]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expires_at.isoformat()
    return key, expires_at.isoformat()
