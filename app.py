from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from keys import KEYS, generate_key  # ✅ External keys logic
import os

app = Flask(__name__, static_folder='public')

# Track which IPs have already generated a key
USED_IPS = set()

# Serve the main HTML interface
@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

# Generate a key if coming from Linkvertise and not already used
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

# Validate the key
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

# Serve other static files like styles, images, etc.
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('public', path)

# Run the app (Render/Replit-compatible)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
