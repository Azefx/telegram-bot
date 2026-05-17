from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
import re

BOT_TOKEN = "8961259856:AAEdusv7MT6L6CANxSrZK-Et-K1Y73HBHm8"
API_ID = 33595004
API_HASH = "cbd1066ed026997f2f4a7c4323b7bda7"
ADMIN_IDS = [8085768728] # حط ايديك

bot = Client("post_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.on_message(filters.command("post") & filters.private)
async def post_text(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("مش عندك صلاحية")
    await send_post(client, message, has_photo=False)

@bot.on_message(filters.photo & filters.private)
async def post_photo(client, message):
    if not is_admin(message.from_user.id):
        return
    if not message.caption or not message.caption.startswith("/post"):
        return await message.reply("ابعته بالصيغة: /post نصك هنا\nلإضافة أزرار حطها تحت النص كده:\n[نص الزرار](url)")
    await send_post(client, message, has_photo=True)

async def send_post(client, message, has_photo):
    try:
        # افصل الكوماند عن النص
        text = message.caption if has_photo else message.text
        text = text.split(None, 1)[1]

        # افصل الأزرار لو موجودة
        buttons = None
        if "\n[" in text:
            parts = text.rsplit("\n[", 1)
            text = parts[0]
            buttons_text = "[" + parts[1]
            button_lines = re.findall(r'\[(.*?)\]\((.*?)\)', buttons_text)
            keyboard = []
            row = []
            for i, (btn_text, btn_url) in enumerate(button_lines):
                row.append(InlineKeyboardButton(btn_text, url=btn_url))
                if len(row) == 2 or i == len(button_lines) - 1:
                    keyboard.append(row)
                    row = []
            if keyboard:
                buttons = InlineKeyboardMarkup(keyboard)

        # ضيف إيموجي بريميوم تلقائي لو مش موجود
        if not any(e in text for e in ["✨", "🔥", "⚡", "💎", "🚀", "⭐"]):
            text = "✨ " + text

        # حوّل التنسيق لـ MarkdownV2 عشان يشتغل من غير <>
        text = escape_markdown_v2(text)

        # لازم تعمل ريبلي على رسالة من القناة عشان اعرف انشر فين
        if not message.reply_to_message:
            return await message.reply("اعمل ريبلي على اي رسالة من القناة واكتب /post نصك")

        channel_id = message.reply_to_message.chat.id

        if has_photo:
            await client.send_photo(
                chat_id=channel_id,
                photo=message.photo.file_id,
                caption=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await client.send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=buttons,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True
            )

        await message.reply("✅ اتنشر في القناة")

    except Exception as e:
        await message.reply(f"❌ غلط: {e}")

def escape_markdown_v2(text):
    # حوّل **عريض** و _مايل_ و `كود` لـ MarkdownV2
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.*?)__', r'__\1__', text)
    text = re.sub(r'`(.*?)`', r'`\1`', text)
    return text

print("Bot started...")
bot.run()
