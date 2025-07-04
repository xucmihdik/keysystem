import json
from datetime import datetime
from urllib.parse import parse_qs

# Access the shared KEYS dictionary from generate_key.py
try:
    from api.generate_key import KEYS
except:
    KEYS = {}  # fallback in case shared import fails

def handler(request):
    query = parse_qs(request.get("queryString", ""))
    key = query.get("key", [None])[0]

    if not key:
        return {
            "statusCode": 400,
            "headers": { "Content-Type": "application/json" },
            "body": json.dumps({ "valid": False, "error": "No key provided" })
        }

    expiry = KEYS.get(key)

    if expiry:
        if datetime.utcnow() < datetime.fromisoformat(expiry):
            return {
                "statusCode": 200,
                "headers": { "Content-Type": "application/json" },
                "body": json.dumps({ "valid": True })
            }
        else:
            return {
                "statusCode": 200,
                "headers": { "Content-Type": "application/json" },
                "body": json.dumps({ "valid": False, "error": "Key expired" })
            }

    return {
        "statusCode": 200,
        "headers": { "Content-Type": "application/json" },
        "body": json.dumps({ "valid": False, "error": "Invalid key" })
    }
