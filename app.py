# app.py

from flask import Flask, request, jsonify, send_from_directory, redirect, Response, render_template, session
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public", template_folder="public")
# IMPORTANT: Change this secret key to a long, random, secret string in production!
app.secret_key = "your_secret_key_change_this_for_production"

# In-memory storage (Consider using a database for persistence in production)
TOKENS = {} # { token: device_id } - Used for Linkvertise flow initiation check
# KEYS now stores the absolute expiry timestamp
# Format: { "clark-xxxx": { "expires_at": "ISO_TIMESTAMP_STRING" } }
KEYS = {} # { key: { "expires_at": ... } }
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
        key_data (dict): The dictionary containing the key's 'expires_at' timestamp.
    Returns:
        tuple: (is_valid (bool), expires_at_iso (str or None), remaining_seconds (int))
    """
    expires_at_str = key_data.get("expires_at")
    if not expires_at_str:
        return False, None, 0 # Invalid key data

    try:
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.utcnow()
        is_valid = now < expires_at
        remaining_seconds = int((expires_at - now).total_seconds()) if is_valid else 0
        return is_valid, expires_at.isoformat(), remaining_seconds
    except ValueError:
        return False, None, 0 # Error parsing date

def clean_expired_keys():
    """Remove expired keys from the KEYS and USED_IPS dictionaries."""
    expired_keys = []
    for key, key_data in KEYS.items():
        is_valid, _, _ = get_key_expiry_info(key_data)
        if not is_valid:
            expired_keys.append(key)

    for key in expired_keys:
        if key in KEYS: # Safety check
            del KEYS[key]
        # Remove from USED_IPS if it exists (for user keys)
        for device_id, k in list(USED_IPS.items()):
            if k == key:
                del USED_IPS[device_id]
                break

def generate_key(device_id=None, duration_hours=24):
    """
    Generates a new key.
    Args:
        device_id (str, optional): Device ID to associate the key with (for user flows).
                                   If None, the key is not associated with a specific user IP.
        duration_hours (int): Duration in hours for the key's initial validity (default 24).
    Returns:
        tuple: (key (str), key_data (dict))
    """
    key = f"clark-{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    key_data = {"expires_at": expires_at.isoformat()}
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
    clean_expired_keys() # Clean expired keys before checking
    key = USED_IPS.get(device_id)
    if key and key in KEYS:
        key_data = KEYS[key]
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid and expires_at_str:
             return jsonify({
                "has_key": True,
                "key": key,
                "expires_at": expires_at_str,
                "remaining_seconds": remaining_seconds
            })
        else:
            # Key expired or invalid, clean up
            if key in KEYS: del KEYS[key]
            if device_id in USED_IPS: del USED_IPS[device_id]

    return jsonify({"has_key": False})

@app.route("/get_token")
def get_token():
    referer = request.headers.get("Referer", "")
    # Basic check to ensure request came from Linkvertise
    if "linkvertise.com" not in referer.lower():
        return "Access Denied: Invalid Referrer", 403
    device_id = get_device_id()
    token = uuid.uuid4().hex[:24]
    TOKENS[token] = device_id
    return redirect(f"/claim?token={token}")

@app.route("/claim")
def claim():
    token = request.args.get("token")
    device_id = get_device_id()
    # Validate token existence and association with the requesting device
    if not token or token not in TOKENS or TOKENS[token] != device_id:
        return "Access Denied: Invalid Token or Device Mismatch", 403

    # Check if the user already has a *valid* key
    existing_key = USED_IPS.get(device_id)
    if existing_key and existing_key in KEYS:
         key_data = KEYS[existing_key]
         is_valid, _, _ = get_key_expiry_info(key_data)
         if is_valid:
             # Key is still valid, redirect user to home with the existing key
             del TOKENS[token] # Clean up the one-time-use token
             return redirect(f"/?key={existing_key}")
         else:
             # Key has expired, clean up the old key entries
             if existing_key in KEYS:
                  del KEYS[existing_key]
             if device_id in USED_IPS:
                  del USED_IPS[device_id]

    # Generate a new key specifically for this user's device (default 24h)
    key, key_data = generate_key(device_id, duration_hours=24)
    del TOKENS[token] # Clean up the one-time-use token
    return redirect(f"/?key={key}")

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    device_id = get_device_id()
    # Validate the secret key provided in the request
    if secret != "your_secret_key": # Replace with your actual secret key
        return jsonify({"error": "Unauthorized"}), 403

    # Check if the user already has a *valid* key
    existing_key = USED_IPS.get(device_id)
    if existing_key and existing_key in KEYS:
         key_data = KEYS[existing_key]
         is_valid, _, _ = get_key_expiry_info(key_data)
         if is_valid:
             # Key is still valid, return the existing key information
             _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
             return jsonify({
                 "key": existing_key,
                 "expires_at": expires_at_str,
                 "remaining_seconds": remaining_seconds,
                 "status": "owner"
             })
         else:
             # Key has expired, clean up the old key entries
             if existing_key in KEYS:
                  del KEYS[existing_key]
             if device_id in USED_IPS:
                  del USED_IPS[device_id]

    # Generate a new key specifically for this user's device (default 24h)
    key, key_data = generate_key(device_id, duration_hours=24)
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
    # Check if the key exists in the KEYS dictionary
    if key in KEYS:
        key_data = KEYS[key]
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid:
            # Key is valid, return its details
            return jsonify({
                "valid": True,
                "expires_at": expires_at_str,
                "remaining_seconds": remaining_seconds
            })
    # Key not found or not valid
    return jsonify({"valid": False}), 404

@app.route("/loader")
def loader():
    # Serve the gui.lua file if it exists
    if os.path.exists("gui.lua"):
        with open("gui.lua", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    # Return 404 if file not found
    return "GUI script not found", 404

# Serve static files from the 'public' directory
@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

# --- Admin Panel Routes ---

# Panel Login Route
@app.route("/panel", methods=["GET", "POST"])
def panel():
    # Handle POST request (login form submission)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Validate credentials (replace with database lookup in production)
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            # Login successful: Set session variable
            session['logged_in'] = True
            # IMPORTANT: Use absolute path for redirect
            return redirect("/panel/dashboard")
        else:
            # Login failed: Render login page with error message
            return render_template("panel.html", error="Invalid credentials")
    # Handle GET request (display login form)
    return render_template("panel.html") # Render the login template

# Dashboard Route (Ensure login check)
@app.route("/panel/dashboard")
def dashboard():
    # CRITICAL: Check session variable to enforce login
    if not session.get('logged_in'):
        # User is not logged in, redirect them to the login page
        # IMPORTANT: Use absolute path for redirect
        return redirect("/panel")

    # User is logged in, proceed to display the dashboard
    clean_expired_keys() # Clean expired keys before displaying

    # Prepare key data for the template (include remaining seconds for countdown)
    keys_with_info = {}
    for key, key_data in KEYS.items():
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid: # Only show valid keys in the dashboard
             keys_with_info[key] = {
                 "expires_at": expires_at_str,
                 "remaining_seconds": remaining_seconds
             }

    # Define the format_countdown helper function for the Jinja2 template
    def format_countdown(seconds):
        """Converts seconds to HH:MM:SS format string for Jinja2."""
        if seconds <= 0:
            return "Expired"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        # Format with leading zeros (e.g., 01:05:09)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    # Render the dashboard template, passing the key data and helper functions
    return render_template(
        "dashboard.html",
        keys=keys_with_info, # Pass the enriched key data
        # Lambda to format expiry datetime string into a readable format
        format_expiry=lambda iso_str: datetime.fromisoformat(iso_str).strftime("%B %d, %Y %I:%M %p"),
        # Pass the format_countdown function for use in the template
        format_countdown=format_countdown
    )

@app.route("/logout")
def logout():
    # Remove the 'logged_in' session variable to log the user out
    session.pop('logged_in', None)
    # Redirect the user back to the login page
    return redirect("/panel")

# --- Admin API Routes ---

# --- MODIFIED: Allow creating a new key without checking for existing user keys ---
# This removes the restriction for the admin dashboard only.
# The user-facing claim/owner_generate/check_key_status routes still enforce single key per user/IP.
@app.route("/create_key", methods=["POST"])
def create_key():
    # DO NOT check for existing valid key for the user's IP/device.
    # Simply generate a new key every time this route is called (e.g., from the dashboard).
    # This allows the admin to create multiple keys.

    # Generate new key (without associating it with a specific user IP immediately).
    # We directly handle key generation here, bypassing the user association logic.
    # Default duration is 24 hours for admin-created keys as well.
    key, key_data = generate_key(device_id=None, duration_hours=24)
    _, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
    # Return the new key information to the dashboard frontend
    return jsonify({
        "key": key,
        "expires_at": expires_at_str,
        "remaining_seconds": remaining_seconds
    })

@app.route("/delete_key", methods=["POST"])
def delete_key():
    # Get the key to delete from the JSON request body
    key = request.json.get("key")
    # Check if the key exists
    if key in KEYS:
        # Remove the key from the main KEYS dictionary
        del KEYS[key]
        # Also remove the association from USED_IPS if it exists
        # (in case an admin deletes a user's key)
        for device_id, k in list(USED_IPS.items()): # Iterate over a copy
            if k == key:
                del USED_IPS[device_id]
                break
        # Return success response
        return jsonify({"success": True})
    # Return error response if key not found
    return jsonify({"error": "Key not found"}), 404

# --- UPDATED: manage_key now correctly sets expires_at based on days ---
@app.route("/manage_key", methods=["POST"])
def manage_key():
    # Get data from the JSON request body
    data = request.json
    key = data.get("key")
    days = data.get("days", 1) # Default to 1 day if not provided
    # Validate the 'days' parameter
    try:
        days = int(days)
        if days <= 0:
             raise ValueError("Days must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid days value. Must be a positive integer."}), 400

    # Check if the key exists
    if key in KEYS:
        # Set the new expiry time based on the provided number of days from NOW
        new_expires_at = datetime.utcnow() + timedelta(days=days)
        KEYS[key] = {"expires_at": new_expires_at.isoformat()}
        _, new_expires_at_str, new_remaining_seconds = get_key_expiry_info(KEYS[key])
        # Return success response with new expiry details
        return jsonify({
            "success": True,
            "new_expiry": new_expires_at_str,
            "new_remaining_seconds": new_remaining_seconds
        })
    # Return error response if key not found
    return jsonify({"error": "Key not found"}), 404

@app.route("/all_keys", methods=["GET"])
def all_keys():
    # Return keys with validity info (used for potential API access or full refresh)
    clean_expired_keys() # Clean first
    keys_info = {}
    for key, key_data in KEYS.items():
        is_valid, expires_at_str, remaining_seconds = get_key_expiry_info(key_data)
        if is_valid: # Only return valid keys
            keys_info[key] = {
                "expires_at": expires_at_str,
                "remaining_seconds": remaining_seconds
            }
    return jsonify(keys_info) # Return JSON data


# Run the application
if __name__ == "__main__":
    # Get port from environment variable (useful for platforms like Render) or default to 8080
    port = int(os.environ.get("PORT", 8080))
    # Run the Flask app, listening on all interfaces (0.0.0.0) on the specified port
    app.run(host="0.0.0.0", port=port)
