from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from keys import KEYS, USED_IPS, generate_key
import uuid, os, base64, hmac, hashlib, time

app = Flask(__name__, static_folder="public")

SECRET_KEY = "p"
TOKEN_SECRET = "clark_secret"
TOKEN_EXPIRY = 180  # token lasts 3 minutes

# Token generation and verification
def generate_token(ip):
    expires = int(time.time()) + TOKEN_EXPIRY
    data = f"{ip}:{expires}"
    sig = hmac.new(TOKEN_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{data}:{sig}".encode()).decode()
    return token

def verify_token(token, ip):
    try:
        decoded = base64.urlsafe_b64decode(token).decode()
        parts = decoded.split(":")
        if len(parts) != 3:
            return False
        token_ip, expires, sig = parts
        if token_ip != ip or int(expires) < int(time.time()):
            return False
        expected_sig = hmac.new(TOKEN_SECRET.encode(), f"{token_ip}:{expires}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, sig)
    except:
        return False

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/get_token")
def get_token():
    referrer = request.referrer or ""
    if "linkvertise" not in referrer.lower():
        return jsonify({ "error": "Invalid referrer" }), 403
    ip = request.remote_addr
    return jsonify({ "token": generate_token(ip) })

@app.route("/generate_key")
def generate_from_user():
    ip = request.remote_addr
    token = request.args.get("token")

    if not token or not verify_token(token, ip):
        return jsonify({ "error": "Unauthorized" }), 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({ "key": key, "expires_at": KEYS[key], "status": "already" })

    key, expiry = generate_key(ip)
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
    return jsonify({ "key": key, "expires_at": expiry.isoformat() })

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
