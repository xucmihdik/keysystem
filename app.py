from flask import Flask, request, jsonify, send_from_directory, redirect, Response
from keys import KEYS, USED_IPS, generate_key
from datetime import datetime
import uuid
import os

app = Flask(__name__, static_folder="public")
TOKENS = {}
SECRET_KEY = "p"

def get_device_id():
    ip = request.remote_addr
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
    forwarded = request.headers.get("X-Forwarded-For")
    referer = request.headers.get("Referer", "")
    origin = request.headers.get("Origin", "")

    block_keywords = ["mozilla", "chrome", "safari", "curl", "postman", "python", "wget"]
    if any(k in user_agent for k in block_keywords):
        return "Access denied (UA)", 403
    if forwarded:
        return "Access denied (Proxy Detected)", 403
    if referer or origin:
        return "Access denied (Referrer/Origin set)", 403

    # LUA GUI PAYLOAD (SERVED TO LOADSTRING)
    lua_gui = '''-- Clark KeySystem GUI
local HttpService = game:GetService("HttpService")
local TweenService = game:GetService("TweenService")
local request = (syn and syn.request) or (http and http.request) or (http_request) or request
if not request then return warn("❌ Your executor does not support HTTP requests.") end

local gui = Instance.new("ScreenGui")
gui.Name = "ClarkKeySystem"
gui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
gui.ResetOnSpawn = false
gui.IgnoreGuiInset = true
gui.Parent = game:GetService("CoreGui")

local main = Instance.new("Frame")
main.AnchorPoint = Vector2.new(0.5, 0.5)
main.Position = UDim2.new(0.5, 0, 0.5, 0)
main.Size = UDim2.new(0, 300, 0, 200)
main.BackgroundColor3 = Color3.fromRGB(10, 10, 10)
main.BorderSizePixel = 0
main.BackgroundTransparency = 0
main.Parent = gui
main.Size = UDim2.new(0, 0, 0, 0)

Instance.new("UICorner", main).CornerRadius = UDim.new(0, 12)
local stroke = Instance.new("UIStroke", main)
stroke.Color = Color3.fromRGB(255, 255, 255)
stroke.Thickness = 2

local title = Instance.new("TextLabel", main)
title.Text = "Clark KeySystem"
title.Font = Enum.Font.GothamBold
title.TextSize = 20
title.TextColor3 = Color3.fromRGB(255, 255, 255)
title.Size = UDim2.new(1, 0, 0, 40)
title.Position = UDim2.new(0, 0, 0, 10)
title.BackgroundTransparency = 1

local input = Instance.new("TextBox", main)
input.PlaceholderText = "Enter your key here"
input.Text = ""
input.Size = UDim2.new(0.85, 0, 0, 32)
input.Position = UDim2.new(0.075, 0, 0.38, 0)
input.Font = Enum.Font.Gotham
input.TextSize = 16
input.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
input.TextColor3 = Color3.fromRGB(0, 0, 0)
input.BorderSizePixel = 0
Instance.new("UICorner", input).CornerRadius = UDim.new(0, 8)

local getBtn = Instance.new("TextButton", main)
getBtn.Text = "📋 Get Key"
getBtn.Size = UDim2.new(0.42, 0, 0, 32)
getBtn.Position = UDim2.new(0.06, 0, 0.72, 0)
getBtn.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
getBtn.TextColor3 = Color3.fromRGB(0, 0, 0)
getBtn.Font = Enum.Font.Gotham
getBtn.TextSize = 15
Instance.new("UICorner", getBtn).CornerRadius = UDim.new(0, 8)

local checkBtn = Instance.new("TextButton", main)
checkBtn.Text = "✅ Check Key"
checkBtn.Size = UDim2.new(0.42, 0, 0, 32)
checkBtn.Position = UDim2.new(0.52, 0, 0.72, 0)
checkBtn.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
checkBtn.TextColor3 = Color3.fromRGB(0, 0, 0)
checkBtn.Font = Enum.Font.Gotham
checkBtn.TextSize = 15
Instance.new("UICorner", checkBtn).CornerRadius = UDim.new(0, 8)

TweenService:Create(main, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.Out), {
	Size = UDim2.new(0, 300, 0, 200)
}):Play()

local function notify(text)
	local notif = Instance.new("TextLabel", gui)
	notif.Size = UDim2.new(0, 260, 0, 28)
	notif.AnchorPoint = Vector2.new(1, 0)
	notif.Position = UDim2.new(1, -10, 0, 10)
	notif.BackgroundColor3 = Color3.fromRGB(255, 255, 255)
	notif.TextColor3 = Color3.fromRGB(0, 0, 0)
	notif.Text = text
	notif.TextSize = 14
	notif.Font = Enum.Font.GothamSemibold
	notif.BackgroundTransparency = 1
	notif.ZIndex = 999
	Instance.new("UICorner", notif).CornerRadius = UDim.new(0, 6)
	TweenService:Create(notif, TweenInfo.new(0.25), { BackgroundTransparency = 0 }):Play()
	task.wait(2.3)
	TweenService:Create(notif, TweenInfo.new(0.3), { BackgroundTransparency = 1 }):Play()
	task.wait(0.3)
	notif:Destroy()
end

local function exitGUI()
	local shrink = TweenService:Create(main, TweenInfo.new(0.3, Enum.EasingStyle.Back, Enum.EasingDirection.In), {
		Size = UDim2.new(0, 0, 0, 0),
		Position = UDim2.new(0.5, 0, 0.55, 0)
	})
	shrink:Play()
	shrink.Completed:Wait()
	gui:Destroy()
end

local function validateKey()
	local key = input.Text
	if key == "" then return notify("⚠️ Please enter a key.") end
	notify("🔎 Checking key...")
	local success, res = pcall(function()
		return request({
			Url = "https://clark-keysystem.onrender.com/validate_key?key=" .. key,
			Method = "GET",
			Headers = {
				["Content-Type"] = "application/json"
			}
		})
	end)
	if not success or not res then
		return notify("❌ Request failed.")
	end
	local good, data = pcall(function()
		return HttpService:JSONDecode(res.Body)
	end)
	if good and data.valid then
		notify("✅ Key is valid! Welcome.")
		exitGUI()
	else
		notify("❌ Invalid or expired key.")
	end
end

getBtn.MouseButton1Click:Connect(function()
	setclipboard("https://clark-keysystem.onrender.com")
	notify("🔗 Key link copied to clipboard!")
end)
checkBtn.MouseButton1Click:Connect(validateKey)
'''

    return Response(lua_gui, mimetype="text/plain")

@app.route("/<path:path>")
def static_file(path):
    return send_from_directory("public", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
