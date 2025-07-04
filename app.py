from flask import Flask, jsonify, request, send_from_directory
from keys import KEYS, generate_key
from datetime import datetime

app = Flask(__name__, static_folder='public')

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/generate_key')
def generate():
    key, expires_at = generate_key()
    return jsonify({"key": key, "expires_at": expires_at})

@app.route('/validate_key')
def validate():
    key = request.args.get('key')
    if not key:
        return jsonify({"valid": False, "error": "No key provided"}), 400

    if key in KEYS:
        expiry = KEYS[key]
        if datetime.utcnow() < expiry:
            return jsonify({"valid": True})
        else:
            return jsonify({"valid": False, "error": "Key expired"})
    else:
        return jsonify({"valid": False, "error": "Invalid key"})

# Optional: catch-all for static files in /public
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('public', path)

if __name__ == '__main__':
    app.run(debug=True)
