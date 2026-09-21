import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8156108154:AAH_F6BwI4Y3S55LzYy6B3c8W1R8fN6Kz9o"
ADMIN_ID = "8556328355"

users_db = {}
withdraw_requests = []

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
    return "Plus App Backend is running!"

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
        res = requests.get(url, params={"chat_id": channel, "user_id": user_id}).json()
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

    return jsonify({"status": "success", "balance": user_data["balance"]})

# የተጠቃሚውን ብቻ ታሪክ የሚያሳይ API
@app.route("/api/user/history", methods=["GET"])
def get_user_history():
    user_id = str(request.args.get("user_id", ADMIN_ID))
    history = [r for r in withdraw_requests if r["user_id"] == user_id]
    return jsonify(history)

# ለአድሚን ጥያቄዎችን የሚያሳይ API
@app.route("/api/admin/requests", methods=["GET"])
def get_admin_requests():
    return jsonify(withdraw_requests)

# አድሚኑ Approve ሲያደርግ ወደ Success የሚቀይር API
@app.route("/api/admin/approve", methods=["POST"])
def approve_request():
    data = request.json or {}
    req_id = data.get("req_id")
    for r in withdraw_requests:
        if r["id"] == req_id:
            r["status"] = "Success"
            break
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
