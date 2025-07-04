from datetime import datetime, timedelta
import uuid
import json
# hi
def handler(request):
    key = f"valid-{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "key": key,
            "expires_at": expires_at.isoformat()
        })
    }
