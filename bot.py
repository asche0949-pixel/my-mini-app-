import telebot
from telebot import types
from flask import Flask, request, jsonify
from flask_cors import CORS

BOT_TOKEN = "8856484714:AAGgssIq-QLAxiZdvOpSEt1cBiqlSwXRjgE"
bot = telebot.TeleBot(BOT_TOKEN)

# የአንተ ቴሌግራም ID (ብር ማውጣት ሲጠየቅ መልእክት በቀጥታ ለአንተ ይደርሳል)
ADMIN_ID = "8556328355"

app = Flask(__name__)
CORS(app)

users = {}

@app.route('/')
def home():
    return "FulusApp Server is Running!"

@app.route('/api/user', methods=['GET'])
def get_user():
    user_id = request.args.get('id')
    if not user_id:
        return jsonify({"error": "No ID provided"}), 400
    
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "streak": 0,
            "invites": 0,
            "tasks_done": []
        }
    return jsonify(users[user_id])

@app.route('/api/check_channel', methods=['POST'])
def check_channel():
    data = request.json
    user_id = data.get('user_id')
    channel = data.get('channel')

    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            if channel not in users[str(user_id)]["tasks_done"]:
                users[str(user_id)]["tasks_done"].append(channel)
                users[str(user_id)]["balance"] += 5.0
            return jsonify({"status": "joined", "balance": users[str(user_id)]["balance"]})
        else:
            return jsonify({"status": "not_joined"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = data.get('user_id')
    amount = float(data.get('amount', 0))
    phone = data.get('phone')
    method = data.get('method')

    if users.get(str(user_id), {}).get('balance', 0) >= amount and amount >= 60:
        users[str(user_id)]['balance'] -= amount
        
        msg = f"🔔 አዲስ የብር ማውጣት ጥያቄ!\n\n👤 ተጠቃሚ ID: {user_id}\n📞 ስልክ: {phone}\n💰 መጠን: {amount} ETB\n🏦 ዘዴ: {method}"
        try:
            bot.send_message(ADMIN_ID, msg)
        except:
            pass
            
        return jsonify({"status": "success", "balance": users[str(user_id)]['balance']})
    return jsonify({"status": "failed", "message": "Insufficient balance"}), 400

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.chat.id)
    text_parts = message.text.split()
    
    if len(text_parts) > 1 and text_parts[1].startswith('ref_'):
        referrer_id = text_parts[1].replace('ref_', '')
        if referrer_id in users and referrer_id != user_id:
            users[referrer_id]["balance"] += 3.0
            users[referrer_id]["invites"] += 1
            try:
                bot.send_message(referrer_id, "🎉 አዲስ ሰው ጋብዘሃል! 3 ETB ተጨምሮልሃል።")
            except:
                pass

    if user_id not in users:
        users[user_id] = {"balance": 0.0, "streak": 0, "invites": 0, "tasks_done": []}

    markup = types.InlineKeyboardMarkup()
    app_btn = types.InlineKeyboardButton("🚀 Open FulusApp", web_app=types.WebAppInfo("https://asche0949-pixel.github.io/my-mini-app-/"))
    markup.add(app_btn)
    bot.send_message(message.chat.id, "እንኳን ወደ FulusApp በደህና መጡ! ከታች ያለውን በተን ተጭነው ስራዎችን ይጀምሩ።", reply_markup=markup)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
