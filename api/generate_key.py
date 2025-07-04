import json
from datetime import datetime, timedelta
import uuid

# In-memory key store (temporary, resets every deploy)
KEYS = {}

def handler(request):
    key = f"valid-{uuid.uuid4().hex[:10]}"
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()

    KEYS[key] = expires_at

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "key": key,
            "expires_at": expires_at
        })
    }
