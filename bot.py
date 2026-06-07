import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

MONTH_STARS = 200
YEAR_STARS = 500
DB_NAME = "bot.db"

# ================== EMOJI DECOR ==================
LOCK = '<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>'
STAR = '<b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>'
PIN = '<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b>'
ROCKET = '<b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>'

def decor(text: str):
    return f"{LOCK} {text} {STAR}"

# ================== DATABASE ==================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS codes (
                code TEXT PRIMARY KEY,
                used BOOLEAN DEFAULT 0,
                used_by INTEGER
            );
        ''')
        await db.commit()

async def add_codes_list(codes_list):
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
                await db.execute("UPDATE codes SET used = 1, used_by = ? WHERE code = ?", (user_id, code))
                await db.commit()
                return code
    return None

# ================== ADDRESSES ==================
ADDRESSES = {
    "usdt_aptos": "0xf8873fe62b564ff0d8042e84c24277c8cef7ee3beb94be1ab0c5da26a7346f77",
    "usdt_erc20": "0x66c81a68b27402038066a146f31d4ffdaad5ab46",
    "usdt_polygon": "0xe280d46e283329240c708ff11fa4871fa4fb3ecc",
    "usdt_bep20": "0x11a34390ce1526efd7db3e5810d58decb74d9f9f",
    "usdt_trc20": "TDEd6MN8AigEb3jPtEY36ixkrJ7TF7fszL",
    "solana": "GH6yhxN58xG698fp4vb3ELs9QqXbzn7tCWuw3WbYfzpA",
    "ltc": "ltc1q9rps52nyug50k95eujjwpvduzg302fs3z9fs98",
    "ton": "UQAFk8b4fKqrqrEKVejWTn95E1v0qoPWDC4SGW_pF9uBkdLj",
}

def crypto_menu_kb():
    kb = InlineKeyboardBuilder()
    for name, data in [
        ("USDT Aptos", "usdt_aptos"), ("USDT ERC20", "usdt_erc20"),
        ("USDT Polygon", "usdt_polygon"), ("USDT BEP20", "usdt_bep20"),
        ("USDT TRC20", "usdt_trc20"), ("Solana", "solana"),
        ("LTC", "ltc"), ("TON", "ton")
    ]:
        kb.button(text=name, callback_data=data)
    kb.adjust(2)
    return kb.as_markup()

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 اشتراك شهري - 200 ⭐", callback_data="buy_month")
    kb.button(text="🛒 اشتراك سنوي - 500 ⭐", callback_data="buy_year")
    kb.button(text="💰 طرق الدفع الكريبتو", callback_data="crypto_menu")
    kb.button(text="📋 الأكواد المتاحة", callback_data="show_codes")
    kb.adjust(1)
    return kb.as_markup()

# ================== BOT SETUP ==================
logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: Message):
    await msg.answer(f"""
{decor("مرحبا بك")} <b>{msg.from_user.first_name}</b> {STAR}

{PIN} بوت اشتراكات النشر التلقائي {ROCKET}
    """.strip(), reply_markup=main_menu())

@dp.callback_query(F.data == "crypto_menu")
async def show_crypto(call: CallbackQuery):
    await call.message.edit_text(f"{decor('اختر طريقة الدفع')}", reply_markup=crypto_menu_kb())

@dp.callback_query(F.data.in_(ADDRESSES.keys()))
async def copy_address(call: CallbackQuery):
    addr = ADDRESSES[call.data]
    name = call.data.upper().replace("_", " ")
    await call.message.answer(f"""
{decor(f'تم نسخ {name}')}

<code>{addr}</code>

{PIN} بعد التحويل أرسل السكرين شوت + أيديك {ROCKET}
    """)
    await call.answer("✅ تم النسخ!")

# Stars Payment
@dp.callback_query(F.data.in_(["buy_month", "buy_year"]))
async def buy_stars(call: CallbackQuery):
    is_month = call.data == "buy_month"
    amount = MONTH_STARS if is_month else YEAR_STARS
    title = "اشتراك شهري" if is_month else "اشتراك سنوي"
    await call.message.answer_invoice(
        title=title,
        description=title,
        payload=call.data + "_sub",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=amount)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)

@dp.message(F.successful_payment)
async def payment_success(msg: Message):
    await msg.answer(f"{decor('تم الدفع بنجاح!')}")

@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("🔧 لوحة الأدمن", reply_markup=InlineKeyboardBuilder().button(text="➕ إضافة أكواد", callback_data="add_codes").as_markup())

@dp.callback_query(F.data == "add_codes")
async def add_codes(call: CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer("أرسل الأكواد (كود في كل سطر)")

@dp.message()
async def handle_message(msg: Message):
    if msg.from_user.id == ADMIN_ID:
        lines = [line.strip() for line in msg.text.splitlines() if line.strip()]
        if lines:
            added = await add_codes_list(lines)
            await msg.answer(f"✅ تم إضافة {added} كود")

async def main():
    await init_db()
    print("🚀 البوت شغال بنجاح")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
