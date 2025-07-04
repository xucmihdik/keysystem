from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
from dateutil.parser import parse as parse_date
import uuid
import os

app = Flask(__name__, static_folder='public')

# In-memory key storage and IP tracker
KEYS = {}
USED_IPS = set()

# Function to generate a key
def generate_key():
    key = f"clark-{uuid.uuid4().hex[:10]}"
    expires_at = datetime.utcnow().isoformat()
    KEYS[key] = expires_at
    return key, expires_at

# Serve index.html
@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

# Route for generating a key (only once per IP and with ref check)
@app.route('/generate_key')
def generate():
    ip = request.remote_addr
    ref = request.args.get("ref")

    if ref != "linkvertise":
        return jsonify({"error": "You must come from Linkvertise."}), 403

    if ip in USED_IPS:
        return jsonify({"error": "You already generated a key."}), 403

    key, expires_at = generate_key()
    USED_IPS.add(ip)
    return jsonify({"key": key, "expires_at": expires_at})

# Route for validating a key
@app.route('/validate_key')
def validate():
    key = request.args.get('key')
    if not key:
        return jsonify({"valid": False, "error": "No key provided"}), 400

    expiry = KEYS.get(key)
    if not expiry:
        return jsonify({"valid": False, "error": "Invalid key"})

    expiry_dt = parse_date(expiry)
    if datetime.utcnow() > expiry_dt + timedelta(hours=24):
        return jsonify({"valid": False, "error": "Key expired"})

    return jsonify({"valid": True})

# Serve other static files (CSS, images, etc.)
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('public', path)

# Required by Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
