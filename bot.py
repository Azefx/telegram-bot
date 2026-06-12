import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

load_dotenv()

TOKEN = "8641750572:AAEuK9_V8zUBedx-K0s5HZfTQ4kElVHOfm0"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

active_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اهلا! اكتب 'عازف' عشان ابدأ 🎵")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # إيقاف
    if any(cmd in text.lower() for cmd in ["اسكت", "ميتكلمش تاني", "كفاية", "stop", "quiet"]):
        if user_id in active_users:
            active_users.pop(user_id)
            await update.message.reply_text("تمام، سكتت ✅")
        return

    # تفعيل
    if "عازف" in text.lower():
        active_users[user_id] = True
        await update.message.reply_text("تمام يا صاحبي، عازف معاك دلوقتي 🎸\nقول اللي في بالك!")
        return

    # رد AI
    if user_id in active_users and active_users[user_id]:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://telegram-bot",
                    "X-Title": "AI Telegram Bot",
                },
                json={
                    "model": "google/gemini-flash-1.5:free",   # ← غيرناه
                    "messages": [
                        {"role": "system", "content": "أنت بوت مرح مصري، بيتكلم عامية مصرية طبيعية جداً، رد بسرعة وبذكاء."},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.85,
                    "max_tokens": 600
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"API Error: {response.status_code} - {response.text}")
                await update.message.reply_text("في زحمة دلوقتي، جرب بعد دقيقتين 🫡")
                return
                
            reply = response.json()["choices"][0]["message"]["content"]
            await update.message.reply_text(reply)

        except Exception as e:
            print(f"Error: {e}")   # هيظهر في Railway Logs
            await update.message.reply_text("النت بطيء أو في زحمة، جرب تاني شوية!")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("البوت شغال بتحسينات جديدة...")
    app.run_polling()
