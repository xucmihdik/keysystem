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
main.Size = UDim2.new(0, 0, 0, 0)
main.BackgroundColor3 = Color3.fromRGB(10, 10, 10)
main.BorderSizePixel = 0
main.BackgroundTransparency = 0
main.Parent = gui

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
				["Content-Type"] = "application/json",
				["X-Secret"] = "123pogiako"
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
