from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect
from keys import KEYS, USED_IPS, generate_key
from datetime import datetime, timedelta
import uuid
import os

app = Flask(__name__, static_folder="public")

TOKENS = {}
SECRET_KEY = "p"  # You can change this to a secure string
TOKEN_TIMEOUT = 300  # 5 minutes in seconds

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
    ip = request.remote_addr
    token = uuid.uuid4().hex[:24]
    TOKENS[token] = {
        "ip": ip,
        "created_at": datetime.utcnow()
    }
    return redirect(f"/claim?token={token}")

@app.route("/claim")
def claim():
    token = request.args.get("token")
    ip = request.remote_addr

    token_data = TOKENS.get(token)

    if not token_data:
        return "❌ Invalid token", 403

    if token_data["ip"] != ip:
        return "❌ Token IP mismatch", 403

    if datetime.utcnow() - token_data["created_at"] > timedelta(seconds=TOKEN_TIMEOUT):
        del TOKENS[token]
        return "❌ Token expired", 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
    else:
        key, _ = generate_key(ip)

    del TOKENS[token]

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Key Claimed</title>
        <style>
            body {
                font-family: sans-serif;
                background: #111;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                flex-direction: column;
            }
            .key {
                background: white;
                color: black;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 1.2rem;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <h2>✅ Key Claimed Successfully!</h2>
        <div class="key">{{ key }}</div>
        <p>⏳ Valid for 24 hours</p>
    </body>
    </html>
    """, key=key)

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    ip = request.remote_addr
    if secret != SECRET_KEY:
        return jsonify({ "error": "Unauthorized" }), 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
    else:
        key, _ = generate_key(ip)

    return jsonify({ "key": key, "expires_at": KEYS[key], "status": "owner" })

@app.route("/validate_key")
def validate_key():
    key = request.args.get("key")
    if key in KEYS and datetime.fromisoformat(KEYS[key]) > datetime.utcnow():
        return jsonify({ "valid": True, "expires_at": KEYS[key] })
    return jsonify({ "valid": False }), 404

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
