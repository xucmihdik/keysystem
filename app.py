from flask import Flask, request, jsonify, send_from_directory, redirect, Response, render_template
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public", template_folder="public")  # Specify template_folder
TOKENS = {}
KEYS = {}
USED_IPS = {}
SECRET_KEY = "p"
ADMIN_USERNAME = "admin"  # Set your admin username
ADMIN_PASSWORD = "password"  # Set your admin password
logged_in_users = set()  # Track logged-in users

# Helper
def get_device_id():
    ip = request.remote_addr
    user_agent = request.headers.get("User  -Agent", "")
    return ip + user_agent

def format_expiry(expiry):
    """Convert expiry string to a more readable format."""
    date = datetime.fromisoformat(expiry)
    return date.strftime("%B %d, %Y %I:%M %p")  # Example: July 22, 2025 08:36 AM

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    device_id = get_device_id()
    key = USED_IPS.get(device_id)
    if key:
        expiry_str = KEYS.get(key)
        if expiry_str:
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
        expiry = datetime.fromisoformat(KEYS.get(key, "1970-01-01T00:00:00"))
        if expiry <= datetime.utcnow():
            del KEYS[key]
            del USED_IPS[device_id]
            key, _ = generate_key(device_id)
    else:
        key, _ = generate_key(device_id)
    del TOKENS[token]
    return redirect(f"/?key={key}")

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    device_id = get_device_id()
    if secret != SECRET_KEY:
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

# ✅ PUBLIC loader endpoint — everyone gets gui.lua
@app.route("/loader")
def loader():
    if os.path.exists("gui.lua"):
        with open("gui.lua", "r", encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/plain")
    return "GUI not found", 404

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

# Panel Route
@app.route("/panel", methods=["GET"])
def panel():
    return render_template("panel.html", keys=KEYS, format_expiry=format_expiry)  # Pass the function to the template

@app.route("/logout")
def logout():
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

@app.route("/all_keys", methods=["GET"])
def all_keys():
    return jsonify(KEYS)

def generate_key(ip):
    key = f"clark-{uuid.uuid4().hex[:12]}"
    expires_at = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expires_at.isoformat()
    USED_IPS[ip] = key
    return key, expires_at.isoformat()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
