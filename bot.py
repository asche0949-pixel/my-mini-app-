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
    return users_db[str_id]

@app.route("/")
def index():
    return "FulusApp Bot Server is running live!"

@app.route("/api/user", methods=["GET"])
def get_user():
    user_id = request.args.get("id", ADMIN_ID)
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
    user_id = str(data.get("user_id", ADMIN_ID))
    amount = float(data.get("amount", 0))
    phone = data.get("phone", "")
    method = data.get("method", "Telebirr")

    user_data = get_or_create_user(user_id)
    user_data["balance"] = max(0.0, user_data["balance"] - amount)

    # ለአድሚን የሚላከው መልእክት ከነ Approve እና Reject በተኖች ጋር
    msg = (
        f"🔔 *አዲስ የገንዘብ ማውጣት ጥያቄ!*\n\n"
        f"👤 *ተጠቃሚ ID:* `{user_id}`\n"
        f"💰 *የተጠየቀው መጠን:* {amount} ETB\n"
        f"💳 *የክፍያ ዘዴ:* {method}\n"
        f"📱 *ስልክ/አካውንት:* `{phone}`\n"
        f"💵 *ቀሪ ሂሳብ:* {user_data['balance']} ETB"
    )

    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve (ክፈል)", "callback_data": f"app_{user_id}_{amount}"},
                {"text": "❌ Reject (ሰርዝ)", "callback_data": f"rej_{user_id}_{amount}"}
            ]
        ]
    }
    
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": inline_keyboard
    }
    try:
        requests.post(send_url, json=payload)
    except Exception as e:
        print("Telegram send error:", e)

    return jsonify({"status": "success", "balance": user_data["balance"]})

# ቴሌግራም ላይ አድሚኑ Approve ወይም Reject ሲጫን የሚሰራ
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}
    
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq["id"]
        from_id = str(cq["from"]["id"])
        data = cq.get("data", "")
        msg_id = cq["message"]["message_id"]
        chat_id = cq["message"]["chat"]["id"]

        # አድሚኑ ብቻ ነው መጫን የሚችለው
        if from_id == ADMIN_ID:
            if data.startswith("app_"):
                parts = data.split("_")
                target_user = parts[1]
                target_amt = parts[2]
                
                # ለተጠቃሚው ማሳወቅ
                user_msg = f"🎉 *እንኳን ደስ አለዎት!*\nየጠየቁት {target_amt} ETB በተሳካ ሁኔታ ተልኮልዎታል!"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": target_user,
                    "text": user_msg,
                    "parse_mode": "Markdown"
                })

                # የአድሚኑን መልእክት ማስተካከል
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": cq["message"]["text"] + "\n\n✅ *ተከፍሏል (Approved)*",
                    "parse_mode": "Markdown"
                })

            elif data.startswith("rej_"):
                parts = data.split("_")
                target_user = parts[1]
                target_amt = float(parts[2])

                # የተሰረዘውን ብር ለተጠቃሚው መመለስ
                u_data = get_or_create_user(target_user)
                u_data["balance"] += target_amt

                # ለተጠቃሚው ማሳወቅ
                user_msg = f"⚠️ የጠየቁት {target_amt} ETB የማውጣት ጥያቄ ተሰርዟል፤ ብሩ ወደ ሂሳብዎ ተመልሷል።"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                    "chat_id": target_user,
                    "text": user_msg,
                    "parse_mode": "Markdown"
                })

                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": msg_id,
                    "text": cq["message"]["text"] + "\n\n❌ *ተሰርዟል (Rejected)*",
                    "parse_mode": "Markdown"
                })

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq_id})

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
