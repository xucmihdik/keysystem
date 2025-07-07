from flask import Flask, request, jsonify, send_from_directory, redirect, Response
from keys import KEYS, USED_IPS, generate_key
from datetime import datetime
import uuid
import os

app = Flask(__name__, static_folder="public")
TOKENS = {}
SECRET_KEY = "p"
LOADER_SECRET = "123pogiako"

def get_device_id():
    ip = request.remote_addr or "0.0.0.0"
    user_agent = request.headers.get("User-Agent", "")
    return ip + user_agent

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    device_id = get_device_id()
    if device_id in USED_IPS:
        key = USED_IPS[device_id]
        return jsonify({"has_key": True, "key": key, "expires_at": KEYS[key]})
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
    user_agent = request.headers.get("User-Agent", "").lower()
    forwarded = request.headers.get("X-Forwarded-For", "")
    origin = request.headers.get("Origin", "")
    referer = request.headers.get("Referer", "")

    browser_keywords = ["mozilla", "chrome", "safari", "firefox", "edge", "curl", "wget", "postman", "python"]
    executor_keywords = ["synapse", "krnl", "delta", "fluxus", "scriptware", "electron", "roblox"]

    if any(b in user_agent for b in browser_keywords):
        return "Access Denied (Browser)", 403
    if forwarded or origin or referer:
        return "Access Denied (Headers)", 403
    if user_agent == "" or any(e in user_agent for e in executor_keywords):
        try:
            with open("gui.lua", "r") as f:
                lua_code = f.read()
            return Response(lua_code, mimetype="text/plain")
        except FileNotFoundError:
            return "gui.lua not found", 500
    return "Access Denied (Unknown Executor)", 403

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
