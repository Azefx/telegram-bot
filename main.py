from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ParseMode
import re
import os

BOT_TOKEN = "8961259856:AAEdusv7MT6L6CANxSrZK-Et-K1Y73HBHm8"
API_ID = 33595004
API_HASH = "cbd1066ed026997f2f4a7c4323b7bda7"
ADMIN_IDS = [8085768728] # حط ايديك

bot = Client("advanced_post_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# تخزين مؤقت لكل يوزر
user_data = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 منشور نصي", callback_data="post_text"),
         InlineKeyboardButton("🖼️ منشور صورة", callback_data="post_photo")],
        [InlineKeyboardButton("📢 نشر لقناة", callback_data="select_channel")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ])

def post_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إضافة أزرار", callback_data="add_buttons"),
         InlineKeyboardButton("👁️ معاينة", callback_data="preview")],
        [InlineKeyboardButton("🚀 نشر الآن", callback_data="publish"),
         InlineKeyboardButton("🗑️ مسح", callback_data="clear")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])

@bot.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if not is_admin(message.from_user.id):
        return await message.reply("مش عندك صلاحية")

    user_data[message.from_user.id] = {"text": "", "photo": None, "buttons": []}
    await message.reply(
        "👋 أهلاً بيك في بوت النشر المتطور\n"
        "اختار نوع المنشور من تحت:",
        reply_markup=main_menu()
    )

@bot.on_callback_query()
async def callbacks(client, callback: CallbackQuery):
    uid = callback.from_user.id
    if not is_admin(uid):
        return await callback.answer("مش عندك صلاحية", show_alert=True)

    data = callback.data
    user_data.setdefault(uid, {"text": "", "photo": None, "buttons": []})

    if data == "post_text":
        await callback.message.edit_text("اكتب النص دلوقتي.\nتقدر تستخدم **عريض** _مايل_ `كود`")
        user_data[uid]["state"] = "waiting_text"

    elif data == "post_photo":
        await callback.message.edit_text("ابعث الصورة دلوقتي مع الكابشن لو عايز")
        user_data[uid]["state"] = "waiting_photo"

    elif data == "add_buttons":
        await callback.message.edit_text(
            "اكتب الأزرار بالصيغة دي:\n"
            "`[نص الزرار](الرابط)`\n"
            "كل سطر = سطر أزرار جديد"
        )
        user_data[uid]["state"] = "waiting_buttons"

    elif data == "preview":
        await show_preview(client, callback, uid)

    elif data == "publish":
        await callback.message.edit_text("اعمل ريبلي على رسالة من القناة عشان أعرف أنشر فين")
        user_data[uid]["state"] = "waiting_channel"

    elif data == "clear":
        user_data[uid] = {"text": "", "photo": None, "buttons": []}
        await callback.message.edit_text("✅ مسحت كل حاجة", reply_markup=main_menu())

    elif data == "back":
        await callback.message.edit_text("القائمة الرئيسية:", reply_markup=main_menu())

    elif data == "cancel":
        user_data.pop(uid, None)
        await callback.message.delete()

    await callback.answer()

@bot.on_message(filters.private)
async def handle_messages(client, message: Message):
    uid = message.from_user.id
    if not is_admin(uid) or uid not in user_data:
        return

    state = user_data[uid].get("state")

    if state == "waiting_text":
        user_data[uid]["text"] = message.text
        user_data[uid]["state"] = None
        await message.reply("✅ تم حفظ النص", reply_markup=post_menu())

    elif state == "waiting_photo":
        if message.photo:
            user_data[uid]["photo"] = message.photo.file_id
            user_data[uid]["text"] = message.caption or ""
            user_data[uid]["state"] = None
            await message.reply("✅ تم حفظ الصورة", reply_markup=post_menu())
        else:
            await message.reply("ابعث صورة يا غالي")

    elif state == "waiting_buttons":
        buttons = parse_buttons(message.text)
        user_data[uid]["buttons"] = buttons
        user_data[uid]["state"] = None
        await message.reply(f"✅ ضفت {len(buttons)} زرار", reply_markup=post_menu())

    elif state == "waiting_channel":
        if message.reply_to_message:
            await publish_post(client, message, uid, message.reply_to_message.chat.id)
        else:
            await message.reply("اعمل ريبلي على رسالة من القناة")

def parse_buttons(text):
    lines = text.strip().split("\n")
    keyboard = []
    for line in lines:
        matches = re.findall(r'\[(.*?)\]\((.*?)\)', line)
        row = [InlineKeyboardButton(txt, url=url) for txt, url in matches]
        if row:
            keyboard.append(row)
    return keyboard

async def show_preview(client, callback, uid):
    data = user_data[uid]
    text = data["text"]
    if not text:
        return await callback.answer("اكتب نص الأول", show_alert=True)

    if not any(e in text for e in ["✨", "🔥", "⚡", "💎", "🚀"]):
        text = "✨ " + text

    keyboard = InlineKeyboardMarkup(data["buttons"]) if data["buttons"] else None

    try:
        if data["photo"]:
            await client.send_photo(
                chat_id=uid,
                photo=data["photo"],
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await client.send_message(
                chat_id=uid,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        await callback.answer("دي المعاينة")
    except Exception as e:
        await callback.answer(f"غلط في التنسيق: {e}", show_alert=True)

async def publish_post(client, message, uid, channel_id):
    data = user_data[uid]
    text = data["text"]
    if not text:
        return await message.reply("مفيش نص تنشره")

    if not any(e in text for e in ["✨", "🔥", "⚡", "💎", "🚀"]):
        text = "✨ " + text

    keyboard = InlineKeyboardMarkup(data["buttons"]) if data["buttons"] else None

    try:
        if data["photo"]:
            await client.send_photo(
                chat_id=channel_id,
                photo=data["photo"],
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await client.send_message(
                chat_id=channel_id,
                text=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        await message.reply("✅ اتنشر بنجاح", reply_markup=main_menu())
        user_data[uid] = {"text": "", "photo": None, "buttons": []}
    except Exception as e:
        await message.reply(f"❌ غلط: {e}")

print("Bot started...")
bot.run()
