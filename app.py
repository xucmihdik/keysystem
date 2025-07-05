from flask import Flask, request, jsonify, send_from_directory, render_template_string, redirect
from keys import KEYS, USED_IPS, generate_key
from datetime import datetime
import uuid
import os

app = Flask(__name__, static_folder="public")

TOKENS = {}
SECRET_KEY = "p"

@app.route("/")
def home():
    return send_from_directory("public", "index.html")

@app.route("/check_key_status")
def check_key_status():
    ip = request.remote_addr
    if ip in USED_IPS:
        key = USED_IPS[ip]
        return jsonify({"has_key": True, "key": key, "expires_at": KEYS[key]})
    return jsonify({"has_key": False})

@app.route("/get_token")
def get_token():
    referer = request.headers.get("Referer", "")
    if "linkvertise.com" not in referer.lower():
        return "❌ Access denied. Please complete Linkvertise first.", 403

    ip = request.remote_addr
    token = uuid.uuid4().hex[:24]
    TOKENS[token] = ip
    return redirect(f"/claim?token={token}")

@app.route("/claim")
def claim():
    token = request.args.get("token")
    ip = request.remote_addr

    if not token or token not in TOKENS or TOKENS[token] != ip:
        return "Invalid token or IP mismatch", 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
    else:
        key, _ = generate_key(ip)

    del TOKENS[token]

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Key Claimed</title>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body {
          height: 100%; width: 100%;
          font-family: 'Segoe UI', sans-serif;
          background: linear-gradient(135deg, #000, #fff);
          display: flex; align-items: center; justify-content: center;
          overflow: hidden; position: relative;
        }
        .bubble {
          position: absolute;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.08);
          animation: floatUp 20s linear infinite;
        }
        @keyframes floatUp {
          0% { transform: translateY(0) scale(0.5); opacity: 0.3; }
          100% { transform: translateY(-120vh) scale(1.2); opacity: 0; }
        }
        .container {
          z-index: 2;
          background: rgba(0, 0, 0, 0.85);
          border: 2px solid #fff;
          border-radius: 16px;
          padding: 24px 20px;
          width: 90%;
          max-width: 400px;
          text-align: center;
          box-shadow: 0 0 25px rgba(0, 0, 0, 0.6);
          animation: fadeIn 0.5s ease;
        }
        h1 {
          font-size: 1.6rem;
          margin-bottom: 16px;
          color: #fff;
        }
        .key-box {
          background: #fff;
          color: #111;
          border-radius: 10px;
          padding: 12px 16px;
          margin: 20px 0;
          display: inline-flex;
          align-items: center;
          gap: 10px;
          font-weight: bold;
          word-break: break-word;
        }
        .copy-icon {
          width: 22px;
          height: 22px;
          cursor: pointer;
        }
        p {
          color: #ccc;
        }
        .notification {
          position: fixed;
          top: 20px;
          right: 20px;
          background: #111;
          padding: 10px 16px;
          color: #fff;
          border-radius: 8px;
          font-size: 0.95rem;
          box-shadow: 0 0 10px rgba(0, 0, 0, 0.4);
          z-index: 99;
          animation: fadeInNotif 0.3s forwards;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInNotif {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      </style>
    </head>
    <body>
      <!-- Bubbles -->
      <div class="bubble" style="width: 60px; height: 60px; left: 5%; top: 100vh; animation-delay: 0s;"></div>
      <div class="bubble" style="width: 100px; height: 100px; left: 25%; top: 100vh; animation-delay: 4s;"></div>
      <div class="bubble" style="width: 80px; height: 80px; left: 50%; top: 100vh; animation-delay: 2s;"></div>
      <div class="bubble" style="width: 70px; height: 70px; left: 70%; top: 100vh; animation-delay: 6s;"></div>
      <div class="bubble" style="width: 90px; height: 90px; left: 85%; top: 100vh; animation-delay: 1.5s;"></div>

      <div class="container">
        <h1>✅ Key Claimed Successfully!</h1>
        <div class="key-box">
          <span id="key">clark-{{ key.replace('clark-', '') }}</span>
          <img src="https://files.catbox.moe/qnfp07.png"
               alt="Copy" class="copy-icon" onclick="copyKey()">
        </div>
        <p>⏳ Valid for 24 hours</p>
      </div>

      <script>
        function copyKey() {
          const keyText = document.getElementById("key").textContent;
          navigator.clipboard.writeText(keyText)
            .then(() => showNotification("✅ Key copied to clipboard!"))
            .catch(() => showNotification("❌ Failed to copy key."));
        }

        function showNotification(text) {
          const notif = document.createElement("div");
          notif.className = "notification";
          notif.textContent = text;
          document.body.appendChild(notif);
          setTimeout(() => notif.remove(), 3000);
        }
      </script>
    </body>
    </html>
    """, key=key)

@app.route("/owner_generate")
def owner_generate():
    secret = request.args.get("secret")
    ip = request.remote_addr

    if secret != SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    if ip in USED_IPS:
        key = USED_IPS[ip]
    else:
        key, _ = generate_key(ip)

    return jsonify({"key": key, "expires_at": KEYS[key], "status": "owner"})

@app.route("/validate_key")
def validate_key():
    key = request.args.get("key")
    if key in KEYS and datetime.fromisoformat(KEYS[key]) > datetime.utcnow():
        return jsonify({"valid": True, "expires_at": KEYS[key]})
    return jsonify({"valid": False}), 404

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
