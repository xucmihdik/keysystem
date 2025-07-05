import uuid
import json
import os
from datetime import datetime, timedelta

KEYS_FILE = "keys.json"
USED_FILE = "used_ips.json"

def load_data():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            keys = json.load(f)
    else:
        keys = {}

    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r") as f:
            used_ips = json.load(f)
    else:
        used_ips = {}

    # Clean up expired keys
    now = datetime.utcnow()
    keys = {k: v for k, v in keys.items() if datetime.fromisoformat(v) > now}
    used_ips = {ip: k for ip, k in used_ips.items() if k in keys}

    return keys, used_ips

def save_data():
    with open(KEYS_FILE, "w") as f:
        json.dump(KEYS, f)
    with open(USED_FILE, "w") as f:
        json.dump(USED_IPS, f)

KEYS, USED_IPS = load_data()

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:10]}"
    expiry = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expiry.isoformat()
    USED_IPS[ip] = key
    save_data()
    return key, expiry.isoformat()
