import json
from urllib.parse import parse_qs

def handler(request):
    query = parse_qs(request["queryString"])
    key = query.get("key", [None])[0]

    if not key:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"valid": False, "error": "No key provided"})
        }

    if key.startswith("valid-"):
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"valid": True})
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"valid": False, "error": "Invalid key"})
    }
