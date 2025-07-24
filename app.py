from flask import Flask, request, jsonify, send_from_directory, redirect, Response, render_template, session
from datetime import datetime, timedelta
import secrets
import uuid
import os

app = Flask(__name__, static_folder="public", template_folder="public")
app.secret_key = secrets.token_hex(32)  # Secure random secret key
TOKENS = {}  # Added missing TOKENS dictionary
KEYS = {}
USED_IPS = {}
ADMIN_USERNAME = "admin"  # Change this to your actual admin username
ADMIN_PASSWORD = "password"  # Change this to your actual admin password

# Helper functions
def get_device_id():
    ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")  # Fixed typo in header name
    return ip + user_agent

def format_expiry(expiry):
    """Convert expiry string to a more readable format."""
    date = datetime.fromisoformat(expiry)
    return date.strftime("%B %d, %Y %I:%M %p")

def clean_expired_keys():
    """Remove expired keys from the KEYS and USED_IPS dictionaries."""
    current_time = datetime.utcnow()
    expired_keys = [key for key, expiry in KEYS.items() if datetime.fromisoformat(expiry) <= current_time]
    for key in expired_keys:
        del KEYS[key]
        # Remove from USED_IPS if it exists
        for ip, k in list(USED_IPS.items()):
            if k == key:
                del USED_IPS[ip]
                break

# Security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    if request.path.startswith('/panel'):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Routes
@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    device_id = get_device_id()
    clean_expired_keys()
    key = USED_IPS.get(device_id)
    if key and key in KEYS:
        expiry_str = KEYS[key]
        expiry = datetime.fromisoformat(expiry_str)
        if expiry > datetime.utcnow():
            return jsonify({"has_key": True, "key": key, "expires_at": expiry_str})
        else:
            del KEYS[key]
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

    if device_id in USED_IPS:
        key = USED_IPS[device_id]
        expiry_str = KEYS.get(key)
        if not expiry_str:
            # If something went wrong and expiry is missing, regenerate key
            key, expiry_str = generate_key(device_id)
        else:
            expiry = datetime.fromisoformat(expiry_str)
            if expiry <= datetime.utcnow():
                del KEYS[key]
                del USED_IPS[device_id]
                key, expiry_str = generate_key(device_id)
    else:
        key, expiry_str = generate_key(device_id)

    del TOKENS[token]
    return redirect(f"/?key={key}&expires_at={expiry_str}")

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    device_id = get_device_id()
    if secret != "your_secret_key":  # Replace with your actual secret key
        return jsonify({"error": "Unauthorized"}), 403
    if device_id in USED_IPS:
        key = USED_IPS[device_id]
        expiry = datetime.fromisoformat(KEYS.get(key, "1970-01-01T00:00:00"))
        if expiry <= datetime.utcnow():
            del KEYS[key]
            del USED_IPS[device_id]
            key, _ = generate_key(device_id)
    else:
        key, _ = generate_key(device_id)
    return jsonify({"key": key, "expires_at": KEYS[key], "status": "owner"})

@app.route("/validate_key")
def validate_key():
    key = request.args.get("key")
    if key in KEYS and datetime.fromisoformat(KEYS[key]) > datetime.utcnow():
        return jsonify({"valid": True, "expires_at": KEYS[key]})
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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['last_activity'] = datetime.utcnow().isoformat()
            return redirect("/panel/dashboard")
        return render_template("panel.html", error="Invalid credentials")
    return render_template("panel.html")

@app.route("/panel/dashboard")
def dashboard():
    if not session.get('logged_in'):
        return redirect("/panel?error=unauthorized"), 303
    # Check session expiration (15 minutes inactivity)
    last_activity = session.get('last_activity')
    if last_activity and (datetime.utcnow() - datetime.fromisoformat(last_activity)) > timedelta(minutes=15):
        session.clear()
        return redirect("/panel?error=session_expired"), 303
    session['last_activity'] = datetime.utcnow().isoformat()
    clean_expired_keys()
    return render_template("dashboard.html", keys=KEYS, format_expiry=format_expiry)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/panel")

@app.route("/create_key", methods=["POST"])
def create_key():
    key, expiry = generate_key(request.remote_addr)
    return jsonify({"key": key, "expires_at": expiry})

@app.route("/delete_key", methods=["POST"])
def delete_key():
    key = request.json.get("key")
    if key in KEYS:
        del KEYS[key]
        for ip, k in USED_IPS.items():
            if k == key:
                del USED_IPS[ip]
                break
        return jsonify({"success": True})
    return jsonify({"error": "Key not found"}), 404

@app.route("/manage_key", methods=["POST"])
def manage_key():
    data = request.json
    key = data.get("key")
    days = data.get("days")

    if key in KEYS:
        expiry = datetime.utcnow() + timedelta(days=int(days))
        KEYS[key] = expiry.isoformat()  # Update the expiry date
        return jsonify({"success": True, "new_expiry": KEYS[key]})
    return jsonify({"error": "Key not found"}), 404

@app.route("/all_keys", methods=["GET"])
def all_keys():
    return jsonify(KEYS)

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)  # Key valid for 24 hours
    KEYS[key] = expires_at.isoformat()
    USED_IPS[ip] = key
    return key, expires_at.isoformat()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
