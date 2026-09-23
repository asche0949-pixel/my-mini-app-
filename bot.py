import os
import json
import time
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8856484714:AAHvdyso7kjUSTEw4qKqVbQhUU31H51I7pE"
ADMIN_ID = "8556328355"
BOT_USERNAME = "Plus_appbot"
WEBAPP_URL = "https://asche0949-pixel.github.io/my-mini-app-/"

DATA_FILE = "database.json"
CHANNELS = ["@PlusTechHub", "@Eth_online_job", "@Alphatech_earn"]

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
            "verified": False,
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
        print(f"Send error: {e}")

def check_member(channel, user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": channel, "user_id": user_id}, timeout=5).json()
        status = res.get("result", {}).get("status", "")
        return status in ["member", "administrator", "creator"]
    except Exception:
        return True

@app.route("/")
def index():
    return "Plus App Backend is live and running!"

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

@app.route("/api/verify_membership", methods=["POST"])
def verify_membership():
    data = request.json or {}
    user_id = str(data.get("user_id", ADMIN_ID))
    referrer_id = str(data.get("referrer_id", "")).strip()

    db = load_data()
    user_data = get_or_create_user(db, user_id)

    missing = []
    for ch in CHANNELS:
        if not check_member(ch, user_id):
            missing.append(ch)

    if missing:
        return jsonify({
            "status": "not_joined",
            "message": f"እባክዎ መጀመሪያ የቀሩትን ቻናሎች ይቀላቀሉ፦ {', '.join(missing)}",
            "verified": False
        })

    if referrer_id and referrer_id != user_id and user_id not in db["invited_users"]:
        db["invited_users"].append(user_id)
        ref_user = get_or_create_user(db, referrer_id)
        ref_user["balance"] += 4.0
        ref_user["invites"] = ref_user.get("invites", 0) + 1

        ref_msg = (
            f"🎉 *እንኳን ደስ አለዎት!*\n\n"
            f"👤 አዲስ ተጠቃሚ በእርስዎ ሊንክ ተቀላቅሏል!\n"
            f"💰 *+4.00 ETB* ወደ ሂሳብዎ ተጨምሯል!\n"
            f"💵 ጠቅላላ ሂሳብዎ: {ref_user['balance']:.2f} ETB"
        )
        send_telegram_message(referrer_id, ref_msg)

    user_data["verified"] = True
    save_data(db)

    return jsonify({"status": "verified", "verified": True, "balance": user_data["balance"]})

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

    user_data["balance"] += 3.0
    user_data["streak"] = (user_data.get("streak", 0) % 7) + 1
    user_data["last_checkin"] = now
    save_data(db)

    return jsonify({
        "status": "success",
        "balance": user_data["balance"],
        "streak": user_data["streak"],
        "can_checkin": False
    })

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

# Webhook ሳይፈልግ ቦቱ በራሱ መልእክቶችን ተቀብሎ የሚመልስበት Polling
def bot_polling_loop():
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=5)
    except Exception:
        pass

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": offset, "timeout": 20}, timeout=25).json()
            if res.get("ok"):
                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        text = msg.get("text", "")

                        if text.startswith("/start"):
                            welcome_text = (
                                f"👋 *እንኳን ወደ Plus App በደህና መጡ!*\n\n"
                                f"በየቀኑ Check-in በማድረግ እና ጓደኞችዎን በመጋበዝ ገንዘብ ያግኙ!\n\n"
                                f"⚠️ ወደ ሚኒ አፑ ከመግባትዎ በፊት ቻናሎቹን ይቀላቀሉ፦\n"
                                f"1. @PlusTechHub\n"
                                f"2. @Eth_online_job\n"
                                f"3. @Alphatech_earn\n\n"
                                f"ከዚያ ከታች ያለውን *«🚀 Open App»* ይጫኑ!"
                            )
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🚀 Open App", "url": f"https://t.me/{BOT_USERNAME}/app"}],
                                    [{"text": "📢 ቻናል 1", "url": "https://t.me/PlusTechHub"}, {"text": "📢 ቻናል 2", "url": "https://t.me/Eth_online_job"}],
                                    [{"text": "📢 ቻናል 3", "url": "https://t.me/Alphatech_earn"}]
                                ]
                            }
                            send_telegram_message(chat_id, welcome_text, keyboard)
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    t = threading.Thread(target=bot_polling_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
