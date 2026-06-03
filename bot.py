import os
import re
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker
from nsfw_detector import predict
from transformers import pipeline

TOKEN = os.getenv("BOT_TOKEN")
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", 0))
SUDO_USERS = [DEVELOPER_ID]
BOT_VERSION = "6.0-PAID"
BOT_USERNAME = os.getenv("BOT_USERNAME", "RayoProtectBot")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///rayo_protect.db"))
Session = sessionmaker(bind=engine)

RANKS = {0: "عضو", 1: "مميز", 2: "ادمن", 3: "مدير", 4: "منشئ", 5: "المالك", 6: "المطور"}
PLANS = {
    "monthly": {"name": "شهري", "days": 30, "price": 100},
    "quarterly": {"name": "3 شهور", "days": 90, "price": 250},
    "yearly": {"name": "سنوي", "days": 365, "price": 800}
}

AWAITING_USER_FOR_CREATOR, AWAITING_USER_FOR_ADMIN, AWAITING_USER_FOR_MOD, AWAITING_USER_FOR_SPECIAL = range(4)
AWAITING_SUB_CODE = range(4, 5)

class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True)
    group_id = Column(BigInteger, unique=True)
    title = Column(String)
    expiry_date = Column(DateTime, default=None)
    owner_id = Column(BigInteger, default=None)
    is_active = Column(Boolean, default=False)
    plan = Column(String, default=None)
    antiflood = Column(Boolean, default=True)
    anti_nsfw = Column(Boolean, default=True)
    anti_links = Column(Boolean, default=True)
    anti_arabic_spam = Column(Boolean, default=True)
    anti_bots = Column(Boolean, default=True)
    max_warnings = Column(Integer, default=3)
    flood_limit = Column(Integer, default=5)

class UserRank(Base):
    __tablename__ = 'ranks'
    id = Column(Integer, primary_key=True)
    group_id = Column(BigInteger)
    user_id = Column(BigInteger)
    rank = Column(Integer, default=0)

class UserWarn(Base):
    __tablename__ = 'warns'
    id = Column(Integer, primary_key=True)
    group_id = Column(BigInteger)
    user_id = Column(BigInteger)
    reason = Column(String)
    date = Column(DateTime, default=datetime.now)

class SubCode(Base):
    __tablename__ = 'sub_codes'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True)
    plan = Column(String)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, default=None)
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)

logger.info("بحمل موديلات الذكاء الاصطناعي Local...")
NSFW_MODEL = predict.load_model('mobilenet_v2_140_224')
TEXT_CLASSIFIER = pipeline("text-classification", model="CAMeL-Lab/bert-base-arabic-camelbert-da-sentiment", device=-1)
logger.info("الموديلات جاهزة ✅")

BAD_WORDS = ['خول', 'شرموط', 'متناك', 'كسمك', 'احا', 'عرص', 'قحبة', 'زانية', 'fuck', 'bitch', 'porn', 'sex']

def get_user_rank(group_id, user_id):
    if user_id == DEVELOPER_ID: return 6
    session = Session()
    group = session.query(Group).filter_by(group_id=group_id).first()
    if group and group.owner_id == user_id:
        session.close()
        return 5
    user_rank = session.query(UserRank).filter_by(group_id=group_id, user_id=user_id).first()
    session.close()
    return user_rank.rank if user_rank else 0

def set_user_rank(group_id, user_id, rank):
    session = Session()
    user_rank = session.query(UserRank).filter_by(group_id=group_id, user_id=user_id).first()
    if not user_rank:
        user_rank = UserRank(group_id=group_id, user_id=user_id, rank=rank)
        session.add(user_rank)
    else:
        user_rank.rank = rank
    session.commit()
    session.close()

def get_group(group_id):
    session = Session()
    group = session.query(Group).filter_by(group_id=group_id).first()
    if not group:
        group = Group(group_id=group_id)
        session.add(group)
        session.commit()
    session.close()
    return group

def is_paid(group_id):
    group = get_group(group_id)
    return group.is_active and group.expiry_date and group.expiry_date > datetime.now()

def is_nsfw_local(image_path):
    try:
        result = predict.classify(NSFW_MODEL, image_path)
        nsfw_score = result[image_path]['porn'] + result[image_path]['hentai'] + result[image_path]['sexy']
        return nsfw_score > 0.65
    except: return False

def is_bad_text_ai(text):
    try:
        result = TEXT_CLASSIFIER(text[:512])[0]
        has_bad_word = any(word in text for word in BAD_WORDS)
        return result['label'] == 'negative' and result['score'] > 0.85 and has_bad_word
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        keyboard = [[InlineKeyboardButton("➕ اضفني لجروبك", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]]
        await update.message.reply_text(
            f"🤖 أهلاً بيك في بوت حماية Rayo v{BOT_VERSION}\n\n"
            "البوت مدفوع باشتراك شهري من المطور.\n"
            "للاشتراك كلمني: @YourUsername\n\n"
            "الأسعار:\n"
            f"• شهري: {PLANS['monthly']['price']} جنيه\n"
            f"• 3 شهور: {PLANS['quarterly']['price']} جنيه\n"
            f"• سنوي: {PLANS['yearly']['price']} جنيه",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        group = get_group(update.effective_chat.id)
        if not group.is_active:
            await update.message.reply_text("❌ الجروب غير مفعل. اطلب كود تفعيل من المطور @YourUsername")
        else:
            await cmd_commands(update, context)

async def cmd_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_paid(chat_id) and update.effective_user.id!= DEVELOPER_ID:
        return await update.message.reply_text("❌ الجروب غير مفعل. استخدم /activate لتفعيل الاشتراك")

    keyboard = [
        [InlineKeyboardButton("• 1 •", callback_data="menu_1"), InlineKeyboardButton("• 2 •", callback_data="menu_2")],
        [InlineKeyboardButton("• 3 •", callback_data="menu_3")],
        [InlineKeyboardButton("• 4 •", callback_data="menu_4"), InlineKeyboardButton("• 5 •", callback_data="menu_5")],
        [InlineKeyboardButton("• 6 •", callback_data="menu_6")]
    ]
    group = get_group(chat_id)
    days_left = (group.expiry_date - datetime.now()).days if group.expiry_date else 0
    text = f"""
بوت حمايه Rayo 🤖

حالة الاشتراك: مفعل ✅
الخطة: {PLANS[group.plan]['name'] if group.plan else 'غير محدد'}
متبقي: {days_left} يوم

اليك اوامر البوت {BOT_VERSION} : -

- اوامر الحمايه ⌯ [ 1م ] : -
- اوامر المشرفين ⌯ [ 2م ] : -
- اوامر الرتب ⌯ [ 3م ] : -
- اوامر التفعيلات ⌯ [ 4م ] : -
- اوامر المسح ⌯ [ 5م ] : -
- اوامر المطورين ⌯ [ 6م ] : -
"""
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    user_rank = get_user_rank(chat_id, user_id)

    if not is_paid(chat_id) and user_id!= DEVELOPER_ID:
        return await query.answer("الجروب غير مفعل", show_alert=True)

    if query.data == "menu_1":
        if user_rank < 2: return await query.answer("للادمن فما فوق", show_alert=True)
        group = get_group(chat_id)
        status = lambda x: '✅' if x else '❌'
        text = f"""⚙️ اوامر الحمايه - [ 1م ] | رتبتك: {RANKS[user_rank]}

1. قفل التكرار: {status(group.antiflood)} - /flood
2. قفل الروابط: {status(group.anti_links)} - /antilink
3. قفل الصور الإباحية: {status(group.anti_nsfw)} - /antinsfw
4. قفل الشتائم: {status(group.anti_arabic_spam)} - /antispam
5. قفل البوتات: {status(group.anti_bots)} - /antibots
6. وضع الطوارئ: /emergency
"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع", callback_data="main_menu")]]))

    elif query.data == "menu_3":
        if user_rank < 3: return await query.answer("للمدير فما فوق", show_alert=True)
        keyboard = [
            [InlineKeyboardButton("رفع منشئ", callback_data="promote_creator")],
            [InlineKeyboardButton("رفع مدير", callback_data="promote_admin")],
            [InlineKeyboardButton("رفع ادمن", callback_data="promote_mod")],
            [InlineKeyboardButton("رفع مميز", callback_data="promote_special")],
            [InlineKeyboardButton("تنزيل عضو", callback_data="demote_user")],
            [InlineKeyboardButton("رجوع", callback_data="main_menu")]
        ]
        text = f"""🎖️ اوامر الرتب - [ 3م ] | رتبتك: {RANKS[user_rank]}

دوس على الزر وارسل يوزر العضو أو اعمل ربلاي عليه
"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "main_menu":
        await cmd_commands(query, context)

async def start_promote(update: Update, context: ContextTypes.DEFAULT_TYPE, rank, rank_name, next_state):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_rank = get_user_rank(chat_id, query.from_user.id)

    if user_rank <= rank and user_rank!= 6:
        return await query.edit_message_text("❌ ماتقدرش ترفع لرتبة أعلى منك أو زيك")

    await query.edit_message_text(f"📤 ارسل الآن @يوزر العضو أو اعمل ربلاي عليه لرفعه {rank_name}", reply_markup=ForceReply(selective=True))
    context.user_data['rank_to_set'] = rank
    context.user_data['rank_name'] = rank_name
    context.user_data['chat_id'] = chat_id
    return next_state

async def promote_creator_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_promote(update, context, 4, "منشئ", AWAITING_USER_FOR_CREATOR)

async def promote_admin_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_promote(update, context, 3, "مدير", AWAITING_USER_FOR_ADMIN)

async def promote_mod_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start_promote(update, context, 2, "ادمن", AWAITING_USER_FOR_MOD)

async def receive_user_to_promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data['chat_id']
    rank = context.user_data['rank_to_set']
    rank_name = context.user_data['rank_name']
    target_user = None

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif update.message.text.startswith('@'):
        try:
            target_user = await context.bot.get_chat(update.message.text)
        except:
            return await update.message.reply_text("❌ اليوزر مش موجود")
    elif update.message.text.isdigit():
        try:
            target_user = await context.bot.get_chat_member(chat_id, int(update.message.text))
            target_user = target_user.user
        except:
            return await update.message.reply_text("❌ الأيدي مش في الجروب")
    else:
        return await update.message.reply_text("❌ ابعت @يوزر أو اعمل ربلاي")

    set_user_rank(chat_id, target_user.id, rank)
    await update.message.reply_text(f"✅ تم رفع {target_user.mention_html()} إلى {rank_name}", parse_mode='HTML')
    return ConversationHandler.END

async def cmd_gensub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= DEVELOPER_ID: return
    if not context.args or context.args[0] not in PLANS:
        return await update.message.reply_text("استخدام: /gensub [monthly/quarterly/yearly]")
    plan = context.args[0]
    import random, string
    code = f"RAYO-{plan.upper()}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    session = Session()
    new_code = SubCode(code=code, plan=plan)
    session.add(new_code)
    session.commit()
    session.close()
    await update.message.reply_text(f"✅ كود تفعيل جديد:\n\n`{code}`\n\nالخطة: {PLANS['name']}\nالسعر: {PLANS['price']} جنيه", parse_mode='Markdown')

async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        return await update.message.reply_text("الأمر ده في الجروب بس")
    await update.message.reply_text("📤 ارسل كود التفعيل اللي اشتريته من المطور", reply_markup=ForceReply(selective=True))
    return AWAITING_SUB_CODE

async def receive_sub_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    chat_id = update.effective_chat.id
    session = Session()
    sub_code = session.query(SubCode).filter_by(code=code, is_used=False).first()
    if not sub_code:
        session.close()
        return await update.message.reply_text("❌ الكود غلط أو مستخدم قبل كده")

    group = session.query(Group).filter_by(group_id=chat_id).first()
    group.is_active = True
    group.expiry_date = datetime.now() + timedelta(days=PLANS[sub_code.plan]['days'])
    group.plan = sub_code.plan
    group.owner_id = update.effective_user.id
    sub_code.is_used = True
    sub_code.used_by = chat_id
    session.commit()
    session.close()
    await update.message.reply_text(f"✅ تم تفعيل البوت بنجاح!\nالخطة: {PLANS[sub_code.plan]['name']}\nالمدة: {PLANS[sub_code.plan]['days']} يوم\n\nاستخدم /اوامر لعرض القائمة")
    return ConversationHandler.END

async def cancel_convo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم الإلغاء")
    return ConversationHandler.END

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_chat.type == 'private': return
    chat_id, user_id = update.effective_chat.id, update.effective_user.id
    if not is_paid(chat_id) and user_id!= DEVELOPER_ID: return
    if get_user_rank(chat_id, user_id) >= 1: return
    group = get_group(chat_id)
    if group.anti_arabic_spam and update.message.text and is_bad_text_ai(update.message.text):
        await update.message.delete()
        return
    if group.anti_links and update.message.entities:
        if any(e.type in ['url', 'text_link'] for e in update.message.entities):
            await update.message.delete()
            return
    if group.anti_nsfw and update.message.photo:
        file = await update.message.photo[-1].get_file()
        path = f"temp_{file.file_id}.jpg"
        await file.download_to_drive(path)
        if is_nsfw_local(path):
            os.remove(path)
            await update.message.delete()
            return
        os.remove(path)

async def new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("شكراً لإضافتي! البوت محتاج تفعيل من المطور.\nاطلب كود تفعيل من @YourUsername وبعدين استخدم /activate")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    promote_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(promote_creator_btn, pattern="^promote_creator$"),
            CallbackQueryHandler(promote_admin_btn, pattern="^promote_admin$"),
            CallbackQueryHandler(promote_mod_btn, pattern="^promote_mod$"),
        ],
        states={
            AWAITING_USER_FOR_CREATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_to_promote)],
            AWAITING_USER_FOR_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_to_promote)],
            AWAITING_USER_FOR_MOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_to_promote)],
        },
        fallbacks=[CommandHandler("cancel", cancel_convo)],
    )
    activate_conv = ConversationHandler(
        entry_points=[CommandHandler("activate", cmd_activate)],
        states={AWAITING_SUB_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sub_code)]},
        fallbacks=[CommandHandler("cancel", cancel_convo)],
    )
    app.add_handler(CommandHandler(["start", "اوامر", "الاوامر"], cmd_commands))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(promote_conv)
    app.add_handler(activate_conv)
    app.add_handler(CommandHandler("gensub", cmd_gensub))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_chat_members))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_filter))
    logger.info(f"Rayo Bot v{BOT_VERSION} - PAID - Running...")
    app.run_polling()

if __name__ == '__main__':
    from web import app as flask_app
    import threading
    def run_flask():
        flask_app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    main()
