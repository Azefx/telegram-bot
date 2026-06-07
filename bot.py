import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MONTH_STARS = 200
YEAR_STARS = 500

DB_NAME = "bot.db"

# ================== DATABASE ==================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS codes (
                code TEXT PRIMARY KEY,
                days INTEGER DEFAULT 30,
                used BOOLEAN DEFAULT 0,
                used_by INTEGER,
                used_at TEXT
            );
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                amount INTEGER,
                method TEXT,
                status TEXT DEFAULT 'pending',
                proof TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscription_end TEXT
            );
        ''')
        await db.commit()

async def add_codes_list(codes_list: list):
    added = 0
    async with aiosqlite.connect(DB_NAME) as db:
        for code in codes_list:
            code = code.strip().upper()
            if code:
                try:
                    await db.execute("INSERT OR IGNORE INTO codes (code) VALUES (?)", (code,))
                    added += 1
                except:
                    pass
        await db.commit()
    return added

async def get_available_code(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT code FROM codes WHERE used = 0 LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if row:
                code = row[0]
                await db.execute(
                    "UPDATE codes SET used = 1, used_by = ?, used_at = ? WHERE code = ?",
                    (user_id, datetime.now().isoformat(), code)
                )
                await db.commit()
                return code
    return None

async def count_available_codes():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM codes WHERE used = 0") as cursor:
            return (await cursor.fetchone())[0]

# ================== KEYBOARDS ==================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 اشتراك شهري - 200 ⭐", callback_data="buy_month")
    kb.button(text="🛒 اشتراك سنوي - 500 ⭐", callback_data="buy_year")
    kb.button(text="💰 دفع كريبتو", callback_data="crypto")
    kb.button(text="📋 الأكواد المتاحة", callback_data="show_codes")
    kb.adjust(1)
    return kb.as_markup()

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ الدفعات المعلقة", callback_data="pending_payments")
    kb.button(text="📦 إدارة الأكواد", callback_data="manage_codes")
    kb.button(text="➕ إضافة أكواد جديدة", callback_data="add_codes")
    kb.adjust(1)
    return kb.as_markup()

# ================== BOT ==================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(
        "👋 <b>مرحبا بك في بوت اشتراكات النشر التلقائي</b>\n\n"
        "اختر الخدمة:",
        reply_markup=main_menu()
    )

@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("🔧 <b>لوحة تحكم الأدمن</b>", reply_markup=admin_menu())

# ================== شراء بالنجوم ==================
@dp.callback_query(F.data == "buy_month")
async def buy_month(call: CallbackQuery):
    await call.message.answer_invoice(
        title="اشتراك شهري",
        description="اشتراك 30 يوم",
        payload="month_sub",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="شهري", amount=MONTH_STARS)]
    )

@dp.callback_query(F.data == "buy_year")
async def buy_year(call: CallbackQuery):
    await call.message.answer_invoice(
        title="اشتراك سنوي",
        description="اشتراك سنة كاملة",
        payload="year_sub",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="سنوي", amount=YEAR_STARS)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(msg: Message):
    payload = msg.successful_payment.invoice_payload
    user_id = msg.from_user.id
    username = msg.from_user.username or "بدون"

    if payload == "month_sub":
        code = await get_available_code(user_id)
        if code:
            await bot.send_message(user_id, f"✅ <b>تم الدفع بنجاح!</b>\n\nكودك:\n<code>{code}</code>\n\nاستمتع 🚀")
        else:
            await bot.send_message(user_id, "❌ لا توجد أكواد متاحة حالياً.")

    elif payload == "year_sub":
        await bot.send_message(user_id, "✅ تم الدفع!\n\nأرسل أيدي حسابك في بوت النشر للتفعيل اليدوي.")
        await bot.send_message(ADMIN_ID, f"🔔 اشتراك سنوي جديد\nUser: {username} ({user_id})")

# ================== دفع كريبتو ==================
@dp.callback_query(F.data == "crypto")
async def crypto(call: CallbackQuery):
    text = """💰 طرق الدفع:

USDT Aptos: `0xf8873fe62b564ff0d8042e84c24277c8cef7ee3beb94be1ab0c5da26a7346f77`
... (كل العناوين)

بعد التحويل أرسل سكرين + أيديك"""
    await call.message.answer(text, parse_mode="Markdown")
    await call.answer()

# ================== إدارة الأكواد ==================
@dp.callback_query(F.data == "show_codes")
async def show_codes(call: CallbackQuery):
    count = await count_available_codes()
    await call.message.answer(f"📋 الأكواد المتاحة: <b>{count}</b> كود")
    await call.answer()

@dp.callback_query(F.data == "manage_codes")
async def manage_codes(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    count = await count_available_codes()
    await call.message.answer(f"📦 الأكواد المتاحة: {count}\n\nاستخدم /addcodes لإضافة قائمة جديدة", reply_markup=admin_menu())

@dp.callback_query(F.data == "add_codes")
async def add_codes_btn(call: CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer("📥 أرسل قائمة الأكواد (كود في كل سطر):")
        await call.answer()

@dp.message(Command("addcodes"))
async def add_codes_cmd(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    await msg.answer("📥 أرسل قائمة الأكواد (كود في كل سطر):")

@dp.message()
async def handle_text(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    # إضافة أكواد
    lines = msg.text.strip().splitlines()
    if len(lines) > 1 or (len(lines) == 1 and len(lines[0]) > 10):
        added = await add_codes_list(lines)
        await msg.answer(f"✅ تم إضافة <b>{added}</b> كود جديد بنجاح!")
        return

# ================== MAIN ==================
async def main():
    await init_db()
    print("✅ البوت شغال بنجاح...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
