import asyncio
import json
import os
import re
import pytz
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, MessageEntityCustomEmoji
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.extensions import markdown

# --- البيانات الأساسية ---
API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = '5759866264:AAEwiaoo-lT-SI6TQhHMTC59umgnkV5zIm4'
ADMIN_ID = 154919127 # المطور الرئيسي
DEVELOPER_USERNAME = "devazf" # غير ده ليوزرك من غير @
MANDATORY_CHANNEL = "Spraize" # حط @قناتك أو سيبه فاضي ""
DB_FILE = 'hero_data.json'

# --- بيانات الدفع - غيرها ببياناتك ---
PAYMENT_INFO = {
    'vodafone': '01105802898', # رقم فودافون كاش
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH', # محفظة LTC
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt', # محفظة TON
    'usdt': 'TRC20: TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh' # محفظة USDT TRC20
}

PRICE_PACKAGES = {
    '7_days': {'days': 7, 'price': '0.5$ - 25 جنية', 'label': '7 أيام'},
    '15_days': {'days': 15, 'price': '1$ - 50 جنية', 'label': '15 يوم'},
    '30_days': {'days': 30, 'price': '3$ - 100 جنية', 'label': 'شهر كامل'}
}

# --- نظام الحفظ والاشتراكات ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'logs_enabled' not in data:
                    data['logs_enabled'] = True
                if 'pending_payments' not in data:
                    data['pending_payments'] = {}
                if 'show_time' not in data:
                    data['show_time'] = False
                if 'auto_reply_enabled' not in data:
                    data['auto_reply_enabled'] = True
                if 'auto_reply_text' not in data:
                    data['auto_reply_text'] = f'تفضل خاص @{DEVELOPER_USERNAME}'
                if 'welcome_enabled' not in data:
                    data['welcome_enabled'] = True
                if 'welcome_text' not in data:
                    data['welcome_text'] = 'أهلاً بيك في بوت Programmer Azef 🌟\n\nأنا بوت النشر التلقائي المطور\nللاشتراك دوس الزر تحت 👇'
                if 'welcomed_users' not in data:
                    data['welcomed_users'] = []
                if 'use_formatting' not in data:
                    data['use_formatting'] = True
                if 'msg_texts' not in data:
                    data['msg_texts'] = [data.get('msg_text', ''), '', '', '']
                if 'current_msg_index' not in data:
                    data['current_msg_index'] = 0
                if 'msg_stats' not in data:
                    data['msg_stats'] = [0, 0, 0, 0]
                if 'msg_delay' not in data:
                    data['msg_delay'] = 5
                if 'send_all_mode' not in data:
                    data['send_all_mode'] = False
                if 'trial_users' not in data:
                    data['trial_users'] = []
                return data
        except:
            pass
    return {
        'session': None,
        'super_groups': [],
        'sleep_time': 30,
        'msg_delay': 5,
        'msg_texts': ['', '', '', ''],
        'current_msg_index': 0,
        'msg_stats': [0, 0, 0, 0],
        'send_all_mode': False,
        'subs': {str(ADMIN_ID): '2099-01-01'},
        'admins': [ADMIN_ID],
        'pending_payments': {},
        'logs_enabled': True,
        'show_time': False,
        'auto_reply_enabled': True,
        'auto_reply_text': f'تفضل خاص @{DEVELOPER_USERNAME}',
        'welcome_enabled': True,
        'welcome_text': 'أهلاً بيك في بوت Programmer Azef 🌟\n\nأنا بوت النشر التلقائي المطور\nللاشتراك دوس الزر تحت 👇',
        'welcomed_users': [],
        'use_formatting': True,
        'trial_users': []
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()
waiting_for = {}
login_temp = {}
is_posting = False
user_client = None

bot = TelegramClient('Hero_Fix', API_ID, API_HASH)

# --- دوال التحقق والمراقبة ---
def is_admin(uid):
    return uid in db.get('admins', [ADMIN_ID])

def is_main_admin(uid):
    return uid == ADMIN_ID

def is_sub(uid):
    if is_admin(uid):
        return True
    uid = str(uid)
    if uid in db.get('subs', {}):
        try:
            expiry_str = db['subs'][uid]
            if ' ' in expiry_str:
                expiry = datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
            else:
                expiry = datetime.strptime(expiry_str, '%Y-%m-%d')
            if expiry > datetime.now():
                return True
        except:
            pass
    return False

def get_current_time():
    if not db.get('show_time', False):
        return ""
    try:
        tz = pytz.timezone('Africa/Cairo')
        now = datetime.now(tz)
        return f"\n🕐 {now.strftime('%I:%M %p - %d/%m/%Y')}"
    except:
        return ""

def parse_premium_emojis(text):
    entities = []
    new_text = text
    offset_diff = 0

    for match in re.finditer(r'\{premium:(\d+)\}', text):
        doc_id = int(match.group(1))
        start = match.start() - offset_diff
        length = 1

        entities.append(MessageEntityCustomEmoji(
            offset=start,
            length=length,
            document_id=doc_id
        ))

        new_text = new_text[:match.start() - offset_diff] + '⭐' + new_text[match.end() - offset_diff:]
        offset_diff += len(match.group(0)) - 1

    return new_text, entities

async def send_log(event, action, text=""):
    if not db.get('logs_enabled', True):
        return
    try:
        user = await event.get_sender()
        name = user.first_name if user else "Unknown"
        uid = user.id if user else "Unknown"
        log_msg = f"🔔 **إشعار دخول جديد**\n👤 المستخدم: {name}\n🆔 الايدي: `{uid}`\n🔘 الإجراء: {action}\n📥 النص: {text[:100]}{get_current_time()}"
        await bot.send_message(ADMIN_ID, log_msg)
    except:
        pass

async def get_all_groups_from_account():
    if not db['session']:
        return [], "❌ لازم تربط حساب أولاً"

    client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
    groups = []
    try:
        await client.connect()
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Chat):
                groups.append(f"-100{entity.id}")
            elif isinstance(entity, Channel) and entity.megagroup:
                groups.append(f"-100{entity.id}")
        return groups, f"✅ تم جلب {len(groups)} جروب"
    except Exception as e:
        return [], f"❌ خطأ: {str(e)}"
    finally:
        await client.disconnect()

# 🔘 الواجهة الرئيسية
def main_menu(uid):
    btns = [
        [Button.inline("🔑 تسجيل الدخول", b"login_phone")],
        [Button.inline("⚙️ إعدادات النشر", b"settings")],
        [Button.inline("🚀 بدء النشر", b"start_post")]
    ]
    if not is_sub(uid):
        if str(uid) not in db.get('trial_users', []):
            btns.append([Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")])
        btns.append([Button.inline("💳 اشترك الآن", b"payment_menu")])
    if is_admin(uid):
        btns.append([Button.inline("🔐 لوحة الأدمن", b"admin_panel")])
    btns.append([Button.url('👨‍💻 اضغط لـ مـراسلة المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')])
    return btns

# 🔘 واجهة الإعدادات
def settings_menu():
    status = "🟢 مفعل ومربوط" if db['session'] else "🔴 غير مربوط"
    groups_count = len(db['super_groups'])
    logs_status = "🔔 الإشعارات: مفعلة" if db.get('logs_enabled', True) else "🔕 الإشعارات: معطلة"
    time_status = "🕐 الساعة: مفعلة" if db.get('show_time', False) else "🕐 الساعة: معطلة"
    reply_status = "💬 الرد التلقائي: مفعل" if db.get('auto_reply_enabled', True) else "💬 الرد التلقائي: معطل"
    welcome_status = "👋 الترحيب: مفعل" if db.get('welcome_enabled', True) else "👋 الترحيب: معطل"
    format_status = "✨ التنسيق: مفعل" if db.get('use_formatting', True) else "✨ التنسيق: معطل"
    mode_status = "📤 وضع: الكل" if db.get('send_all_mode', False) else "🔄 وضع: تدوير"

    stats = db.get('msg_stats', [0, 0, 0, 0])
    msg_delay = db.get('msg_delay', 5)

    return [
        [Button.inline(status, b"none")],
        [Button.inline(logs_status, b"toggle_logs")],
        [Button.inline(time_status, b"toggle_time")],
        [Button.inline(reply_status, b"toggle_reply")],
        [Button.inline(welcome_status, b"toggle_welcome")],
        [Button.inline(format_status, b"toggle_format")],
        [Button.inline(mode_status, b"toggle_mode")],
        [Button.inline("✏️ تعديل نص الرد", b"edit_reply_text"), Button.inline("✏️ تعديل الترحيب", b"edit_welcome_text")],
        [Button.inline(f"📩 الرسالة 1 ({stats[0]})", b"add_msg_0"), Button.inline(f"📩 الرسالة 2 ({stats[1]})", b"add_msg_1")],
        [Button.inline(f"📩 الرسالة 3 ({stats[2]})", b"add_msg_2"), Button.inline(f"📩 الرسالة 4 ({stats[3]})", b"add_msg_3")],
        [Button.inline("📥 جلب المجموعات تلقائي", b"fetch_groups")],
        [Button.inline(f"👥 السوبرات: {groups_count}", b"show_links")],
        [Button.inline("➕ إضافة يدوي", b"add_links"), Button.inline("👤 ربط حساب", b"login_phone")],
        [Button.inline(f"⏱️ وقت الجروب: {db['sleep_time']}ث", b"set_time"), Button.inline(f"⏱️ وقت الرسالة: {msg_delay}ث", b"set_msg_delay")],
        [Button.inline("🔴 إيقاف", b"stop_post"), Button.inline("🟢 بدء النشر", b"start_post")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

# 🔘 لوحة الأدمن
def admin_panel(uid):
    btns = [
        [Button.inline("➕ تفعيل مشترك", b"add_sub")],
        [Button.inline("👥 قائمة المشتركين", b"list_subs")],
    ]
    if is_main_admin(uid):
        btns.append([Button.inline("⬆️ رفع أدمن", b"add_admin"), Button.inline("⬇️ تنزيل أدمن", b"remove_admin")])
        btns.append([Button.inline("👑 قائمة الادمن", b"list_admins")])
        btns.append([Button.inline("⏳ المدفوعات المعلقة", b"pending_payments")])
    btns.append([Button.inline("🔙 رجوع", b"back_main")])
    return btns

# 🔘 قائمة الدفع
def payment_menu_keyboard():
    return [
        [Button.inline(f'7 أيام - {PRICE_PACKAGES["7_days"]["price"]}', 'pay_7_days')],
        [Button.inline(f'15 يوم - {PRICE_PACKAGES["15_days"]["price"]}', 'pay_15_days')],
        [Button.inline(f'شهر كامل - {PRICE_PACKAGES["30_days"]["price"]}', 'pay_30_days')],
        [Button.inline('🔙 رجوع', 'back_main')]
    ]

def payment_methods_keyboard(package):
    return [
        [Button.inline('📱 فودافون كاش', f'method_vodafone_{package}')],
        [Button.inline('💎 LTC', f'method_ltc_{package}')],
        [Button.inline('💎 TON', f'method_ton_{package}')],
        [Button.inline('💵 USDT TRC20', f'method_usdt_{package}')],
        [Button.inline('🔙 رجوع', 'payment_menu')]
    ]

# --- تشغيل الحساب المربوط للرد التلقائي ---
async def start_user_client():
    global user_client
    if not db['session'] or not db.get('auto_reply_enabled', True):
        return

    try:
        if user_client and user_client.is_connected():
            await user_client.disconnect()

        user_client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
        await user_client.start()

        @user_client.on(events.NewMessage(incoming=True))
        async def auto_reply_handler(event):
            if not db.get('auto_reply_enabled', True):
                return
            if not event.is_group:
                return
            if event.sender_id == (await user_client.get_me()).id:
                return

            me = await user_client.get_me()
            text = event.message.text or ""
            is_mentioned = me.username and f"@{me.username.lower()}" in text.lower()
            is_reply_to_me = event.message.reply_to and event.message.reply_to.reply_to_msg_id

            if is_reply_to_me:
                try:
                    reply_msg = await event.get_reply_message()
                    if reply_msg and reply_msg.sender_id == me.id:
                        is_reply_to_me = True
                    else:
                        is_reply_to_me = False
                except:
                    is_reply_to_me = False

            if is_mentioned or is_reply_to_me:
                try:
                    await event.reply(db.get('auto_reply_text', f'تفضل خاص @{DEVELOPER_USERNAME}'))
                except:
                    pass

        print("✅ الرد التلقائي شغال")
    except Exception as e:
        print(f"❌ خطأ في تشغيل الرد التلقائي: {e}")
        # --- استقبال الأوامر ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    time_display = get_current_time()
    bot_name = f"🚀 **بوت النشر التلقائي المطور - Programmer Azef**{time_display}"

    if event.is_private and db.get('welcome_enabled', True):
        if str(uid) not in db.get('welcomed_users', []):
            welcome_msg = db.get('welcome_text', 'أهلاً بيك 🌟')
            
            btns = [
                [Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")],
                [Button.inline("💳 اشترك الآن", b"payment_menu")],
                [Button.url('👨‍💻 راسل المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')]
            ]
            
            try:
                await bot.send_file(
                    uid,
                    file=WELCOME_PHOTO,
                    caption=f"{welcome_msg}{time_display}",
                    buttons=btns
                )
            except Exception as e:
                print(f"خطأ الصورة: {e}")
                await event.reply(f"{welcome_msg}{time_display}", buttons=btns)
                
            db['welcomed_users'].append(str(uid))
            save_db()
            await send_log(event, "مستخدم جديد", "تم إرسال الترحيب بالصورة")
            return

    if not is_sub(uid):
        btns = []
        if str(uid) not in db.get('trial_users', []):
            btns.append([Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")])
        btns.append([Button.inline("💳 اشترك الآن", b"payment_menu")])
        btns.append([Button.url('👨‍💻 راسل المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')])
        return await event.reply(f"⚠️ **عذراً، اشتراكك غير مفعل**\n\n💳 تقدر تشترك من الزر تحت أو راسل المطور:\n🆔 الايدي: `{uid}`{time_display}", buttons=btns)
    await event.reply(bot_name, buttons=main_menu(uid))
            
        db['welcomed_users'].append(str(uid))
        save_db()
        await send_log(event,"مستخدم جديد", "تم إرسال الترحيب بالصورة")
        return

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_cmd(event):
    if is_admin(event.sender_id):
        await event.reply("👑 **لوحة التحكم:**", buttons=admin_panel(event.sender_id))

# --- محرك النشر الذكي ---
async def auto_publisher(event):
    global is_posting
    if not db['session']:
        return await event.reply("⚠️ سجل دخول أولاً!")

    available_msgs = [(i, msg) for i, msg in enumerate(db['msg_texts']) if msg.strip()]
    if not available_msgs:
        return await event.reply("⚠️ ضيف رسالة واحدة على الأقل من الإعدادات!")
    if not db['super_groups']:
        return await event.reply("⚠️ ضيف سوبرات أولاً أو دوس 'جلب المجموعات تلقائي'!")

    is_posting = True
    client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
    try:
        await client.connect()
        mode_text = "إرسال الكل" if db.get('send_all_mode', False) else "تدوير"
        await event.reply(f"✅ **تم تشغيل المحرك الذكي للنشر..**\n📊 عدد الجروبات: {len(db['super_groups'])}\n📤 الوضع: {mode_text}{get_current_time()}")

        while is_posting:
            for target in db['super_groups']:
                if not is_posting:
                    break
                try:
                    if db.get('send_all_mode', False):
                        for actual_idx, msg_text in available_msgs:
                            if not is_posting:
                                break

                            entities = []
                            text_to_send = msg_text

                            if db.get('use_formatting', True):
                                text_to_send, custom_entities = parse_premium_emojis(msg_text)
                                entities.extend(custom_entities)
                                await client.send_message(
                                    int(target),
                                    text_to_send,
                                    parse_mode='markdown',
                                    formatting_entities=entities if entities else None
                                )
                            else:
                                await client.send_message(int(target), msg_text)

                            db['msg_stats'][actual_idx] += 1
                            save_db()

                            if actual_idx!= available_msgs[-1][0]:
                                await asyncio.sleep(db.get('msg_delay', 5))
                    else:
                        msg_idx = db['current_msg_index'] % len(available_msgs)
                        actual_idx, msg_text = available_msgs[msg_idx]

                        entities = []
                        text_to_send = msg_text

                        if db.get('use_formatting', True):
                            text_to_send, custom_entities = parse_premium_emojis(msg_text)
                            entities.extend(custom_entities)
                            await client.send_message(
                                int(target),
                                text_to_send,
                                parse_mode='markdown',
                                formatting_entities=entities if entities else None
                            )
                        else:
                            await client.send_message(int(target), msg_text)

                        db['msg_stats'][actual_idx] += 1
                        db['current_msg_index'] = (db['current_msg_index'] + 1) % len(available_msgs)
                        save_db()

                    await asyncio.sleep(db['sleep_time'])
                except FloodWaitError as e:
                    await event.reply(f"⚠️ حماية: سأنتظر {e.seconds} ثانية.{get_current_time()}")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"Error sending to {target}: {e}")
                    continue
            await asyncio.sleep(5)
    except Exception as e:
        await event.reply(f"❌ خطأ في المحرك: {str(e)}")
    finally:
        is_posting = False
        await client.disconnect()

@bot.on(events.CallbackQuery)
async def handler(event):
    global is_posting
    data, uid = event.data, event.sender_id

    if data == b"free_trial":
        if str(uid) in db.get('trial_users', []):
            return await event.answer("❌ انت استخدمت التجربة المجانية قبل كده!", alert=True)

        expiry = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        db['subs'][str(uid)] = expiry
        db['trial_users'].append(str(uid))
        save_db()

        await event.edit(f"🎁 **تم تفعيل التجربة المجانية!**\n\n⏰ صالحة لمدة: 1 ساعة\n📅 تنتهي: {expiry}\n\nدوس /start عشان تبدأ", buttons=main_menu(uid))
        await send_log(event, "تجربة مجانية", "تم تفعيل تجربة ساعة من قبل المبرمج")
        return

    if data == b"toggle_logs":
        if not is_main_admin(uid):
            return await event.answer("للمطور فقط!", alert=True)
        db['logs_enabled'] = not db.get('logs_enabled', True)
        save_db()
        status = "مفعلة ✅" if db['logs_enabled'] else "معطلة ❌"
        await event.answer(f"الإشعارات {status}", alert=True)
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"toggle_time":
        db['show_time'] = not db.get('show_time', False)
        save_db()
        status = "مفعلة ✅" if db['show_time'] else "معطلة ❌"
        await event.answer(f"الساعة {status}", alert=True)
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"toggle_reply":
        db['auto_reply_enabled'] = not db.get('auto_reply_enabled', True)
        save_db()
        status = "مفعل ✅" if db['auto_reply_enabled'] else "معطل ❌"
        await event.answer(f"الرد التلقائي {status}", alert=True)

        if db['auto_reply_enabled']:
            asyncio.create_task(start_user_client())
        else:
            if user_client and user_client.is_connected():
                await user_client.disconnect()

        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"toggle_welcome":
        db['welcome_enabled'] = not db.get('welcome_enabled', True)
        save_db()
        status = "مفعل ✅" if db['welcome_enabled'] else "معطل ❌"
        await event.answer(f"الترحيب {status}", alert=True)
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"toggle_format":
        db['use_formatting'] = not db.get('use_formatting', True)
        save_db()
        status = "مفعل ✅" if db['use_formatting'] else "معطل ❌"
        await event.answer(f"التنسيق {status}", alert=True)
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"toggle_mode":
        db['send_all_mode'] = not db.get('send_all_mode', False)
        save_db()
        status = "الكل ✅" if db['send_all_mode'] else "تدوير ✅"
        await event.answer(f"الوضع: {status}", alert=True)
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
        return

    if data == b"edit_reply_text":
        waiting_for[uid] = 'edit_reply_text'
        await event.reply(f"✏️ **النص الحالي:**\n{db.get('auto_reply_text')}\n\nارسل النص الجديد:")
        return

    if data == b"edit_welcome_text":
        waiting_for[uid] = 'edit_welcome_text'
        await event.reply(f"✏️ **نص الترحيب الحالي:**\n{db.get('welcome_text')}\n\nارسل النص الجديد:")
        return

    if data == b"payment_menu":
        await event.edit("💳 **اختر الباقة المناسبة**\n\nكل الباقات تعطيك صلاحية كاملة للبوت:", buttons=payment_menu_keyboard())
        return

    if data.startswith(b'pay_'):
        package = data.decode().split('_')[1] + '_' + data.decode().split('_')[2]
        if package not in PRICE_PACKAGES:
            return
        pkg = PRICE_PACKAGES[package]
        await event.edit(f"💳 **الباقة:** {pkg['label']}\n💰 **السعر:** {pkg['price']}\n\nاختر طريقة الدفع:", buttons=payment_methods_keyboard(package))
        return

    if data.startswith(b'method_'):
        parts = data.decode().split('_')
        method = parts[1]
        package = parts[2] + '_' + parts[3]

        if package not in PRICE_PACKAGES:
            return

        pkg = PRICE_PACKAGES[package]
        info = PAYMENT_INFO[method]

        method_names = {'vodafone': 'فودافون كاش', 'ltc': 'LTC', 'ton': 'TON', 'usdt': 'USDT TRC20'}

        msg = f"💳 **الدفع عبر {method_names[method]}**\n\n"
        msg += f"📦 الباقة: {pkg['label']}\n"
        msg += f"💰 المبلغ: {pkg['price']}\n\n"
        msg += f"📍 **حول على:**\n`{info}`\n\n"
        msg += "⚠️ **مهم جداً:**\n"
        msg += "1. حول المبلغ بالظبط\n"
        msg += "2. خد سكرين شوت أو رقم العملية\n"
        msg += "3. دوس 'أرسلت المبلغ' تحت وابعت الإثبات\n\n"
        msg += "✅ هيتم التفعيل خلال دقائق بعد التأكيد"

        waiting_for[uid] = f"payment_proof_{package}_{method}"

        await event.edit(msg, buttons=[
            [Button.inline('✅ أرسلت المبلغ', f'confirm_payment_{package}_{method}')],
            [Button.inline('🔙 رجوع', f'pay_{package}')]
        ])
        return

    if data.startswith(b'confirm_payment_'):
        parts = data.decode().split('_')
        package = parts[2] + '_' + parts[3]
        method = parts[4]
        waiting_for[uid] = f"payment_proof_{package}_{method}"
        await event.edit("📸 **تمام، ابعت دلوقتي:**\n\n1. سكرين شوت التحويل\n2. أو رقم العملية\n3. أو أي إثبات\n\nالمطور هيأكد ويفعلك فوراً")
        return

    if data.startswith(b'approve_payment_'):
        if not is_main_admin(uid):
            return await event.answer("للمطور فقط!", alert=True)

        parts = data.decode().split('_')
        user_id = int(parts[2])
        package = parts[3] + '_' + parts[4]

        days = PRICE_PACKAGES[package]['days']
        expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        db['subs'][str(user_id)] = expiry
        save_db()

        db['pending_payments'].pop(str(user_id), None)
        save_db()

        await event.edit(f"✅ **تم التفعيل بنجاح**\n\n👤 المستخدم: `{user_id}`\n📦 الباقة: {PRICE_PACKAGES[package]['label']}\n📅 صالح لحد: {expiry}")
        await bot.send_message(user_id, f"✅ **تم تفعيل اشتراكك بنجاح!**\n\n🎁 الباقة: {PRICE_PACKAGES[package]['label']}\n📅 صالح لحد: {expiry}\n\nدوس /start عشان تبدأ", buttons=main_menu(user_id))
        return

    if data.startswith(b'reject_payment_'):
        if not is_main_admin(uid):
            return await event.answer("للمطور فقط!", alert=True)

        user_id = int(data.decode().split('_')[2])
        db['pending_payments'].pop(str(user_id), None)
        save_db()
        await event.edit(f"❌ **تم رفض الطلب**\n\n👤 المستخدم: `{user_id}`")
        await bot.send_message(user_id, "❌ **تم رفض طلب الدفع**\n\nممكن الإثبات مش واضح أو المبلغ غلط.\nراسل المطور للتوضيح:", buttons=[[Button.url('👨‍💻 راسل المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')]])
        return

    if data == b"pending_payments":
        if not is_main_admin(uid):
            return
        pending = db.get('pending_payments', {})
        if not pending:
            return await event.answer("لا يوجد طلبات معلقة", alert=True)

        msg = "⏳ **المدفوعات المعلقة:**\n\n"
        btns = []
        for user_id, info in pending.items():
            msg += f"👤 `{user_id}` - {info['package']} - {info['method']}\n"
            btns.append([Button.inline(f"✅ تفعيل {user_id}", f"approve_payment_{user_id}_{info['package_key']}")])
            btns.append([Button.inline(f"❌ رفض {user_id}", f"reject_payment_{user_id}")])

        btns.append([Button.inline("🔙 رجوع", b"admin_panel")])
        await event.edit(msg, buttons=btns)
        return

    if not is_sub(uid):
        return await event.answer("انتهى اشتراكك!", alert=True)

    await send_log(event, "ضغط زر", data.decode())

    if data == b"settings":
        await event.edit("⚙️ الإعدادات:", buttons=settings_menu())
    elif data == b"back_main":
        await event.edit("🏠 الرئيسية:", buttons=main_menu(uid))
    elif data == b"admin_panel":
        await event.edit("🔐 **لوحة التحكم:**", buttons=admin_panel(uid))
    elif data == b"fetch_groups":
        await event.answer("⏳ جاري جلب المجموعات...", alert=True)
        groups, msg = await get_all_groups_from_account()
        if groups:
            db['super_groups'] = groups
            save_db()
        await event.edit(f"{msg}\n\nارجع للإعدادات عشان تشوف العدد", buttons=settings_menu())
    elif data == b"start_post":
        if is_posting:
            return await event.answer("🚀 يعمل بالفعل!", alert=True)
        asyncio.create_task(auto_publisher(event))
    elif data == b"stop_post":
        is_posting = False
        await event.answer("🛑 توقف النشر.", alert=True)
    elif data == b"add_sub" and is_admin(uid):
        waiting_for[uid] = 'get_id'
        await event.reply("👤 ارسل ايدي المستخدم:")
    elif data == b"add_admin" and is_main_admin(uid):
        waiting_for[uid] = 'get_admin_id'
        await event.reply("⬆️ ارسل ايدي الأدمن الجديد:")
    elif data == b"remove_admin" and is_main_admin(uid):
        waiting_for[uid] = 'remove_admin_id'
        await event.reply("⬇️ ارسل ايدي الأدمن اللي عايز تنزله:")
    elif data == b"list_admins" and is_main_admin(uid):
        admins_list = "\n".join([f"- `{admin}`" for admin in db['admins']])
        await event.reply(f"👑 **قائمة الأدمنز:**\n\n{admins_list}")
    elif data == b"list_subs" and is_admin(uid):
        msg = "👥 المشتركين:\n" + "\n".join([f"- `{k}` ({v})" for k,v in db['subs'].items()])
        await event.reply(msg)
    elif data.startswith(b"add_msg_"):
        msg_index = int(data.decode().split('_')[-1])
        waiting_for[uid] = f'add_msg_{msg_index}'
        current_msg = db['msg_texts'][msg_index] if db['msg_texts'][msg_index] else "فارغة"
        await event.reply(f"📩 **الرسالة {msg_index + 1} الحالية:**\n{current_msg}\n\n**أرسل النص الجديد:**\n\n**التنسيق المدعوم:**\n`**نص**` = عريض\n`__نص__` = مائل\n`> نص` = اقتباس\n`` `نص` `` = كود\n`{{premium:123456789}}` = إيموجي بريميوم\n\nمثال:\n`**عنوان مهم**`\n> __ملاحظة__: {{premium:5368324170671202286}}")
    elif data in [b"add_links", b"set_time", b"set_msg_delay", b"login_phone", b"show_links"]:
        if data == b"show_links":
            res = "\n".join(db['super_groups']) if db['super_groups'] else "لا يوجد."
            return await event.reply(f"👥 السوبرات المضافة حالياً: {len(db['super_groups'])}\n\n{res}")

        waiting_for[uid] = data.decode()

        if data == b"login_phone":
            await event.reply("🔄 أرسل رقم الهاتف المراد ربطه (مع رمز الدولة):")
        elif data == b"add_links":
            await event.reply("🔗 **أرسل روابط السوبرات الآن**\n(كل رابط في سطر واحد، أو معرف المجموعة)")
        elif data == b"set_time":
            await event.reply("⏱️ **أدخل مدة الانتظار بين الجروبات بالثواني**")
        elif data == b"set_msg_delay":
            await event.reply("⏱️ **أدخل مدة الانتظار بين الرسائل بالثواني**")

@bot.on(events.NewMessage)
async def inputs(event):
    uid = event.sender_id
    if not event.text or event.text.startswith('/'):
        if event.photo or event.document:
            step = waiting_for.get(uid)
            if step and step.startswith('payment_proof_'):
                parts = step.split('_')
                package = parts[2] + '_' + parts[3]
                method = parts[4]

                db['pending_payments'][str(uid)] = {
                    'package': PRICE_PACKAGES[package]['label'],
                    'package_key': package,
                    'method': method,
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                save_db()

                method_names = {'vodafone': 'فودافون كاش', 'ltc': 'LTC', 'ton': 'TON', 'usdt': 'USDT'}
                await bot.send_message(
                    ADMIN_ID,
                    f"💰 **طلب دفع جديد**\n\n👤 المستخدم: `{uid}`\n📦 الباقة: {PRICE_PACKAGES[package]['label']}\n💳 الطريقة: {method_names[method]}\n💰 المبلغ: {PRICE_PACKAGES[package]['price']}\n\n👇 الإثبات تحت:",
                    buttons=[
                        [Button.inline('✅ تفعيل', f'approve_payment_{uid}_{package}')],
                        [Button.inline('❌ رفض', f'reject_payment_{uid}')]
                    ]
                )
                await bot.forward_messages(ADMIN_ID, event.message)

                await event.reply("✅ **تم إرسال الإثبات للمطور**\n\nهيتم المراجعة والتفعيل خلال دقائق ⏳")
                waiting_for.pop(uid, None)
        return

    step = waiting_for.pop(uid, None)
    if not step:
        return

    text = event.text.strip()

    if step == 'login_phone':
        login_temp[uid] = {'phone': text}
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_code_request(text)
            login_temp[uid]['client'] = client
            waiting_for[uid] = 'login_code'
            await event.reply('📩 أرسل الكود (مع فواصل مثل 1-2-3-4-5):')
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
            await client.disconnect()
            login_temp.pop(uid, None)

    elif step == 'login_code':
        code = text.replace('-', '')
        temp = login_temp.get(uid)
        if not temp:
            return await event.reply('❌ ابدأ من جديد.')
        client = temp['client']
        try:
            await client.sign_in(temp['phone'], code)
            db['session'] = client.session.save()
            save_db()
            await event.reply('✅ تم ربط الحساب بنجاح!')
            asyncio.create_task(start_user_client())
        except SessionPasswordNeededError:
            waiting_for[uid] = 'login_pass'
            login_temp[uid] = client
            await event.reply('🔒 أرسل كلمة مرور التحقق بخطوتين:')
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
            await client.disconnect()
            login_temp.pop(uid, None)

    elif step == 'login_pass':
        client = login_temp.get(uid)
        if not client:
            return await event.reply('❌ ابدأ من جديد.')
        try:
            await client.sign_in(password=text)
            db['session'] = client.session.save()
            save_db()
            await event.reply('✅ تم ربط الحساب بنجاح!')
            asyncio.create_task(start_user_client())
        except Exception as e:
            await event.reply(f'❌ خطأ: {e}')
        finally:
            await client.disconnect()
            login_temp.pop(uid, None)

    elif step == 'add_links':
        links = [l.strip() for l in text.split('\n') if l.strip()]
        db['super_groups'].extend(links)
        save_db()
        await event.reply(f'✅ تم إضافة {len(links)} سوبر')

    elif step == 'set_time':
        try:
            db['sleep_time'] = int(text)
            save_db()
            await event.reply(f'✅ تم التحديث إلى {text} ثانية')
        except:
            await event.reply('❌ رقم غير صحيح')

    elif step == 'set_msg_delay':
        try:
            db['msg_delay'] = int(text)
            save_db()
            await event.reply(f'✅ تم التحديث إلى {text} ثانية')
        except:
            await event.reply('❌ رقم غير صحيح')

    elif step.startswith('add_msg_'):
        msg_index = int(step.split('_')[-1])
        db['msg_texts'][msg_index] = text
        save_db()
        await event.reply(f'✅ تم حفظ الرسالة {msg_index + 1}')

    elif step == 'get_id' and is_admin(uid):
        try:
            target = int(text)
            expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            db['subs'][str(target)] = expiry
            save_db()
            await event.reply(f'✅ تم تفعيل {target} لمدة شهر')
        except:
            await event.reply('❌ خطأ في الايدي')

    elif step == 'get_admin_id' and is_main_admin(uid):
        try:
            target = int(text)
            if target not in db['admins']:
                db['admins'].append(target)
                save_db()
            await event.reply(f'✅ تم رفع {target} أدمن')
        except:
            await event.reply('❌ خطأ في الايدي')

    elif step == 'remove_admin_id' and is_main_admin(uid):
        try:
            target = int(text)
            if target == ADMIN_ID:
                return await event.reply('❌ مينفعش تنزل المطور الرئيسي')
            if target in db['admins']:
                db['admins'].remove(target)
                save_db()
            await event.reply(f'✅ تم تنزيل {target}')
        except:
            await event.reply('❌ خطأ في الايدي')

    elif step == 'edit_reply_text' and is_main_admin(uid):
        db['auto_reply_text'] = text
        save_db()
        await event.reply('✅ تم تحديث نص الرد التلقائي')

    elif step == 'edit_welcome_text' and is_main_admin(uid):
        db['welcome_text'] = text
        save_db()
        await event.reply('✅ تم تحديث نص الترحيب')

    elif step.startswith('payment_proof_'):
        parts = step.split('_')
        package = parts[2] + '_' + parts[3]
        method = parts[4]

        db['pending_payments'][str(uid)] = {
            'package': PRICE_PACKAGES[package]['label'],
            'package_key': package,
            'method': method,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        save_db()

        method_names = {'vodafone': 'فودافون كاش', 'ltc': 'LTC', 'ton': 'TON', 'usdt': 'USDT'}
        await bot.send_message(
            ADMIN_ID,
            f"💰 **طلب دفع جديد**\n\n👤 المستخدم: `{uid}`\n📦 الباقة: {PRICE_PACKAGES[package]['label']}\n💳 الطريقة: {method_names[method]}\n💰 المبلغ: {PRICE_PACKAGES[package]['price']}\n\n📝 الإثبات:\n{text}",
            buttons=[
                [Button.inline('✅ تفعيل', f'approve_payment_{uid}_{package}')],
                [Button.inline('❌ رفض', f'reject_payment_{uid}')]
            ]
        )

        await event.reply("✅ **تم إرسال الإثبات للمطور**\n\nهيتم المراجعة والتفعيل خلال دقائق ⏳")

# --- بدء التشغيل ---
async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("🚀 البوت اشتغل!")
    if db['session'] and db.get('auto_reply_enabled', True):
        asyncio.create_task(start_user_client())
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
