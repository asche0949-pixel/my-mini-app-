import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8156108154:AAH_F6BwI4Y3S55LzYy6B3c8W1R8fN6Kz9o"
ADMIN_ID = "8556328355"
WEBAPP_URL = "https://asche0949-pixel.github.io/my-mini-app-/"

users_db = {}
withdraw_requests = []
invited_users = set()  # የተጋበዙ ሰዎችን ለመመዝገብ (ደጋግመው እንዳይገቡ)

def get_or_create_user(user_id):
    str_id = str(user_id)
    if str_id not in users_db:
        users_db[str_id] = {
            "balance": 0.0,
            "invites": 0,
            "streak": 0,
            "tasks_done": []
        }
    return users_db[str_id]

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Send message error: {e}")

@app.route("/")
def index():
    return "Plus App Bot & Backend is live!"

@app.route("/api/user", methods=["GET"])
def get_user():
    user_id = request.args.get("id", ADMIN_ID)
    return jsonify(get_or_create_user(user_id))

@app.route("/api/check_channel", methods=["POST"])
def check_channel():
    data = request.json or {}
    user_id = data.get("user_id")
    channel = data.get("channel", "@PlusTechHub")
    user_data = get_or_create_user(user_id)
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": channel, "user_id": user_id}, timeout=5).json()
        status = res.get("result", {}).get("status", "")
        if status in ["member", "administrator", "creator"]:
            if channel not in user_data["tasks_done"]:
                user_data["balance"] += 5.0
                user_data["tasks_done"].append(channel)
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

    user_data = get_or_create_user(user_id)
    user_data["balance"] = max(0.0, user_data["balance"] - amount)

    req_id = len(withdraw_requests) + 1
    req_item = {
        "id": req_id,
        "user_id": user_id,
        "amount": amount,
        "phone": phone,
        "method": method,
        "status": "Pending"
    }
    withdraw_requests.append(req_item)

    # ለአድሚን ማሳወቂያ
    msg = (
        f"🔔 *አዲስ የገንዘብ ማውጣት ጥያቄ!*\n\n"
        f"👤 *ተጠቃሚ ID:* `{user_id}`\n"
        f"💰 *መጠን:* {amount} ETB\n"
        f"💳 *ዘዴ:* {method}\n"
        f"📱 *ስልክ:* `{phone}`"
    )
    send_telegram_message(ADMIN_ID, msg)

    return jsonify({"status": "success", "balance": user_data["balance"]})

@app.route("/api/user/history", methods=["GET"])
def get_user_history():
    user_id = str(request.args.get("user_id", ADMIN_ID))
    history = [r for r in withdraw_requests if r["user_id"] == user_id]
    return jsonify(history)

@app.route("/api/admin/requests", methods=["GET"])
def get_admin_requests():
    return jsonify(withdraw_requests)

@app.route("/api/admin/approve", methods=["POST"])
def approve_request():
    data = request.json or {}
    req_id = data.get("req_id")
    for r in withdraw_requests:
        if r["id"] == req_id:
            r["status"] = "Success"
            # ለተጠቃሚው ማሳወቅ
            user_msg = f"🎉 *እንኳን ደስ አለዎት!*\nየጠየቁት {r['amount']} ETB በተሳካ ሁኔታ ተልኮልዎታል!"
            send_telegram_message(r["user_id"], user_msg)
            break
    return jsonify({"status": "success"})

# የቴሌግራም መልእክቶችን እና የ Referral ሊንክን የሚያስተናግድ Webhook
@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = request.json or {}

    # ተጠቃሚው መልእክት ሲልክ (/start)
    if "message" in update:
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")

        if text.startswith("/start"):
            get_or_create_user(chat_id)
            parts = text.split()

            # ሰው በሊንክ ከመጣ (ለምሳሌ /start ref_8556328355)
            if len(parts) > 1 and parts[1].startswith("ref_"):
                referrer_id = parts[1].replace("ref_", "").strip()

                # ራሱን ካልጋበዘ እና ከዚህ በፊት ያልተመዘገበ ከሆነ
                if referrer_id != chat_id and chat_id not in invited_users:
                    invited_users.add(chat_id)
                    referrer = get_or_create_user(referrer_id)
                    referrer["balance"] += 3.0
                    referrer["invites"] += 1

                    # ለጋባዡ ማሳወቂያ መላክ
                    ref_notify = (
                        f"🎉 *አዲስ ሰው ተቀላቅሏል!*\n\n"
                        f"👤 አንድ ተጠቃሚ በእርስዎ መጋበዣ ሊንክ ገብቷል።\n"
                        f"💰 *+3.00 ETB* ወደ ሂሳብዎ ተጨምሯል!\n"
                        f"💵 አጠቃላይ ሂሳብዎ: {referrer['balance']:.2f} ETB"
                    )
                    send_telegram_message(referrer_id, ref_notify)

            # ለአዲሱ ሰው የሚላክ የእንኳን ደህና መጣህ መልእክት
            welcome_text = (
                f"👋 *እንኳን ወደ Plus App በደህና መጡ!*\n\n"
                f"በየቀኑ Check-in በማድረግ፣ ተግባራትን በማጠናቀቅ እና ጓደኞችዎን በመጋበዝ ገንዘብ ያግኙ!\n\n"
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
