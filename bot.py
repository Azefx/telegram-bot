import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests  # بدل groq client

load_dotenv()

TOKEN = "8641750572:AAEuK9_V8zUBedx-K0s5HZfTQ4kElVHOfm0"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# قاموس اليوزرز الشغالين
active_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اهلا! اكتب 'عازف' عشان ابدأ اتكلم معاك 🎵")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # أوامر الإيقاف
    stop_commands = ["اسكت", "ميتكلمش تاني", "كفاية", "stop", "quiet"]
    if any(cmd in text.lower() for cmd in stop_commands):
        if user_id in active_users:
            active_users.pop(user_id)
            await update.message.reply_text("تمام، سكتت ✅")
        return

    # تفعيل البوت
    if "عازف" in text.lower():
        active_users[user_id] = True
        await update.message.reply_text("تمام يا صاحبي، عازف معاك دلوقتي 🎸\nقول اللي عايزه!")
        return

    # لو اليوزر شغال → رد AI
    if user_id in active_users and active_users[user_id]:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://your-telegram-bot.com",  # اختياري
                    "X-Title": "Telegram AI Bot",
                },
                json={
                    "model": "meta-llama/llama-3.3-70b-instruct:free",   # أو google/gemini-flash-1.5:free أو deepseek/deepseek-r1:free
                    "messages": [
                        {"role": "system", "content": "أنت بوت مرح وصريح بيتكلم عامية مصرية فصيحة، رد طبيعي ومضحك أحياناً."},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 700
                }
            )
            
            reply = response.json()["choices"][0]["message"]["content"]
            await update.message.reply_text(reply)
            
        except Exception as e:
            await update.message.reply_text("في مشكلة دلوقتي، جرب تاني!")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("البوت شغال بـ OpenRouter 🚀")
    app.run_polling()
