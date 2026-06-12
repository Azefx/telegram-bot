import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

load_dotenv()

TOKEN = "8641750572:AAHYlqGYMYS_NZj4pzTWd2yOyXsyh31ZxFs"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# قاموس عشان نحفظ مين شغال مع البوت دلوقتي (user_id → True/False)
active_users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اهلا! اكتب 'عازف' في الجروب عشان ابدأ اتكلم معاك 🎵")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_type = update.effective_chat.type
    
    # أوامر الإيقاف
    stop_commands = ["اسكت", "ميتكلمش تاني", "كفاية", "stop", "quiet"]
    if any(cmd in text.lower() for cmd in stop_commands):
        if user_id in active_users:
            active_users.pop(user_id)
            await update.message.reply_text("تمام، سكتت ✅")
        return

    # تفعيل البوت بكلمة "عازف"
    if "عازف" in text:
        active_users[user_id] = True
        await update.message.reply_text("تمام يا صاحبي، عازف معاك دلوقتي 🎸\nاكتب اللي عايزه وانا هرد عليك!")
        return

    # لو المستخدم شغال → يرد عليه
    if user_id in active_users and active_users[user_id]:
        try:
            # برومبت قوي بالعامية المصرية
            prompt = f"""أنت بوت مرح وصريح بيتكلم عامية مصرية، رد بطريقة طبيعية ومضحكة أحياناً.
            الرسالة: {text}"""
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=600,
            )
            reply = chat_completion.choices[0].message.content
            await update.message.reply_text(reply)
        except Exception:
            await update.message.reply_text("في حاجة غلط، جرب تاني!")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("البوت شغال في الجروبات والخاص... 🎵")
    app.run_polling()
