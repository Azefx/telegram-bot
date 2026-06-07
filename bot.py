import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

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
                await db.execute("INSERT OR IGNORE INTO codes (code) VALUES (?)", (code,))
                added += 1
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

async def save_pending_payment(user_id: int, username: str, amount: int, proof: str, method: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO payments (user_id, username, amount, method, proof) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, amount, method, proof)
        )
        await db.commit()
        async with db.execute("SELECT last_insert_rowid()") as cursor:
            pid = (await cursor.fetchone())[0]
            return pid

async def update_payment_status(payment_id: int, status: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
        await db.commit()

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
    kb.button(text="➕ إضافة أكواد", callback_data="add_codes")
    kb.adjust(1)
    return kb.as_markup()

def accept_reject_kb(payment_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ قبول", callback_data=f"accept_{payment_id}")
    kb.button(text="❌ رفض", callback_data=f"reject_{payment_id}")
    kb.adjust(2)
    return kb.as_markup()

# ================== BOT ==================
logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer("👋 <b>مرحبا بك في بوت اشتراكات النشر التلقائي</b>\n\nاختر الخدمة:", reply_markup=main_menu())

@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("🔧 <b>لوحة تحكم الأدمن</b>", reply_markup=admin_menu())

# ================== TELEGRAM STARS ==================
@dp.callback_query(F.data == "buy_month")
async def buy_month(call: CallbackQuery):
    await call.message.answer_invoice(
        title="اشتراك شهري", description="30 يوم", payload="month_sub",
        provider_token="", currency="XTR", prices=[LabeledPrice(label="شهري", amount=MONTH_STARS)]
    )

@dp.callback_query(F.data == "buy_year")
async def buy_year(call: CallbackQuery):
    await call.message.answer_invoice(
        title="اشتراك سنوي", description="سنة كاملة", payload="year_sub",
        provider_token="", currency="XTR", prices=[LabeledPrice(label="سنوي", amount=YEAR_STARS)]
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
            await bot.send_message(user_id, f"✅ <b>تم الدفع بنجاح!</b>\n\nكودك:\n<code>{code}</code>\n\n🚀 استمتع بالنشر التلقائي")
        else:
            await bot.send_message(user_id, "❌ لا توجد أكواد متاحة.")
    
    elif payload == "year_sub":
        await bot.send_message(user_id, "✅ تم الدفع!\n\nأرسل أيدي حسابك في بوت النشر للتفعيل.")
        await bot.send_message(ADMIN_ID, f"🔔 اشتراك سنوي جديد\n👤 {username} ({user_id})")

# ================== CRYPTO PAYMENT ==================
@dp.callback_query(F.data == "crypto")
async def crypto(call: CallbackQuery):
    text = """💰 <b>طرق الدفع</b>

USDT Aptos: `0xf8873fe62b564ff0d8042e84c24277c8cef7ee3beb94be1ab0c5da26a7346f77`
USDT ERC20: `0x66c81a68b27402038066a146f31d4ffdaad5ab46`
USDT Polygon: `0xe280d46e283329240c708ff11fa4871fa4fb3ecc`
USDT BEP20: `0x11a34390ce1526efd7db3e5810d58decb74d9f9f`
USDT TRC20: `TDEd6MN8AigEb3jPtEY36ixkrJ7TF7fszL`
Solana: `GH6yhxN58xG698fp4vb3ELs9QqXbzn7tCWuw3WbYfzpA`
TON: `UQAFk8b4fKqrqrEKVejWTn95E1v0qoPWDC4SGW_pF9uBkdLj`

<b>بعد التحويل:</b>
أرسل السكرين شوت + أيديك"""
    await call.message.answer(text, parse_mode=ParseMode.MARKDOWN)
    await call.answer()

@dp.message(F.photo)
async def handle_photo(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        return
    proof = msg.photo[-1].file_id
    username = msg.from_user.username or "بدون"
    await msg.answer("✅ تم استلام الإيصال.\nأرسل أيديك الآن (مثال: 123456789)")
    # حفظ مؤقت (يمكن تحسينه بـ FSM لاحقاً)
    # هنا نبعت للأدمن مباشرة
    await bot.send_photo(ADMIN_ID, proof, caption=f"🔔 دفع كريبتو جديد\n👤 {username} ({msg.from_user.id})\n\nأرسل الأيدي بعد كده")
    await bot.send_message(ADMIN_ID, "اضغط قبول أو رفض بعد ما تتأكد", reply_markup=accept_reject_kb(999))  # يمكن تعديل الـ ID

# ================== ADMIN HANDLERS ==================
@dp.callback_query(F.data.startswith("accept_") | F.data.startswith("reject_"))
async def handle_payment_action(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    action, pid = call.data.split("_")
    status = "accepted" if action == "accept" else "rejected"
    await update_payment_status(int(pid), status)
    await call.message.edit_text(call.message.text + f"\n\n<b>الحالة: {status.upper()}</b>")
    await call.answer("تم ✅")

@dp.callback_query(F.data.in_(["pending_payments", "manage_codes", "add_codes"]))
async def admin_actions(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return
    if call.data == "add_codes":
        await call.message.answer("📥 أرسل قائمة الأكواد (كل كود في سطر):")
    elif call.data == "pending_payments":
        await call.message.answer("📋 لا توجد دفعات معلقة حالياً (يمكن توسيع النظام).")
    else:
        count = await count_available_codes()
        await call.message.answer(f"📦 الأكواد المتاحة: {count}", reply_markup=admin_menu())
    await call.answer()

@dp.message(Command("addcodes"))
async def add_codes_cmd(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("📥 أرسل قائمة الأكواد (كود في كل سطر):")

@dp.message()
async def handle_all_text(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    lines = [line.strip() for line in msg.text.strip().splitlines() if line.strip()]
    if lines and len(lines[0]) > 8:   # كود عادة أطول من 8 أحرف
        added = await add_codes_list(lines)
        await msg.answer(f"✅ تم إضافة <b>{added}</b> كود بنجاح!")

# ================== MAIN ==================
async def main():
    await init_db()
    print("🚀 البوت شغال بنجاح - النسخة الكاملة")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
