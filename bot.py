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
DATA_FILE = "database.json"

GATE_CHANNELS = ["@PlusTechHub", "@Eth_online_job", "@Alphatech_earn"]

TASK_CHANNELS = {
    "task_money_power": {"channel": "@money_power54", "reward": 2.0},
    "task_tips_mickey": {"channel": "@Tipsmickey", "reward": 2.0}
}

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
    str_id = str(user_id).strip()
    if not str_id or str_id == "None":
        str_id = "unknown"

    if str_id not in db["users"]:
        db["users"][str_id] = {
            "balance": 0.0,
            "invites": 0,
            "verified": False,
            "completed_tasks": []
        }
    else:
        if "completed_tasks" not in db["users"][str_id]:
            db["users"][str_id]["completed_tasks"] = []

    return db["users"][str_id]

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": str(chat_id).strip(), "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=6)
    except Exception as e:
        print(f"Send error: {e}")

# አባልነትን 100% አጥብቆ መፈተሽ (ካልገባ በፍጹም False ይመልሳል)
def check_member(channel, user_id):
    str_id = str(user_id).strip()
    if not str_id.isdigit():
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    try:
        res = requests.get(url, params={"chat_id": channel, "user_id": int(str_id)}, timeout=6).json()
        if res.get("ok"):
            status = res.get("result", {}).get("status", "")
            return status in ["member", "administrator", "creator", "restricted"]
        return False
    except Exception:
        return False

@app.route("/")
def index():
    return "Plus App Backend is live and running!"

@app.route("/api/user", methods=["GET", "POST"])
def get_or_sync_user():
    db = load_data()

    if request.method == "POST":
        data = request.json or {}
        user_id = str(data.get("id", "")).strip()
        local_bal = float(data.get("balance", 0.0))
        local_tasks = data.get("completed_tasks", [])
        
        user_data = get_or_create_user(db, user_id)
        if local_bal > user_data["balance"]:
            user_data["balance"] = local_bal
        for t in local_tasks:
            if t not in user_data["completed_tasks"]:
                user_data["completed_tasks"].append(t)
        save_data(db)
        return jsonify(user_data)
    else:
        user_id = str(request.args.get("id", "")).strip()
        user_data = get_or_create_user(db, user_id)
        save_data(db)
        return jsonify(user_data)

# ጥብቅ የቻናሎች ማረጋገጫ (አንዱም ቢቀር ይከለክላል)
@app.route("/api/verify_membership", methods=["POST"])
def verify_membership():
    data = request.json or {}
    user_id = str(data.get("user_id", "")).strip()
    referrer_id = str(data.get("referrer_id", "")).strip()

    if not user_id.isdigit():
        return jsonify({
            "status": "not_joined",
            "message": "የቴሌግራም መለያዎን ማግኘት አልተቻለም። እባክዎ አፑን ከቴሌግራም ቦት ውስጥ ይክፈቱት!",
            "verified": False
        }), 400

    missing = []
    for ch in GATE_CHANNELS:
        if not check_member(ch, user_id):
            missing.append(ch)

    # አንድም ቻናል ከቀረ ማስጠንቀቂያ ሰጥቶ መከልከል
    if missing:
        return jsonify({
            "status": "not_joined",
            "message": f"አልተቀላቀሉም! እባክዎ መጀመሪያ የቀሩትን ቻናሎች ይቀላቀሉ፦ {', '.join(missing)}",
            "verified": False
        }), 400

    db = load_data()
    user_data = get_or_create_user(db, user_id)

    if referrer_id and referrer_id.isdigit() and referrer_id != user_id and user_id not in db["invited_users"]:
        db["invited_users"].append(user_id)
        ref_user = get_or_create_user(db, referrer_id)
        ref_user["balance"] += 3.0
        ref_user["invites"] = ref_user.get("invites", 0) + 1

        ref_msg = (
            f"🎉 *እንኳን ደስ አለዎት!*\n\n"
            f"👤 አዲስ ተጠቃሚ በእርስዎ ሊንክ ተቀላቅሏል!\n"
            f"💰 *+3.00 ETB* ወደ ሂሳብዎ ገብቷል!\n\n"
            f"💵 ጠቅላላ ሂሳብዎ፦ *{ref_user['balance']:.2f} ETB*\n"
            f"👥 ጠቅላላ የጋበዟቸው ሰዎች፦ *{ref_user['invites']}*"
        )
        send_telegram_message(referrer_id, ref_msg)

    user_data["verified"] = True
    save_data(db)

    return jsonify({"status": "verified", "verified": True, "balance": user_data["balance"]})

# የታስክ ማረጋገጫ (ቻናሉን በትክክል ሳይቀላቀል በፍጹም አይሰጥም)
@app.route("/api/task/verify", methods=["POST"])
def verify_task():
    data = request.json or {}
    user_id = str(data.get("user_id", "")).strip()
    task_id = data.get("task_id")

    if not user_id.isdigit():
        return jsonify({"status": "error", "message": "የቴሌግራም መለያ ማግኘት አልተቻለም።"}), 400

    if task_id not in TASK_CHANNELS:
        return jsonify({"status": "error", "message": "የማይታወቅ ታስክ!"}), 400

    db = load_data()
    user_data = get_or_create_user(db, user_id)

    if task_id in user_data.get("completed_tasks", []):
        return jsonify({"status": "error", "message": "ይህንን ታስክ አስቀድመው ወስደዋል!"}), 400

    task_info = TASK_CHANNELS[task_id]
    if not check_member(task_info["channel"], user_id):
        return jsonify({"status": "not_joined", "message": "ቻናሉን አልተቀላቀሉም! እባክዎ መጀመሪያ ቻናሉን ይቀላቀሉ።"}), 400

    reward = task_info["reward"]
    user_data["balance"] += reward
    user_data["completed_tasks"].append(task_id)
    save_data(db)

    return jsonify({
        "status": "success",
        "balance": user_data["balance"],
        "reward": reward,
        "completed_tasks": user_data["completed_tasks"]
    })

@app.route("/api/withdraw", methods=["POST"])
def withdraw():
    data = request.json or {}
    user_id = str(data.get("user_id", "")).strip()
    amount = float(data.get("amount", 0))
    phone = data.get("phone", "")
    method = data.get("method", "Telebirr")

    if not user_id.isdigit():
        return jsonify({"status": "error", "message": "መለያ ማረጋገጥ አልተቻለም!"}), 400

    db = load_data()
    user_data = get_or_create_user(db, user_id)

    if user_data["balance"] < amount:
        return jsonify({"status": "error", "message": "በቂ ቀሪ ሂሳብ የለዎትም!"}), 400

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

    admin_alert = (
        f"🔔 *አዲስ የገንዘብ ማውጣት ጥያቄ!*\n\n"
        f"👤 *ተጠቃሚ ID:* `{user_id}`\n"
        f"💰 *መጠን:* {amount} ETB\n"
        f"💳 *ዘዴ:* {method}\n"
        f"📱 *ስልክ:* `{phone}`\n\n"
        f"ለማጽደቅ ወደ ሚኒ አፑ ገብተው '👑 Admin' ክፍል ውስጥ ያረጋግጡ!"
    )
    send_telegram_message(ADMIN_ID, admin_alert)

    return jsonify({"status": "success", "balance": user_data["balance"], "request": req_item})

@app.route("/api/user/history", methods=["GET"])
def get_user_history():
    user_id = str(request.args.get("user_id", "")).strip()
    db = load_data()
    history = [r for r in db["withdraw_requests"] if str(r.get("user_id", "")).strip() == user_id]
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
            user_msg = (
                f"🎉 *እንኳን ደስ አለዎት!*\n\n"
                f"የጠየቁት *{r['amount']} ETB* በ {r['method']} ተልኮልዎታል!\n"
                f"📱 ስልክ: `{r['phone']}`"
            )
            send_telegram_message(r["user_id"], user_msg)
            save_data(db)
            break
    return jsonify({"status": "success"})

@app.route("/api/admin/add_balance", methods=["POST"])
def add_balance():
    data = request.json or {}
    admin_id = str(data.get("admin_id", "")).strip()
    target_id = str(data.get("target_id", "")).strip()
    amount = float(data.get("amount", 0))

    if admin_id != ADMIN_ID:
        return jsonify({"status": "error", "message": "ያልተፈቀደ አሰራር!"}), 403

    if not target_id.isdigit() or amount <= 0:
        return jsonify({"status": "error", "message": "እባክዎ ትክክለኛ ID እና መጠን ያስገቡ!"}), 400

    db = load_data()
    target_user = get_or_create_user(db, target_id)
    target_user["balance"] += amount
    save_data(db)

    alert_msg = (
        f"🎁 *ስጦታ ደርሶዎታል!*\n\n"
        f"የአስተዳዳሪው ስጦታ *+{amount:.2f} ETB* ወደ አካውንትዎ ገብቷል!\n"
        f"💵 አጠቃላይ ቀሪ ሂሳብዎ፦ *{target_user['balance']:.2f} ETB*"
    )
    send_telegram_message(target_id, alert_msg)

    return jsonify({"status": "success", "new_balance": target_user["balance"]})

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
                                f"ታስኮችን በመስራት እና ጓደኞችዎን በመጋበዝ ገንዘብ ያግኙ!\n\n"
                                f"ከታች ያለውን *«🚀 Open Plus App»* ይጫኑ!"
                            )
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🚀 Open Plus App", "url": f"https://t.me/{BOT_USERNAME}/app"}],
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
