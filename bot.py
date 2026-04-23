import asyncio
import json
import os
import re
import pytz
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, MessageEntityCustomEmoji
from telethon.errors import SessionPasswordNeededError, FloodWaitError, UserNotParticipantError
from telethon.extensions import markdown

# --- البيانات الأساسية ---
API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = '5759866264:AAFO8zeDmjcmENrx_vwiNGwGb95Fff37qxM'
ADMIN_ID = 154919127 # المطور الرئيسي
DEVELOPER_USERNAME = "devazf" # غير ده ليوزرك من غير @
MANDATORY_CHANNEL = "vip6705" # حط @قناتك أو سيبه فاضي ""
DB_FILE = 'hero_data.json'
WELCOME_PHOTO = "IMG_20260423_102854_326.jpg" # الصورة الافتراضية للترحيب

# --- بيانات الدفع - محدثة ---
PAYMENT_INFO = {
    'vodafone': '01105802898', # فودافون كاش
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH', # محفظة LTC
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt', # محفظة TON
    'usdt': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh' # محفظة USDT TRC20
}

PRICE_PACKAGES = {
    '1_day': {'days': 1, 'price': '0.5$ - 25 جنية', 'label': 'يوم واحد'},
    '7_days': {'days': 7, 'price': '2$ - 70 جنية', 'label': '7 أيام'},
    '15_days': {'days': 15, 'price': '3$ - 100 جنية', 'label': '15 يوم'},
    '30_days': {'days': 30, 'price': '5$ - 120 جنية', 'label': '30 يوم'}
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
                if 'welcome_photo' not in data:
                    data['welcome_photo'] = WELCOME_PHOTO
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
                if 'groups_data' not in data:
                    data['groups_data'] = {} # لحفظ اسم + ايدي الجروب
                return data
        except:
            pass
    return {
        'session': None,
        'super_groups': [],
        'groups_data': {},
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
        'welcome_photo': WELCOME_PHOTO,
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
        log_msg = f"🔔 **إشعار مراقبة جديد**\n👤 المستخدم: {name}\n🆔 الايدي: `{uid}`\n🔘 الإجراء: {action}\n📥 النص: {text[:100]}{get_current_time()}"
        await bot.send_message(ADMIN_ID, log_msg)
    except:
        pass

async def get_all_groups_from_account():
    if not db['session']:
        return [], {}, "❌ لازم تربط حساب أولاً"

    client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
    groups = []
    groups_data = {}
    try:
        await client.connect()
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Chat):
                gid = f"-100{entity.id}"
                groups.append(gid)
                groups_data[gid] = entity.title
            elif isinstance(entity, Channel) and entity.megagroup:
                gid = f"-100{entity.id}"
                groups.append(gid)
                groups_data[gid] = entity.title
        return groups, groups_data, f"✅ تم جلب {len(groups)} جروب"
    except Exception as e:
        return [], {}, f"❌ خطأ: {str(e)}"
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
    btns.append([Button.url('👨‍💻 مراسلة المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')])
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
        [Button.inline(f"👥 عرض الجروبات: {groups_count}", b"show_links")],
        [Button.inline("➕ إضافة جروب يدوي", b"add_links"), Button.inline("🗑️ حذف جروب", b"remove_link")],
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
        btns.append([Button.inline("👑 قائمة الأدمنز", b"list_admins")])
        btns.append([Button.inline("⏳ المدفوعات المعلقة", b"pending_payments")])
        btns.append([Button.inline("🖼️ تغيير صورة الترحيب", b"change_welcome_photo")])
    btns.append([Button.inline("🔙 رجوع", b"back_main")])
    return btns

# 🔘 قائمة الدفع
def payment_menu_keyboard():
    return [
        [Button.inline(f'يوم واحد - {PRICE_PACKAGES["1_day"]["price"]}', 'pay_1_day')],
        [Button.inline(f'7 أيام - {PRICE_PACKAGES["7_days"]["price"]}', 'pay_7_days')],
        [Button.inline(f'15 يوم - {PRICE_PACKAGES["15_days"]["price"]}', 'pay_15_days')],
        [Button.inline(f'30 يوم - {PRICE_PACKAGES["30_days"]["price"]}', 'pay_30_days')],
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

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    time_display = get_current_time()
    bot_name = f"🚀 **بوت النشر التلقائي المطور - Programmer Azef**{time_display}"

    if event.is_private and db.get('welcome_enabled', True):
        if str(uid) not in db.get('welcomed_users', []):
            welcome_msg = db.get('welcome_text', 'أهلاً بيك 🌟')
            welcome_photo = db.get('welcome_photo', WELCOME_PHOTO)

            btns = [
                [Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")],
                [Button.inline("💳 اشترك الآن", b"payment_menu")],
                [Button.url('👨‍💻 راسل المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')]
            ]

            try:
                await bot.send_file(
                    uid,
                    file=welcome_photo,
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
    @bot.on(events.CallbackQuery)
async def callbacks(event):
    uid = event.sender_id
    data = event.data

    # التحقق من الاشتراك الإجباري للأعضاء الجدد
    if MANDATORY_CHANNEL and not is_admin(uid):
        try:
            await bot.get_permissions(MANDATORY_CHANNEL, uid)
        except UserNotParticipantError:
            return await event.answer(f"❌ لازم تشترك في القناة أولاً {MANDATORY_CHANNEL}", alert=True)
        except:
            pass

    if data == b"back_main":
        await event.edit("🔙 رجوع للقائمة الرئيسية", buttons=main_menu(uid))
        return

    if data == b"admin_panel":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        await event.edit("🔐 **لوحة تحكم الأدمن**", buttons=admin_panel(uid))
        return

    if data == b"change_welcome_photo":
        if not is_main_admin(uid):
            return await event.answer("للمطور فقط!", alert=True)
        waiting_for[uid] = 'change_welcome_photo'
        current = db.get('welcome_photo', 'مش محددة')
        await event.edit(f"🖼️ **الصورة الحالية:**\n`{current}`\n\n📸 ابعت الصورة الجديدة دلوقتي\n🔗 أو ابعت رابط مباشر للصورة\n\n❌ /cancel للالغاء")
        return

    if data == b"payment_menu":
        await event.edit("💳 **اختر باقة الاشتراك:**", buttons=payment_menu_keyboard())
        return

    if data == b"pay_1_day":
        await event.edit("💳 **اختر طريقة الدفع:**", buttons=payment_methods_keyboard("1_day"))
        return
    if data == b"pay_7_days":
        await event.edit("💳 **اختر طريقة الدفع:**", buttons=payment_methods_keyboard("7_days"))
        return
    if data == b"pay_15_days":
        await event.edit("💳 **اختر طريقة الدفع:**", buttons=payment_methods_keyboard("15_days"))
        return
    if data == b"pay_30_days":
        await event.edit("💳 **اختر طريقة الدفع:**", buttons=payment_methods_keyboard("30_days"))
        return

    if data.startswith(b'method_'):
        parts = data.decode().split('_')
        method = parts[1]
        package = '_'.join(parts[2:])

        pkg_info = PRICE_PACKAGES.get(package)
        if not pkg_info:
            return await event.answer("❌ باقة غير صحيحة", alert=True)

        if method == 'vodafone':
            info = f"📱 **فودافون كاش**\n💵 المبلغ: {pkg_info['price']}\n📞 الرقم: `{PAYMENT_INFO['vodafone']}`\n\n📸 بعد التحويل ابعت سكرين + رقم العملية"
        elif method == 'ltc':
            info = f"💎 **Litecoin LTC**\n💵 المبلغ: {pkg_info['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['ltc']}`\n\n📸 بعد التحويل ابعت سكرين + Hash العملية"
        elif method == 'ton':
            info = f"💎 **Toncoin TON**\n💵 المبلغ: {pkg_info['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['ton']}`\n\n📸 بعد التحويل ابعت سكرين + Hash العملية"
        elif method == 'usdt':
            info = f"💵 **USDT TRC20**\n💵 المبلغ: {pkg_info['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['usdt']}`\n\n📸 بعد التحويل ابعت سكرين + Hash العملية"
        else:
            return await event.answer("❌ طريقة دفع غير صحيحة", alert=True)

        waiting_for[uid] = f'payment_proof_{package}_{method}'
        btns = [[Button.inline("🔙 رجوع", b"payment_menu")]]
        await event.edit(f"{info}\n\n⏰ مدة الباقة: {pkg_info['label']}{get_current_time()}", buttons=btns)
        return

    if data == b"settings":
        if not is_sub(uid):
            return await event.answer("❌ لازم تشترك أول", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    # ====== إدارة الجروبات ======
    if data == b"add_links":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'add_links'
        await event.edit("➕ **إضافة جروب يدوي**\n\nابعت رابط الجروب أو الايدي:\nمثال: `https://t.me/groupname` أو `-1001234567890`\n\n❌ /cancel للالغاء")
        return

    if data == b"remove_link":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        if not db['super_groups']:
            return await event.answer("❌ مفيش جروبات مضافة", alert=True)
        waiting_for[uid] = 'remove_link'
        groups_list = "\n".join([f"{i+1}. {db['groups_data'].get(g, g)}" for i, g in enumerate(db['super_groups'])])
        await event.edit(f"🗑️ **حذف جروب**\n\nاختر رقم الجروب للحذف:\n{groups_list}\n\n❌ /cancel للالغاء")
        return

    if data == b"show_links":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        if not db['super_groups']:
            return await event.answer("❌ مفيش جروبات مضافة", alert=True)
        groups_list = "\n".join([f"{i+1}. {db['groups_data'].get(g, g)}\n `{g}`" for i, g in enumerate(db['super_groups'])])
        await event.edit(f"👥 **الجروبات المضافة: {len(db['super_groups'])}**\n\n{groups_list}", buttons=[[Button.inline("🔙 رجوع", b"settings")]])
        return

    if data == b"fetch_groups":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        if not db['session']:
            return await event.answer("❌ لازم تربط حساب أولاً", alert=True)

        await event.answer("⏳ جاري جلب الجروبات...", alert=False)
        groups, groups_data, msg = await get_all_groups_from_account()

        if groups:
            db['super_groups'] = groups
            db['groups_data'] = groups_data
            save_db()
            await event.edit(f"✅ {msg}\n\nتم إضافة {len(groups)} جروب تلقائياً", buttons=[[Button.inline("🔙 رجوع", b"settings")]])
        else:
            await event.edit(f"❌ {msg}", buttons=[[Button.inline("🔙 رجوع", b"settings")]])
        return

    # باقي الأزرار القديمة
    if data == b"toggle_welcome":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['welcome_enabled'] = not db.get('welcome_enabled', True)
        save_db()
        status = "مفعل ✅" if db['welcome_enabled'] else "معطل ❌"
        await event.answer(f"الترحيب: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"toggle_logs":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['logs_enabled'] = not db.get('logs_enabled', True)
        save_db()
        status = "مفعلة ✅" if db['logs_enabled'] else "معطلة ❌"
        await event.answer(f"الإشعارات: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"toggle_time":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['show_time'] = not db.get('show_time', False)
        save_db()
        status = "مفعلة ✅" if db['show_time'] else "معطلة ❌"
        await event.answer(f"الساعة: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"toggle_reply":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['auto_reply_enabled'] = not db.get('auto_reply_enabled', True)
        save_db()
        status = "مفعل ✅" if db['auto_reply_enabled'] else "معطل ❌"
        await event.answer(f"الرد التلقائي: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"toggle_format":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['use_formatting'] = not db.get('use_formatting', True)
        save_db()
        status = "مفعل ✅" if db['use_formatting'] else "معطل ❌"
        await event.answer(f"التنسيق: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"toggle_mode":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['send_all_mode'] = not db.get('send_all_mode', False)
        save_db()
        status = "وضع الكل 📤" if db['send_all_mode'] else "وضع التدوير 🔄"
        await event.answer(f"الوضع: {status}", alert=True)
        await event.edit("⚙️ **إعدادات النشر التلقائي**", buttons=settings_menu())
        return

    if data == b"edit_welcome_text":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'edit_welcome_text'
        current = db.get('welcome_text', 'مش محدد')
        await event.reply(f"✏️ **النص الحالي:**\n{current}\n\nابعت النص الجديد:")
        return

@bot.on(events.NewMessage)
async def handle_all(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    # التحقق من الاشتراك الإجباري
    if MANDATORY_CHANNEL and not is_admin(uid) and event.is_private:
        try:
            await bot.get_permissions(MANDATORY_CHANNEL, uid)
        except UserNotParticipantError:
            btns = [[Button.url("📢 اشترك في القناة", f"https://t.me/{MANDATORY_CHANNEL.replace('@', '')}")]]
            return await event.reply(f"⚠️ **لازم تشترك في القناة أولاً عشان تستخدم البوت**\n\n👇 دوس الزر تحت واشترك وبعدين ارجع اعمل /start\n\n{MANDATORY_CHANNEL}", buttons=btns)
        except:
            pass

    if text == "/cancel":
        if uid in waiting_for:
            del waiting_for[uid]
            await event.reply("✅ تم الإلغاء")
        return

    step = waiting_for.get(uid)

    # تغيير صورة الترحيب
    if step == 'change_welcome_photo' and is_main_admin(uid):
        if event.photo:
            try:
                path = await event.download_media(file="welcome.jpg")
                db['welcome_photo'] = path
                save_db()
                del waiting_for[uid]
                await event.reply(f"✅ تم تحديث صورة الترحيب\n📁 الملف: `{path}`\n\nجرب تعمل /start من حساب تاني عشان تشوفها")
            except Exception as e:
                await event.reply(f"❌ خطأ في حفظ الصورة: {e}")
        elif text.startswith('http'):
            db['welcome_photo'] = text
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم تحديث رابط صورة الترحيب\n🔗 `{text}`\n\nجرب تعمل /start من حساب تاني عشان تشوفها")
        else:
            await event.reply("❌ ابعت صورة أو رابط صحيح\n❌ /cancel للالغاء")
        return

    # إضافة جروب يدوي
    if step == 'add_links' and is_admin(uid):
        try:
            if text.startswith('https://t.me/'):
                username = text.split('/')[-1]
                entity = await bot.get_entity(username)
                gid = f"-100{entity.id}"
                gname = entity.title
            elif text.startswith('-100'):
                gid = text
                entity = await bot.get_entity(int(gid))
                gname = entity.title
            else:
                return await event.reply("❌ رابط أو ايدي غير صحيح")

            if gid in db['super_groups']:
                await event.reply("⚠️ الجروب مضاف بالفعل")
            else:
                db['super_groups'].append(gid)
                db['groups_data'][gid] = gname
                save_db()
                await event.reply(f"✅ تم إضافة الجروب:\n📝 {gname}\n🆔 `{gid}`")
            del waiting_for[uid]
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}\nتأكد ان البوت أو الحساب المربوط عضو في الجروب")
        return

    # حذف جروب
    if step == 'remove_link' and is_admin(uid):
        try:
            index = int(text) - 1
            if 0 <= index < len(db['super_groups']):
                gid = db['super_groups'][index]
                gname = db['groups_data'].get(gid, gid)
                db['super_groups'].pop(index)
                if gid in db['groups_data']:
                    del db['groups_data'][gid]
                save_db()
                await event.reply(f"✅ تم حذف الجروب:\n📝 {gname}")
            else:
                await event.reply("❌ رقم غير صحيح")
            del waiting_for[uid]
        except:
            await event.reply("❌ ابعت رقم صحيح")
        return

    # تغيير نص الترحيب
    if step == 'edit_welcome_text' and is_admin(uid):
        db['welcome_text'] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تحديث نص الترحيب:\n{text}")
        return

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await start_user_client()
    print("✅ البوت شغال...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
