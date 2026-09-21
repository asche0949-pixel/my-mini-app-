import os
import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8156108154:AAH_F6BwI4Y3S55LzYy6B3c8W1R8fN6Kz9o"
ADMIN_ID = "8556328355"
BOT_USERNAME = "Plus_appbot"
WEBAPP_URL = "https://asche0949-pixel.github.io/my-mini-app-/"

DATA_FILE = "database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}, "withdraw_requests": [], "invited_users": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_or_create_user(db, user_id):
    str_id = str(user_id)
    if str_id not in db["users"]:
        db["users"][str_id] = {
            "balance": 0.0,
            "invites": 0,
            "streak": 0,
            "last_checkin": 0,
            "tasks_done": []
        }
    return db["users"][str_id]

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Send message error: {e}")

@app.route("/")
def index():
    return "Plus App Backend is live!"

@app.route("/api/user", methods=["GET"])
def get_user():
    user_id = request.args.get("id", ADMIN_ID)
    db = load_data()
    user_data = get_or_create_user(db, user_id)
    save_data(db)
    
    now = time.time()
    can_checkin = (now - user_data.get("last_checkin", 0)) >= 86400
    
    res = dict(user_data)
    res["can_checkin"] = can_checkin
    return jsonify(res)

@app.route("/api/checkin", methods=["POST"])
def checkin():
    data = request.json or {}
    user_id = str(data.get("user_id", ADMIN_ID))
    db = load_data()
    user_data = get_or_create_user(db, user_id)

    now = time.time()
    last_check = user_data.get("last_checkin", 0)
    cooldown = 86400

    if now - last_check < cooldown:
        remaining_hours = int((cooldown - (now - last_check)) // 3600)
        remaining_minutes = int(((cooldown - (now - last_check)) % 3600) // 60)
        return jsonify({
            "status": "error",
            "message": f"የዛሬውን ወስደዋል! ከ {remaining_hours} ሰዓት ከ {remaining_minutes} ደቂቃ በኋላ ይሞክሩ።",
            "can_checkin": False
        }), 400

    user_data["balance"] += 60.0
    user_data["streak"] = user_data.get("streak", 0) + 1
    user_data["last_checkin"] = now
    save_data(db)

    return jsonify({
        "status": "success",
        "balance": user_data["balance"],
        "streak": user_data["streak"],
        "can_checkin": False
    })

@app.route("/api/check_channel", methods=["POST"])
def check_channel():
    data = request.json or {}
    user_id = data.get("user_id")
    channel = data.get("channel", "@PlusTechHub")
    db = load_data()
    user_data = get_or_create_user(db, user_id)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": channel, "user_id": user_id}, timeout=5).json()
        status = res.get("result", {}).get("status", "")
        if status in ["member", "administrator", "creator"]:
            if channel not in user_data["tasks_done"]:
                user_data["balance"] += 5.0
                user_data["tasks_done"].append(channel)
                save_data(db)
            return jsonify({"status": "joined", "balance": user_data["balance"]})
    except:
        pass
    return jsonify({"status": "not_joined"})

@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    data = request.json or {}
    user_id = str(data.get("user_id", ADMIN_ID))
    amount = float(data.get("amount", 0))
    phone = data.get("phone", "")
    method = data.get("method", "Telebirr")

    db = load_data()
    user_data = get_or_create_user(db, user_id)
    user_data["balance"] = max(0.0, user_data["balance"] - amount)

    req_id = int(time.time() * 1000)
    req_item = {
        "id": req_id,
        "user_id": user_id,
        "amount": amount,
        "phone": phone,
        "method": method,
        "status": "Pending",
        "date": time.strftime("%Y-%m-%d %H:%M")
    }
    db["withdraw_requests"].append(req_item)
    save_data(db)

    # ለአድሚን በቴሌግራም መላክ
    msg = (
        f"🔔 *አዲስ የገንዘብ ማውጣት ጥያቄ!*\n\n"
        f"👤 *ተጠቃሚ ID:* `{user_id}`\n"
        f"💰 *መጠን:* {amount} ETB\n"
        f"💳 *ዘዴ:* {method}\n"
        f"📱 *ስልክ:* `{phone}`"
    )
    send_telegram_message(ADMIN_ID, msg)

    return jsonify({"status": "success", "balance": user_data["balance"], "request": req_item})

@app.route("/api/user/history", methods=["GET"])
def get_user_history():
    user_id = str(request.args.get("user_id", ADMIN_ID))
    db = load_data()
    history = [r for r in db["withdraw_requests"] if str(r["user_id"]) == user_id]
    return jsonify(history)

@app.route("/api/admin/requests", methods=["GET"])
def get_admin_requests():
    db = load_data()
    return jsonify(db["withdraw_requests"])

@app.route("/api/admin/approve", methods=["POST"])
def approve_request():
    data = request.json or {}
    req_id = data.get("req_id")
    db = load_data()
    for r in db["withdraw_requests"]:
        if str(r["id"]) == str(req_id):
            r["status"] = "Success"
            user_msg = f"🎉 *እንኳን ደስ አለዎት!*\nየጠየቁት {r['amount']} ETB በተሳካ ሁኔታ ተልኮልዎታል!"
            send_telegram_message(r["user_id"], user_msg)
            save_data(db)
            break
    return jsonify({"status": "success"})

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}
    if "message" in update:
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")

        if text.startswith("/start"):
            db = load_data()
            get_or_create_user(db, chat_id)
            parts = text.split()

            if len(parts) > 1 and parts[1].startswith("ref_"):
                referrer_id = parts[1].replace("ref_", "").strip()
                if referrer_id != chat_id and chat_id not in db["invited_users"]:
                    db["invited_users"].append(chat_id)
                    referrer = get_or_create_user(db, referrer_id)
                    referrer["balance"] += 3.0
                    referrer["invites"] = referrer.get("invites", 0) + 1

                    ref_notify = (
                        f"🎉 *አዲስ ሰው ተቀላቅሏል!*\n\n"
                        f"👤 አንድ ተጠቃሚ በእርስዎ ሊንክ ተቀላቅሏል።\n"
                        f"💰 *+3.00 ETB* ወደ ሂሳብዎ ገብቷል!\n"
                        f"💵 ጠቅላላ ሂሳብዎ: {referrer['balance']:.2f} ETB"
                    )
                    send_telegram_message(referrer_id, ref_notify)

            save_data(db)

            welcome_text = (
                f"👋 *እንኳን ወደ Plus App በደህና መጡ!*\n\n"
                f"በየቀኑ Check-in በማድረግ፣ ተግባራትን በማጠናቀቅ እና ሰዎችን በመጋበዝ ገንዘብ ያግኙ!\n\n"
                f"ለመጀመር ከታች ያለውን *«Open App»* በተን ይጫኑ።"
            )
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🚀 Open App", "web_app": {"url": WEBAPP_URL}}],
                    [{"text": "📢 ቻናላችን", "url": "https://t.me/PlusTechHub"}]
                ]
            }
            send_telegram_message(chat_id, welcome_text, keyboard)

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
