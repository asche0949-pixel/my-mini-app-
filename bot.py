import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8156108154:AAH_F6BwI4Y3S55LzYy6B3c8W1R8fN6Kz9o"
ADMIN_ID = "8556328355"

users_db = {}

def get_or_create_user(user_id):
    str_id = str(user_id)
    if str_id not in users_db:
        users_db[str_id] = {
            "balance": 100.0,
            "invites": 0,
            "streak": 0,
            "tasks_done": []
        }
    # አንተ ስትገባ ሁልጊዜ በቂ ሂሳብ (100 ETB) እንዲኖርህ ይደረጋል
    if str_id == ADMIN_ID and users_db[str_id]["balance"] < 60:
        users_db[str_id]["balance"] = 100.0

    return users_db[str_id]

@app.route("/")
def index():
    return "FulusApp Bot Server is running live!"

@app.route("/api/user", methods=["GET"])
def get_user():
    user_id = request.args.get("id")
    if not user_id:
        return jsonify({"error": "Missing user id"}), 400
    
    user_data = get_or_create_user(user_id)
    return jsonify(user_data)

@app.route("/api/check_channel", methods=["POST"])
def check_channel():
    data = request.json or {}
    user_id = data.get("user_id")
    channel = data.get("channel", "@PlusTechHub")
    
    if not user_id:
        return jsonify({"status": "error", "message": "Missing user id"}), 400

    user_data = get_or_create_user(user_id)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": channel, "user_id": user_id}
    
    try:
        res = requests.get(url, params=params).json()
        status = res.get("result", {}).get("status", "")
        
        if status in ["member", "administrator", "creator"]:
            if channel not in user_data["tasks_done"]:
                user_data["balance"] += 5.0
                user_data["tasks_done"].append(channel)
            return jsonify({"status": "joined", "balance": user_data["balance"]})
        else:
            return jsonify({"status": "not_joined"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    data = request.json or {}
    user_id = str(data.get("user_id", ""))
    amount = float(data.get("amount", 0))
    phone = data.get("phone", "")
    method = data.get("method", "Telebirr")

    if not user_id:
        return jsonify({"status": "error", "message": "የተጠቃሚ መለያ አልተገኘም!"}), 400

    user_data = get_or_create_user(user_id)

    # ለአድሚን ወይም ለሙከራ ሂሳብ ባይበቃ እንኳ ለሙከራ እንዲያልፍ ይደረጋል
    if user_data["balance"] < amount:
        user_data["balance"] = max(0.0, 100.0 - amount)
    else:
        user_data["balance"] -= amount

    # ለአንተ በቴሌግራም ማሳወቂያ መላክ
    msg = (
        f"🔔 *አዲስ የገንዘብ ማውጣት ጥያቄ!*\n\n"
        f"👤 *ተጠቃሚ ID:* `{user_id}`\n"
        f"💰 *የተጠየቀው መጠን:* {amount} ETB\n"
        f"💳 *የክፍያ ዘዴ:* {method}\n"
        f"📱 *ስልክ/አካውንት:* `{phone}`\n"
        f"💵 *ቀሪ ሂሳብ:* {user_data['balance']} ETB"
    )
    
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(send_url, json=payload)
    except Exception as e:
        print("Telegram send error:", e)

    return jsonify({"status": "success", "balance": user_data["balance"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
