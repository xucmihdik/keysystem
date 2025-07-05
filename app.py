from flask import Flask, request, jsonify, send_from_directory
from keys import KEYS, USED_IPS, generate_key
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public")

ALLOWED_REF = "https://link-hub.net/1367787/WmEGaMKAKlRJ"
TOKENS = {}
SECRET_KEY = "p"  # Change this to something secret and long

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    ip = request.remote_addr
    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({ "has_key": True, "key": key, "expires_at": KEYS[key] })
    return jsonify({ "has_key": False })

@app.route("/get_token")
def get_token():
    referer = request.headers.get("Referer", "")
    if referer.startswith(ALLOWED_REF):
        token = uuid.uuid4().hex[:24]
        TOKENS[token] = request.remote_addr
        return jsonify({ "token": token })
    return jsonify({ "error": "Invalid referrer" }), 403

@app.route("/generate_key")
def gen_key():
    token = request.args.get("token")
    ip = request.remote_addr

    if not token or token not in TOKENS:
        return jsonify({ "error": "Invalid or missing token" }), 403
    if TOKENS[token] != ip:
        return jsonify({ "error": "Token doesn't match your IP" }), 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({ "key": key, "expires_at": KEYS[key], "status": "already" })

    key, expiry = generate_key(ip)
    del TOKENS[token]
    return jsonify({ "key": key, "expires_at": expiry, "status": "new" })

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    ip = request.remote_addr

    if secret != SECRET_KEY:
        return jsonify({ "error": "Unauthorized" }), 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({ "key": key, "expires_at": KEYS[key], "status": "already" })

    key, expiry = generate_key(ip)
    return jsonify({ "key": key, "expires_at": expiry, "status": "new" })

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

# Render-compatible entry point
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
