import os
import requests
from flask import Flask, request
import telebot

BOT_TOKEN = '8641750572:AAEuK9_V8zUBedx-K0s5HZfTQ4kElVHOfm0'
POE_KEY = os.environ.get('POE_KEY') # هنضيفه في Railway

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

def ask_ai(text):
    # API مجاني من Poe: gpt-3.5-turbo
    url = "https://api.poe.com/bot/gpt-3.5-turbo"
    headers = {"Authorization": f"Bearer {POE_KEY}"}
    r = requests.post(url, json={"query": text}, headers=headers)
    return r.json().get('text', 'حصل خطأ')

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    bot.send_chat_action(message.chat.id, 'typing')
    reply = ask_ai(message.text)
    bot.send_message(message.chat.id, reply)

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok"

@app.route("/")
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://' + os.environ['RAILWAY_STATIC_URL'] + '/' + BOT_TOKEN)
    return "webhook set"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
