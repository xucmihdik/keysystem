from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from keys import KEYS, USED_IPS, generate_key, save_data
import uuid
import os

app = Flask(__name__, static_folder="public")

SECRET_KEY = "p"
ALLOWED_REF = "https://link-hub.net/1367787/WmEGaMKAKlRJ"
TOKENS = {}

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/get_token")
def get_token():
    ref = request.referrer or ""
    if not ref.startswith(ALLOWED_REF):
        return jsonify({ "error": "Access denied" }), 403

    ip = request.remote_addr
    token = uuid.uuid4().hex[:24]
    TOKENS[ip] = token
    return jsonify({ "token": token })

@app.route("/generate_key")
def generate_from_token():
    ip = request.remote_addr
    token = request.args.get("token")

    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({ "key": key, "expires_at": KEYS[key], "status": "already" })

    if not token or TOKENS.get(ip) != token:
        return jsonify({ "error": "Invalid or missing token" }), 403

    key, expiry = generate_key(ip)
    save_data()
    return jsonify({ "key": key, "expires_at": expiry, "status": "new" })

@app.route("/check_key_status")
def check_key_status():
    ip = request.remote_addr
    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({
            "has_key": True,
            "key": key,
            "expires_at": KEYS[key]
        })
    return jsonify({ "has_key": False })

@app.route("/validate_key")
def validate_key():
    key = request.args.get("key")
    if not key or key not in KEYS:
        return jsonify({ "valid": False, "error": "Invalid key" })
    expiry = datetime.fromisoformat(KEYS[key])
    if datetime.utcnow() > expiry:
        return jsonify({ "valid": False, "error": "Key expired" })
    return jsonify({ "valid": True })

@app.route("/owner_generate")
def owner_generate():
    if request.args.get("secret") != SECRET_KEY:
        return jsonify({ "error": "Unauthorized" }), 403
    key = f"clark-{uuid.uuid4().hex[:10]}"
    expiry = datetime.utcnow() + timedelta(hours=24)
    KEYS[key] = expiry.isoformat()
    USED_IPS["owner-manual"] = key
    save_data()
    return jsonify({ "key": key, "expires_at": expiry.isoformat(), "status": "owner" })

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
