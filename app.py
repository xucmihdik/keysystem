# app.py

from flask import Flask, request, jsonify, send_from_directory, redirect, Response, render_template, session
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public", template_folder="public")
app.secret_key = "your_secret_key"  # Set a strong secret key for session management

# In-memory storage
TOKENS = {} # { token: device_id } - Used for Linkvertise flow initiation check
# KEYS now stores creation timestamp instead of absolute expiry
# Format: { "clark-xxxx": { "created_at": "ISO_TIMESTAMP_STRING" } }
KEYS = {} # { key: { "created_at": ... } }
USED_IPS = {} # { device_id_hash: key } - Used to enforce single key per user for claim/owner_generate

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
    expired_keys = []
    for key, key_data in KEYS.items():
        is_valid, _, _ = get_key_expiry_info(key_data)
        if not is_valid:
            expired_keys.append(key)

    for key in expired_keys:
        del KEYS[key]
        # Remove from USED_IPS if it exists (for user keys)
        for device_id, k in list(USED_IPS.items()):
            if k == key:
                del USED_IPS[device_id]
                break

def generate_key(device_id=None):
    """
    Generates a new key.
    Args:
        device_id (str, optional): Device ID to associate the key with (for user flows).
                                   If None, the key is not associated with a specific user IP.
    Returns:
        tuple: (key (str), key_data (dict))
    """
    key = f"clark-{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow()
    key_data = {"created_at": created_at.isoformat()}
    KEYS[key] = key_data
    if device_id:
        # Associate the key with the device ID for user flows (enforces single key)
        USED_IPS[device_id] = key
    # Note: Keys created without device_id (e.g., from dashboard) are not added to USED_IPS
    # and are not subject to the single-key-per-user restriction.
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
            # Return key, expiry timestamp, and remaining seconds for the user's single key
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

    # Check if existing key is still valid FOR THIS USER
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

    # Generate new key ASSOCIATED WITH THIS USER'S DEVICE ID
    key, key_data = generate_key(device_id)
    del TOKENS[token]
    # Redirect with the new key
    return redirect(f"/?key={key}")

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    device_id = get_device_id()
    if secret != "your_secret_key":  # Replace with your actual secret key
        return jsonify({"error": "Unauthorized"}), 403

    # Check if existing key is still valid FOR THIS USER
    existing_key = USED_IPS.get(device_id)
    if existing_key and existing_key in KEYS:
         key_data = KEYS[existing_key]
         is_valid, _, _ = get_key_expiry_info(key_data)
         if is_valid:
             # Key still valid, return existing key info
             _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
             return jsonify({
                 "key": existing_key,
                 "expires_at": expires_at_str,
                 "remaining_seconds": remaining_seconds,
                 "status": "owner"
             })
         else:
             # Key expired, clean up
             del KEYS[existing_key]
             if device_id in USED_IPS:
                  del USED_IPS[device_id]

    # Generate new key ASSOCIATED WITH THIS USER'S DEVICE ID
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
@app.route("/panel", methods=["GET", "POST"])
def panel():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect("/panel/dashboard")
        else:
            return render_template("panel.html", error="Invalid credentials")
    return render_template("panel.html")

# Dashboard Route (Ensure login check)
@app.route("/panel/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect("/panel") # Redirect if not logged in
    clean_expired_keys() # Clean before displaying

    # Prepare key data for template (include remaining seconds)
    keys_with_info = {}
    for key, key_data in KEYS.items():
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid: # Only show valid keys
             keys_with_info[key] = {
                 "expires_at": expires_at_str,
                 "remaining_seconds": remaining_seconds
             }
        # Optionally handle expired keys differently in the dashboard if needed

    # Define the format_countdown helper function for the template
    def format_countdown(seconds):
        """Converts seconds to HH:MM:SS format string for Jinja2."""
        if seconds <= 0:
            return "Expired"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return render_template(
        "dashboard.html",
        keys=keys_with_info, # Pass the enriched data
        format_expiry=lambda iso_str: datetime.fromisoformat(iso_str).strftime("%B %d, %Y %I:%M %p"),
        format_countdown=format_countdown # Pass the new helper function
    )

@app.route("/logout")
def logout():
    session.pop('logged_in', None)  # Remove the logged in session
    return redirect("/panel")

# --- MODIFIED: Allow creating a new key without checking for existing user keys ---
# This removes the restriction for the admin dashboard only.
# The user-facing claim/owner_generate/check_key_status routes still enforce single key per user/IP.
@app.route("/create_key", methods=["POST"])
def create_key():
    # DO NOT check for existing valid key for the user's IP/device
    # Simply generate a new key every time this route is called (e.g., from the dashboard)

    # Generate new key (without associating it with a specific user IP immediately)
    # We can modify generate_key slightly or just handle it here.
    key = f"clark-{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow()
    key_data = {"created_at": created_at.isoformat()}
    KEYS[key] = key_data
    # Note: We don't add this key to USED_IPS here, because it's an admin-created key,
    # not tied to a specific user's IP for the single-key restriction logic.
    # The single-key restriction for users relies on USED_IPS, which is populated by claim/owner_generate.

    _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
    return jsonify({
        "key": key,
        "expires_at": expires_at_str,
        "remaining_seconds": remaining_seconds
    })

@app.route("/delete_key", methods=["POST"])
def delete_key():
    key = request.json.get("key")
    if key in KEYS:
        del KEYS[key]
        # Also remove from USED_IPS if it exists (in case an admin deletes a user's key)
        for device_id, k in list(USED_IPS.items()): # Iterate over a copy
            if k == key:
                del USED_IPS[device_id]
                break
        return jsonify({"success": True})
    return jsonify({"error": "Key not found"}), 404

@app.route("/manage_key", methods=["POST"])
def manage_key():
    # Example: Sets a NEW key duration from NOW (not extending)
    data = request.json
    key = data.get("key")
    days = data.get("days", 1) # Default to 1 day if not provided
    try:
        days = int(days)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid days value"}), 400

    if key in KEYS:
        # Create a NEW key entry with the current time as creation time
        # and the specified duration. This effectively resets/renews the key.
        new_created_at = datetime.utcnow()
        KEYS[key] = {"created_at": new_created_at.isoformat()}
        _, new_expires_at_str, new_remaining_seconds = get_key_expiry_info(KEYS[key])
        return jsonify({
            "success": True,
            "new_expiry": new_expires_at_str,
            "new_remaining_seconds": new_remaining_seconds
        })
    return jsonify({"error": "Key not found"}), 404


@app.route("/all_keys", methods=["GET"])
def all_keys():
    # Return keys with validity info
    clean_expired_keys()
    keys_info = {}
    for key, key_data in KEYS.items():
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid: # Only return valid keys
            keys_info[key] = {
                "expires_at": expires_at_str,
                "remaining_seconds": remaining_seconds
            }
    return jsonify(keys_info)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
