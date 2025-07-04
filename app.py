from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from dateutil.parser import parse as parse_date
from keys import KEYS, generate_key
import os

app = Flask(__name__, static_folder='public')

USED_IPS = {}
OWNER_SECRET = "p"  # your owner token

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/generate_key')
def generate():
    ip = request.remote_addr
    ref = request.args.get("ref")

    if ref != "linkvertise":
        return jsonify({"error": "You must come from Linkvertise."}), 403

    if ip in USED_IPS:
        existing_key = USED_IPS[ip]
        expiry = KEYS.get(existing_key)
        return jsonify({
            "key": existing_key,
            "expires_at": expiry,
            "status": "already"
        })

    key, expires_at = generate_key()
    USED_IPS[ip] = key

    return jsonify({"key": key, "expires_at": expires_at, "status": "new"})

@app.route('/owner_generate')
def owner_generate():
    token = request.args.get("token")

    if token != OWNER_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    key, expires_at = generate_key()
    return jsonify({"key": key, "expires_at": expires_at})

@app.route('/validate_key')
def validate():
    key = request.args.get('key')

    if not key:
        return jsonify({"valid": False, "error": "No key provided"}), 400

    expiry = KEYS.get(key)
    if not expiry:
        return jsonify({"valid": False, "error": "Invalid key"})

    expiry_time = parse_date(expiry)
    if datetime.utcnow() > expiry_time:
        return jsonify({"valid": False, "error": "Key expired"})

    return jsonify({"valid": True})

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('public', path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
