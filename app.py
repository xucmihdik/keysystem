# app.py (Corrected and Integrated)

from flask import Flask, request, jsonify, send_from_directory, redirect, Response, render_template, session
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public", template_folder="public")
app.secret_key = "your_secret_key"  # Set a strong secret key for session management

# In-memory storage
TOKENS = {} # { token: device_id }
# KEYS now stores creation timestamp instead of absolute expiry
# Format: { "clark-xxxx": { "created_at": "ISO_TIMESTAMP_STRING" } }
KEYS = {} # { key: { "created_at": ... } }
USED_IPS = {} # { device_id_hash: key }

ADMIN_USERNAME = "admin"  # Set your admin username
ADMIN_PASSWORD = "password"  # Set your admin password

# --- Helper Functions ---

def get_device_id():
    """Generates a unique identifier for the user's device/browser."""
    ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")
    # Simple concatenation - consider hashing (e.g., hashlib.sha256) for better privacy/security
    return ip + user_agent

def get_key_expiry_info(key_data):
    """
    Calculates if a key is valid, its expiry time, and remaining seconds.
    Args:
        key_data (dict): The dictionary containing the key's 'created_at' timestamp.
    Returns:
        tuple: (is_valid (bool), expires_at_iso (str or None), remaining_seconds (int))
    """
    created_at_str = key_data.get("created_at")
    if not created_at_str:
        return False, None, 0 # Invalid key data

    try:
        created_at = datetime.fromisoformat(created_at_str)
        expires_at = created_at + timedelta(hours=24)
        now = datetime.utcnow()
        is_valid = now < expires_at
        remaining_seconds = int((expires_at - now).total_seconds()) if is_valid else 0
        return is_valid, expires_at.isoformat(), remaining_seconds
    except ValueError:
        # Error parsing the date string
        return False, None, 0

def clean_expired_keys():
    """Remove expired keys from the KEYS and USED_IPS dictionaries."""
    current_time = datetime.utcnow()
    expired_keys = []
    for key, key_data in KEYS.items():
        is_valid, _, _ = get_key_expiry_info(key_data)
        if not is_valid:
            expired_keys.append(key)

    for key in expired_keys:
        del KEYS[key]
        # Remove from USED_IPS if it exists
        for device_id, k in list(USED_IPS.items()):
            if k == key:
                del USED_IPS[device_id]
                break

def generate_key(device_id):
    """Generates a new key associated with a device ID."""
    key = f"clark-{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow()
    key_data = {"created_at": created_at.isoformat()}
    KEYS[key] = key_data
    USED_IPS[device_id] = key
    return key, key_data

# --- Routes ---

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    device_id = get_device_id()
    clean_expired_keys()  # Clean expired keys before checking
    key = USED_IPS.get(device_id)
    if key and key in KEYS:
        key_data = KEYS[key]
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid and expires_at_str:
            # Return key, expiry timestamp, and remaining seconds
             return jsonify({
                "has_key": True,
                "key": key,
                "expires_at": expires_at_str, # Full expiry timestamp
                "remaining_seconds": remaining_seconds # Seconds left
            })
        else:
            # Key expired, clean up
            del KEYS[key]
            if device_id in USED_IPS:
                 del USED_IPS[device_id]

    return jsonify({"has_key": False})

@app.route("/get_token")
def get_token():
    referer = request.headers.get("Referer", "")
    if "linkvertise.com" not in referer.lower():
        return "", 403
    device_id = get_device_id()
    token = uuid.uuid4().hex[:24]
    TOKENS[token] = device_id
    return redirect(f"/claim?token={token}")

@app.route("/claim")
def claim():
    token = request.args.get("token")
    device_id = get_device_id()
    if not token or token not in TOKENS or TOKENS[token] != device_id:
        return "", 403

    # Check if existing key is still valid
    existing_key = USED_IPS.get(device_id)
    if existing_key and existing_key in KEYS:
         key_data = KEYS[existing_key]
         is_valid, _, _ = get_key_expiry_info(key_data)
         if is_valid:
             # Key still valid, redirect with existing key
             del TOKENS[token] # Clean up token
             return redirect(f"/?key={existing_key}")
         else:
             # Key expired, clean up
             del KEYS[existing_key]
             if device_id in USED_IPS:
                  del USED_IPS[device_id]

    # Generate new key
    key, key_data = generate_key(device_id)
    del TOKENS[token]
    # expires_at_str is calculated on the frontend now, but we pass the key
    return redirect(f"/?key={key}")

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    device_id = get_device_id()
    if secret != "your_secret_key":  # Replace with your actual secret key
        return jsonify({"error": "Unauthorized"}), 403

    # Check if existing key is still valid
    existing_key = USED_IPS.get(device_id)
    if existing_key and existing_key in KEYS:
         key_data = KEYS[existing_key]
         is_valid, _, _ = get_key_expiry_info(key_data)
         if is_valid:
             # Key still valid, return existing key info
             _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
             return jsonify({
                 "key": existing_key, # Fixed typo: was "key "
                 "expires_at": expires_at_str, # Fixed typo: was "expires_at "
                 "remaining_seconds": remaining_seconds, # Fixed typo: was "remaining_seconds "
                 "status": "owner" # Fixed typo: was "status "
             })
         else:
             # Key expired, clean up
             del KEYS[existing_key]
             if device_id in USED_IPS:
                  del USED_IPS[device_id]

    # Generate new key
    key, key_data = generate_key(device_id)
    _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
    return jsonify({
        "key": key,
        "expires_at": expires_at_str,
        "remaining_seconds": remaining_seconds,
        "status": "owner"
    })

@app.route("/validate_key")
def validate_key():
    key = request.args.get("key")
    if key in KEYS:
        key_data = KEYS[key]
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid:
            return jsonify({
                "valid": True,
                "expires_at": expires_at_str,
                "remaining_seconds": remaining_seconds
            })
    return jsonify({"valid": False}), 404

@app.route("/loader")
def loader():
    if os.path.exists("gui.lua"):
        with open("gui.lua", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "GUI not found", 404

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

# Panel Login Route
@app.route("/panel", methods=["GET
