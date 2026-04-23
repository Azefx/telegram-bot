import asyncio
import json
import os
import pytz
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat
from telethon.errors import UserNotParticipantError, FloodWaitError, PhoneCodeInvalidError

API_ID = int(os.environ.get('API_ID', '33595004'))
API_HASH = os.environ.get('API_HASH', 'cbd1066ed026997f2f4a7c4323b7bda7')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '5759866264:AAFI8depurjcQCUbra62Bzs2paaIdizkEUI')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '154919127'))
DEVELOPER_USERNAME = os.environ.get('DEVELOPER_USERNAME', "devazf")
MANDATORY_CHANNEL = os.environ.get('MANDATORY_CHANNEL', "@vip6705")
HELP_PHOTO = os.environ.get('HELP_PHOTO', 'image.jpg')
DB_FILE = 'poster_data.json'
BACKUP_FILE = 'sessions_backup.json'
MAX_ACCOUNTS = 5

PRICE_PACKAGES = {
    '1_day': {'days': 1, 'price': '0.5$ - 25 جنية', 'label': 'يوم واحد'},
    '7_days': {'days': 7, 'price': '2$ - 70 جنية', 'label': '7 أيام'},
    '15_days': {'days': 15, 'price': '3$ - 100 جنية', 'label': '15 يوم'},
    '30_days': {'days': 30, 'price': '5$ - 120 جنية', 'label': '30 يوم'}
}

PAYMENT_INFO = {
    'vodafone': '01105802898',
    'ltc': 'LZgafAodZxDmjM9Ri51ygZ6dU8UbxE2cPH',
    'ton': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt',
    'usdt': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh'
}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': {},
        'subs': {str(ADMIN_ID): '2099-01-01'},
        'admins': [ADMIN_ID],
        'auto_reply': True,
        'auto_reply_keywords': ['موجود', 'موجود؟', 'موجوده', 'فينك', 'وينك'],
        'auto_reply_keywords_enabled': True,
        'pending': {},
        'welcomed': [],
        'welcome_enabled': True,
        'welcome_text': '🌟 **أهلاً بيك في بوت النشر المطور**\n\n🚀 أسرع بوت نشر تلقائي على تليجرام\n⚡ نشر في مئات الجروبات بضغطة زر\n💎 مميزات احترافية\n👇 اختار من الأزرار تحت',
        'welcome_photo': 'image.jpg',
        'start_photo': 'image.jpg',
        'trial_users': [],
        'stats': {'total_sent': 0, 'start_time': str(datetime.now())}
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def backup_all_sessions():
    backup = {
        'backup_time': str(datetime.now()),
        'total_sessions': 0,
        'sessions': []
    }

    for uid, user_data in db['users'].items():
        for acc_id, acc in user_data['accounts'].items():
            if acc['session']:
                backup['sessions'].append({
                    'user_id': uid,
                    'account_id': acc_id,
                    'account_name': acc['name'],
                    'phone': acc['phone'],
                    'username': acc['username'],
                    'session': acc['session'],
                    'linked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                backup['total_sessions'] += 1

    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    return backup['total_sessions']

def get_account_template():
    return {
        'session': None,
        'phone': None,
        'username': None,
        'groups': {},
        'messages': ['', '', '', ''],
        'current_msg': 0,
        'msg_stats': [0, 0, 0, 0],
        'sleep_time': 60,
        'msg_delay': 5,
        'send_all': False,
        'banned_groups': [],
        'is_posting': False,
        'name': 'حساب جديد',
        'reply_mention_text': f'تفضل خاص @{DEVELOPER_USERNAME}',
        'reply_keyword_text': 'موجود يا غالي 🌚'
    }

def get_user_data(uid):
    uid = str(uid)
    if uid not in db['users']:
        db['users'][uid] = {
            'accounts': {},
            'active_account': None
        }
        save_db()
    return db['users'][uid]

def get_active_account(uid):
    user = get_user_data(uid)
    if not user['active_account'] or user['active_account'] not in user['accounts']:
        return None
    return user['accounts'][user['active_account']]

db = load_db()
bot = TelegramClient('PosterBot', API_ID, API_HASH)
waiting_for = {}
login_sessions = {}
active_clients = {}

def is_admin(uid):
    return uid in db['admins']

def is_main_admin(uid):
    return uid == ADMIN_ID

def is_sub(uid):
    if is_admin(uid):
        return True
    if str(uid) in db['subs']:
        try:
            expiry = datetime.strptime(db['subs'][str(uid)], '%Y-%m-%d %H:%M')
            return expiry > datetime.now()
        except:
            try:
                expiry = datetime.strptime(db['subs'][str(uid)], '%Y-%m-%d')
                return expiry > datetime.now()
            except:
                pass
    if str(uid) in db['trial_users']:
        return True
    return False

def get_time():
    tz = pytz.timezone('Africa/Cairo')
    return datetime.now(tz).strftime('\n🕐 %I:%M %p - %d/%m/%Y')

def get_uptime():
    start = datetime.strptime(db['stats']['start_time'], '%Y-%m-%d %H:%M:%S.%f')
    diff = datetime.now() - start
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    return f"{days} يوم, {hours} ساعة, {minutes} دقيقة"

def main_menu(uid):
    btns = [
        [Button.inline("🔑 إدارة الحسابات", b"accounts")],
        [Button.inline("⚙️ الإعدادات", b"settings")],
        [Button.inline("📊 الإحصائيات", b"stats")],
        [Button.inline("❓ المساعدة", b"help")]
    ]

    if not is_sub(uid) and str(uid) not in db['trial_users']:
        btns.append([Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")])

    if not is_sub(uid):
        btns.append([Button.inline("💳 اشترك الآن", b"pay_menu")])

    if is_admin(uid):
        btns.append([Button.inline("👑 لوحة الأدمن", b"admin")])

    btns.append([Button.url("👨‍💻 المبرمج", f"https://t.me/{DEVELOPER_USERNAME}")])
    return btns

def accounts_menu(uid):
    user = get_user_data(uid)
    btns = []

    for acc_id, acc in user['accounts'].items():
        status = "🟢" if acc['session'] else "🔴"
        active = "✅" if user['active_account'] == acc_id else ""
        name = acc.get('name', f'حساب {acc_id}')
        phone = acc.get('phone', 'غير مربوط')
        btns.append([Button.inline(f"{active} {status} {name} - {phone}", f"acc_{acc_id}".encode())])

    if len(user['accounts']) < MAX_ACCOUNTS:
        btns.append([Button.inline("➕ إضافة حساب جديد", b"add_account")])

    btns.append([Button.inline("🔙 رجوع", b"back")])
    return btns

def account_control(uid, acc_id):
    acc = get_user_data(uid)['accounts'][acc_id]
    status = "🟢 مربوط" if acc['session'] else "🔴 غير مربوط"
    posting = "🔴 إيقاف النشر" if acc['is_posting'] else "🟢 بدء النشر"

    return [
        [Button.inline(status, b"none")],
        [Button.inline(f"📝 الاسم: {acc['name']}", b"none")],
        [Button.inline("✏️ تغيير الاسم", f"rename_{acc_id}".encode())],
        [Button.inline("🔑 ربط الحساب", f"login_{acc_id}".encode()), Button.inline("🗑️ حذف الحساب", f"del_acc_{acc_id}".encode())],
        [Button.inline(posting, f"toggle_post_{acc_id}".encode())],
        [Button.inline("🔙 رجوع", b"accounts")]
    ]

def settings_menu(uid):
    acc = get_active_account(uid)
    if not acc:
        return [[Button.inline("❌ اختار حساب أول", b"accounts")], [Button.inline("🔙 رجوع", b"back")]]

    status = "🟢 مربوط" if acc['session'] else "🔴 غير مربوط"
    mode = "📤 الكل" if acc['send_all'] else "🔄 تدوير"
    reply_group = "✅ مفعل" if db['auto_reply'] else "❌ معطل"
    keywords = "✅ مفعل" if db['auto_reply_keywords_enabled'] else "❌ معطل"
    welcome = "✅ مفعل" if db['welcome_enabled'] else "❌ معطل"

    btns = [
        [Button.inline(f"📱 {acc['name']} - {status}", b"accounts")],
        [Button.inline(f"👥 الجروبات: {len(acc['groups'])}", b"show_groups")],
        [Button.inline("📥 جلب تلقائي", b"fetch"), Button.inline("➕ إضافة جروب", b"add_group")],
        [Button.inline("🗑️ حذف جروب", b"delete_group"), Button.inline("🚫 الجروبات المحظورة", b"banned")],
        [Button.inline(f"📩 رسالة 1 ({acc['msg_stats'][0]})", b"msg_0"), Button.inline(f"📩 رسالة 2 ({acc['msg_stats'][1]})", b"msg_1")],
        [Button.inline(f"📩 رسالة 3 ({acc['msg_stats'][2]})", b"msg_2"), Button.inline(f"📩 رسالة 4 ({acc['msg_stats'][3]})", b"msg_3")],
        [Button.inline(f"⏱️ وقت الجروب: {acc['sleep_time']}ث", b"set_sleep"), Button.inline(f"⏱️ وقت الرسالة: {acc['msg_delay']}ث", b"set_delay")],
        [Button.inline(mode, b"toggle_mode")],
        [Button.inline(f"💬 رد المنشن: {reply_group}", b"toggle_reply"), Button.inline(f"🔤 رد الكلمات: {keywords}", b"toggle_keywords")],
        [Button.inline("💬 نص رد المنشن", b"edit_mention_reply"), Button.inline("🔤 نص رد الكلمات", b"edit_keyword_reply")],
    ]

    if is_admin(uid):
        btns.append([Button.inline(f"👋 الترحيب: {welcome}", b"toggle_welcome"), Button.inline("🖼️ صورة الترحيب", b"change_photo")])
        btns.append([Button.inline("✏️ نص الترحيب", b"edit_welcome"), Button.inline("🔤 كلمات الرد", b"edit_keywords")])
        btns.append([Button.inline("🖼️ صورة /start", b"change_start_photo")])

    if acc['is_posting']:
        btns.append([Button.inline("🔴 إيقاف النشر", b"stop")])
    else:
        btns.append([Button.inline("🟢 بدء النشر", b"start")])

    btns.append([Button.inline("🔙 رجوع", b"back")])
    return btns

def admin_panel(uid):
    btns = [
        [Button.inline("➕ إضافة اشتراك", b"add_sub"), Button.inline("➖ إزالة اشتراك", b"remove_sub")],
        [Button.inline("👥 قائمة المشتركين", b"list_subs"), Button.inline("📋 الطلبات المعلقة", b"pending")],
        [Button.inline("💾 نسخة احتياطية للجلسات", b"backup_sessions")],
        [Button.inline("📢 إذاعة", b"broadcast"), Button.inline("🔄 إعادة تشغيل", b"restart")],
        [Button.inline("🔙 رجوع", b"back")]
    ]
    return btns

def pay_menu():
    btns = []
    for key, pkg in PRICE_PACKAGES.items():
        btns.append([Button.inline(f"{pkg['label']} - {pkg['price']}", f"pay_{key}".encode())])
    btns.append([Button.inline("🔙 رجوع", b"back")])
    return btns

def payment_methods(pkg_key):
    return [
        [Button.inline(f"📱 فودافون كاش", f"method_vodafone_{pkg_key}".encode())],
        [Button.inline(f"💎 USDT TRC20", f"method_usdt_{pkg_key}".encode())],
        [Button.inline(f"💎 Litecoin", f"method_ltc_{pkg_key}".encode())],
        [Button.inline(f"💎 Toncoin", f"method_ton_{pkg_key}".encode())],
        [Button.inline("🔔 دفعت - إشعار المطور", f"notify_{pkg_key}".encode())],
        [Button.inline("🔙 رجوع", b"pay_menu")]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    get_user_data(uid)

    if MANDATORY_CHANNEL and not is_admin(uid):
        try:
            await bot.get_permissions(MANDATORY_CHANNEL, uid)
        except UserNotParticipantError:
            btns = [[Button.url("📢 اشترك الآن", f"https://t.me/{MANDATORY_CHANNEL.replace('@', '')}")]]
            return await event.reply(f"⚠️ **لازم تشترك في القناة أولاً**\n\n{MANDATORY_CHANNEL}\n\nبعد الاشتراك ارجع اعمل /start", buttons=btns)
        except:
            pass

    if db['welcome_enabled'] and is_admin(uid) and str(uid) not in db['welcomed']:
        db['welcomed'].append(str(uid))
        save_db()

        welcome_btns = [
            [Button.inline("⚙️ الإعدادات", b"settings")],
            [Button.inline("🚀 بدء النشر", b"start")],
            [Button.url("👨‍💻 المبرمج", f"https://t.me/{DEVELOPER_USERNAME}")]
        ]

        try:
            await bot.send_file(uid, file=db['welcome_photo'], caption=f"{db['welcome_text']}{get_time()}", buttons=welcome_btns)
            return
        except:
            await event.reply(f"{db['welcome_text']}{get_time()}", buttons=welcome_btns)
            return

    if not is_sub(uid):
        btns = []
        if str(uid) not in db['trial_users']:
            btns.append([Button.inline("🎁 تجربة مجانية 1 ساعة", b"free_trial")])
        btns.append([Button.inline("💳 اشترك الآن", b"pay_menu")])
        btns.append([Button.url("👨‍💻 المبرمج", f"https://t.me/{DEVELOPER_USERNAME}")])

        caption = f"🚀 **بوت النشر التلقائي المطور**\n⚠️ **اشتراكك غير مفعل**\n🆔 ايديك: `{uid}`{get_time()}"

        try:
            await bot.send_file(uid, file=db['start_photo'], caption=caption, buttons=btns)
        except:
            await event.reply(caption, buttons=btns)
        return

    caption = f"🚀 **بوت النشر التلقائي المطور**\n\n✅ اشتراكك مفعل\n\n👇 اختار من الأزرار تحت{get_time()}"

    try:
        await bot.send_file(uid, file=db['start_photo'], caption=caption, buttons=main_menu(uid))
    except:
        await event.reply(caption, buttons=main_menu(uid))

@bot.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    uid = event.sender_id
    get_user_data(uid)

    if is_admin(uid):
        help_text = f"""
🚀 **أوامر بوت النشر المطور**

**👤 أوامر المستخدمين:**
/start - القائمة الرئيسية
/help - عرض المساعدة

**👑 أوامر الأدمن:**
/activate user_id package_key - تفعيل اشتراك
مثال: `/activate 123456789 7_days`

**⚙️ المميزات:**
- 🔑 5 حسابات لكل مستخدم
- 📥 جلب تلقائي لكل الجروبات
- ➕ إضافة/حذف جروبات يدوي
- 📩 4 رسائل مختلفة لكل حساب
- 🔄 وضع التدوير أو نشر الكل
- ⏱️ تحكم كامل في الأوقات
- 💬 رد تلقائي على المنشن والكلمات - كل حساب ليه نص منفصل
- 🎁 تجربة مجانية ساعة
- 💳 نظام اشتراكات متكامل
- 💾 نسخ احتياطي للجلسات

**📞 الدعم:** @{DEVELOPER_USERNAME}
{get_time()}
"""
    else:
        help_text = f"""
🚀 **بوت النشر التلقائي المطور**

**📋 الأوامر المتاحة:**
/start - القائمة الرئيسية
/help - عرض المساعدة

**⚙️ المميزات:**
- 🔑 اربط لحد 5 حسابات تليجرام
- 📥 اجلب كل جروباتك تلقائياً
- ➕ ضيف جروبات يدوي بالرابط
- 📩 ضيف 4 رسائل مختلفة لكل حساب
- 🔄 اختار وضع التدوير أو نشر الكل
- ⏱️ اظبط وقت الانتظار بين الجروبات
- 💬 رد تلقائي على المنشن والكلمات - نص خاص لكل حساب
- 🎁 تجربة مجانية لمدة ساعة

**💳 الاشتراك:**
استخدم /start وبعدين "💳 اشترك الآن"

**📞 الدعم الفني:** @{DEVELOPER_USERNAME}
{get_time()}
"""

    try:
        await bot.send_file(uid, file=HELP_PHOTO, caption=help_text)
    except:
        await event.reply(help_text)

@bot.on(events.NewMessage(pattern='/activate'))
async def activate_sub(event):
    if not is_admin(event.sender_id):
        return

    try:
        parts = event.raw_text.split()
        user_id = parts[1]
        pkg_key = parts[2]
        pkg = PRICE_PACKAGES[pkg_key]

        expiry = datetime.now() + timedelta(days=pkg['days'])
        db['subs'][user_id] = expiry.strftime('%Y-%m-%d')

        if user_id in db['pending']:
            del db['pending'][user_id]
        if user_id in db['trial_users']:
            db['trial_users'].remove(user_id)

        save_db()
        await event.reply(f"✅ تم تفعيل اشتراك `{user_id}`\n📦 {pkg['label']}\n📅 ينتهي: {expiry.strftime('%Y-%m-%d')}")

        try:
            await bot.send_message(int(user_id), f"🎉 **تم تفعيل اشتراكك!**\n📦 الباقة: {pkg['label']}\n⏰ المدة: {pkg['days']} يوم\n📅 ينتهي: {expiry.strftime('%Y-%m-%d')}{get_time()}")
        except:
            pass
    except:
        await event.reply("❌ الاستخدام: `/activate user_id package_key`\nمثال: `/activate 123456789 7_days`")

@bot.on(events.CallbackQuery)
async def callbacks(event):
    uid = event.sender_id
    data = event.data
    user = get_user_data(uid)
    acc = get_active_account(uid)

    if data == b"back":
        await event.edit("🔙 القائمة الرئيسية", buttons=main_menu(uid))
        return

    if data == b"help":
        await help_command(event)
        return

    if data == b"accounts":
        await event.edit(f"🔑 **إدارة الحسابات**\n\nعدد الحسابات: {len(user['accounts'])}/{MAX_ACCOUNTS}", buttons=accounts_menu(uid))
        return

    if data == b"add_account":
        if len(user['accounts']) >= MAX_ACCOUNTS:
            return await event.answer(f"❌ الحد الأقصى {MAX_ACCOUNTS} حسابات", alert=True)

        new_id = str(len(user['accounts']) + 1)
        while new_id in user['accounts']:
            new_id = str(int(new_id) + 1)

        user['accounts'][new_id] = get_account_template()
        user['accounts'][new_id]['name'] = f'حساب {new_id}'
        user['active_account'] = new_id
        save_db()
        await event.edit(f"✅ تم إضافة {user['accounts'][new_id]['name']}\n\nالآن اربط الحساب:", buttons=account_control(uid, new_id))
        return

    if data.startswith(b'acc_'):
        acc_id = data.decode().replace('acc_', '')
        if acc_id in user['accounts']:
            user['active_account'] = acc_id
            save_db()
            await event.edit(f"📱 **{user['accounts'][acc_id]['name']}**", buttons=account_control(uid, acc_id))
        return

    if data.startswith(b'rename_'):
        acc_id = data.decode().replace('rename_', '')
        waiting_for[uid] = f'rename_acc_{acc_id}'
        await event.edit(f"✏️ **تغيير اسم الحساب**\n\nالاسم الحالي: {user['accounts'][acc_id]['name']}\n\nابعت الاسم الجديد:")
        return

    if data.startswith(b'login_'):
        acc_id = data.decode().replace('login_', '')
        if uid in login_sessions:
            del login_sessions[uid]
        waiting_for[uid] = f'phone_{acc_id}'
        await event.edit("📱 **ربط حساب**\n\nابعت رقمك مع كود الدولة\nمثال: `+201234567890`\n\n❌ /cancel للالغاء")
        return

    if data.startswith(b'del_acc_'):
        acc_id = data.decode().replace('del_acc_', '')
        if acc_id in user['accounts']:
            client_key = f"{uid}_{acc_id}"
            if client_key in active_clients:
                try:
                    await active_clients[client_key].disconnect()
                except:
                    pass
                del active_clients[client_key]

            del user['accounts'][acc_id]
            if user['active_account'] == acc_id:
                user['active_account'] = next(iter(user['accounts'])) if user['accounts'] else None
            save_db()
            await event.answer("✅ تم حذف الحساب", alert=True)
            await event.edit(f"🔑 **إدارة الحسابات**", buttons=accounts_menu(uid))
        return

    if data.startswith(b'toggle_post_'):
        acc_id = data.decode().replace('toggle_post_', '')
        if acc_id in user['accounts']:
            acc = user['accounts'][acc_id]
            if acc['is_posting']:
                acc['is_posting'] = False
                save_db()
                await event.answer("🔴 تم إيقاف النشر", alert=True)
            else:
                if not acc['session']:
                    return await event.answer("❌ اربط الحساب أول", alert=True)
                asyncio.create_task(start_posting_uid(uid, acc_id))
                await event.answer("🟢 بدأ النشر", alert=True)
            await event.edit(f"📱 **{acc['name']}**", buttons=account_control(uid, acc_id))
        return

    if data == b"free_trial":
        if str(uid) in db['trial_users']:
            return await event.answer("❌ استخدمت التجربة قبل كده", alert=True)
        if is_sub(uid):
            return await event.answer("✅ انت مشترك بالفعل", alert=True)

        expiry = datetime.now() + timedelta(hours=1)
        db['trial_users'].append(str(uid))
        db['subs'][str(uid)] = expiry.strftime('%Y-%m-%d %H:%M')
        save_db()
        await event.edit(f"🎁 **تم تفعيل التجربة المجانية**\n⏰ صالحة لمدة ساعة\n\nارجع اعمل /start", buttons=main_menu(uid))
        return

    if data == b"pay_menu":
        await event.edit("💳 **اختر الباقة المناسبة:**", buttons=pay_menu())
        return

    if data.startswith(b'pay_'):
        pkg_key = data.decode().replace('pay_', '')
        await event.edit(f"💳 **اختر طريقة الدفع:**", buttons=payment_methods(pkg_key))
        return

    if data.startswith(b'method_'):
        parts = data.decode().split('_')
        method = parts[1]
        pkg_key = '_'.join(parts[2:])
        pkg = PRICE_PACKAGES[pkg_key]

        waiting_for[uid] = f'proof_{pkg_key}_{method}'

        if method == 'vodafone':
            info = f"📱 **فودافون كاش**\n💵 المبلغ: {pkg['price']}\n📞 الرقم: `{PAYMENT_INFO['vodafone']}`"
        elif method == 'usdt':
            info = f"💵 **USDT TRC20**\n💵 المبلغ: {pkg['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['usdt']}`"
        elif method == 'ltc':
            info = f"💎 **Litecoin**\n💵 المبلغ: {pkg['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['ltc']}`"
        elif method == 'ton':
            info = f"💎 **Toncoin**\n💵 المبلغ: {pkg['price']}\n📬 المحفظة:\n`{PAYMENT_INFO['ton']}`"

        msg = f"{info}\n\n📸 **بعد التحويل:**\nابعت سكرين + رقم/هاش العملية\n\n⏰ مدة الباقة: {pkg['label']}"
        await event.edit(msg, buttons=[[Button.inline("🔙 رجوع", b"pay_menu")]])
        return

    if data.startswith(b'notify_'):
        pkg_key = data.decode().replace('notify_', '')
        pkg = PRICE_PACKAGES[pkg_key]

        admin_msg = f"🔔 **إشعار دفع جديد**\n\n"
        admin_msg += f"👤 المستخدم: `{uid}`\n"
        admin_msg += f"📛 الاسم: {event.sender.first_name}\n"
        admin_msg += f"📦 الباقة: {pkg['label']}\n"
        admin_msg += f"💵 السعر: {pkg['price']}\n"
        admin_msg += f"🆔 اليوزر: @{event.sender.username if event.sender.username else 'مفيش'}\n\n"
        admin_msg += f"لتفعيل: `/activate {uid} {pkg_key}`"

        try:
            await bot.send_message(ADMIN_ID, admin_msg)
            await event.answer("✅ تم إرسال إشعار للمطور\nهيتواصل معاك قريب", alert=True)
        except:
            await event.answer("❌ فشل الإرسال، كلم المطور مباشر", alert=True)
        return

    if data == b"settings":
        if not is_sub(uid):
            return await event.answer("❌ لازم تشترك أول", alert=True)
        await event.edit("⚙️ **الإعدادات المتقدمة**", buttons=settings_menu(uid))
        return

    if data == b"stats":
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        total_sent = sum(acc['msg_stats'])
        uptime = get_uptime()
        active_groups = len([g for g in acc['groups'] if g not in acc['banned_groups']])

        msg = f"📊 **إحصائيات {acc['name']}**\n\n"
        msg += f"⏱️ مدة التشغيل: `{uptime}`\n"
        msg += f"📤 رسائلك: `{total_sent}`\n"
        msg += f"👥 جروباتك: `{active_groups}`\n"
        msg += f"🚫 محظور: `{len(acc['banned_groups'])}`\n{get_time()}"

        await event.answer(msg, alert=True)
        return

    if data == b"fetch":
        if not acc or not acc['session']:
            return await event.answer("❌ اربط حساب أول", alert=True)

        await event.answer("⏳ جاري الجلب...", alert=False)
        try:
            client_key = f"{uid}_{user['active_account']}"
            if client_key not in active_clients:
                active_clients[client_key] = TelegramClient(StringSession(acc['session']), API_ID, API_HASH)
                await active_clients[client_key].start()

            client = active_clients[client_key]

            groups = {}
            async for dialog in client.iter_dialogs():
                if isinstance(dialog.entity, (Channel, Chat)) and getattr(dialog.entity, 'megagroup', False):
                    gid = f"-100{dialog.entity.id}"
                    if gid not in acc['banned_groups']:
                        groups[gid] = dialog.entity.title

            acc['groups'] = groups
            save_db()
            await event.edit(f"✅ تم جلب {len(groups)} جروب", buttons=settings_menu(uid))
        except Exception as e:
            await event.edit(f"❌ خطأ: {e}", buttons=settings_menu(uid))
        return

    if data == b"show_groups":
        if not acc or not acc['groups']:
            return await event.answer("❌ مفيش جروبات", alert=True)
        active = [name for gid, name in acc['groups'].items() if gid not in acc['banned_groups']]
        text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(active[:30])])
        if len(active) > 30:
            text += f"\n\n... و {len(active)-30} جروب تاني"
        await event.answer(text, alert=True)
        return

    if data == b"add_group":
        waiting_for[uid] = 'add_group'
        await event.edit("➕ **إضافة جروب يدوي**\n\nابعت رابط الجروب أو الايدي:\n`https://t.me/groupname` أو `-1001234567890`\n\n❌ /cancel للالغاء")
        return

    if data == b"delete_group":
        if not acc or not acc['groups']:
            return await event.answer("❌ مفيش جروبات مضافة", alert=True)
        waiting_for[uid] = 'delete_group'
        groups_list = "\n".join([f"{i+1}. {name}" for i, name in enumerate(acc['groups'].values())])
        await event.edit(f"🗑️ **حذف جروب**\n\nاختر رقم الجروب:\n{groups_list[:3000]}\n\n❌ /cancel للالغاء")
        return

    if data == b"banned":
        if not acc or not acc['banned_groups']:
            return await event.answer("✅ مفيش جروبات محظورة", alert=True)
        text = "\n".join([f"{i+1}. {gid}" for i, gid in enumerate(acc['banned_groups'][:20])])
        await event.answer(f"🚫 **الجروبات المحظورة:**\n{text}", alert=True)
        return

    if data.startswith(b'msg_'):
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        idx = int(data.decode().split('_')[1])
        waiting_for[uid] = f'set_msg_{idx}'
        current = acc['messages'][idx] or 'فاضي'
        await event.edit(f"✏️ **الرسالة {idx+1}**\n\nالحالية:\n{current[:500]}\n\nابعت النص الجديد:")
        return

    if data == b"set_sleep":
        waiting_for[uid] = 'set_sleep'
        await event.edit(f"⏱️ **وقت الانتظار بين الجروبات**\n\nالحالي: {acc['sleep_time']} ثانية\n\nابعت الوقت الجديد (بالثواني):")
        return

    if data == b"set_delay":
        waiting_for[uid] = 'set_delay'
        await event.edit(f"⏱️ **وقت الانتظار بين الرسائل**\n\nالحالي: {acc['msg_delay']} ثانية\n\nابعت الوقت الجديد:")
        return

    if data == b"toggle_mode":
        acc['send_all'] = not acc['send_all']
        save_db()
        mode = "وضع الكل 📤" if acc['send_all'] else "وضع التدوير 🔄"
        await event.answer(f"✅ {mode}", alert=True)
        await event.edit("⚙️ **الإعدادات**", buttons=settings_menu(uid))
        return

    if data == b"toggle_reply":
        db['auto_reply'] = not db['auto_reply']
        save_db()
        
                status = "مفعل ✅" if db['auto_reply'] else "معطل ❌"
        await event.answer(f"الرد على المنشن: {status}", alert=True)
        await event.edit("⚙️ **الإعدادات**", buttons=settings_menu(uid))
        return

    if data == b"toggle_keywords":
        db['auto_reply_keywords_enabled'] = not db['auto_reply_keywords_enabled']
        save_db()
        status = "مفعل ✅" if db['auto_reply_keywords_enabled'] else "معطل ❌"
        await event.answer(f"الرد على الكلمات: {status}", alert=True)
        await event.edit("⚙️ **الإعدادات**", buttons=settings_menu(uid))
        return

    if data == b"edit_mention_reply":
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        waiting_for[uid] = 'edit_mention_reply'
        await event.edit(f"💬 **نص رد المنشن الحالي:**\n{acc['reply_mention_text']}\n\nابعت النص الجديد:")
        return

    if data == b"edit_keyword_reply":
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        waiting_for[uid] = 'edit_keyword_reply'
        await event.edit(f"🔤 **نص رد الكلمات الحالي:**\n{acc['reply_keyword_text']}\n\nابعت النص الجديد:")
        return

    if data == b"toggle_welcome":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        db['welcome_enabled'] = not db['welcome_enabled']
        save_db()
        status = "مفعل ✅" if db['welcome_enabled'] else "معطل ❌"
        await event.answer(f"الترحيب: {status}", alert=True)
        await event.edit("⚙️ **الإعدادات**", buttons=settings_menu(uid))
        return

    if data == b"change_photo":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'change_photo'
        await event.edit(f"🖼️ **الصورة الحالية:**\n{db['welcome_photo']}\n\n📸 ابعت صورة جديدة أو رابط مباشر\n❌ /cancel للالغاء")
        return

    if data == b"change_start_photo":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'change_start_photo'
        await event.edit(f"🖼️ **صورة /start الحالية:**\n{db['start_photo']}\n\n📸 ابعت صورة جديدة أو رابط مباشر\n❌ /cancel للالغاء")
        return

    if data == b"edit_welcome":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'edit_welcome'
        await event.edit(f"✏️ **النص الحالي:**\n{db['welcome_text']}\n\nابعت النص الجديد:")
        return

    if data == b"edit_keywords":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'edit_keywords'
        keywords = ', '.join(db['auto_reply_keywords'])
        await event.edit(f"🔤 **الكلمات الحالية:**\n{keywords}\n\nابعت الكلمات الجديدة مفصولة بفاصلة:\nمثال: `موجود, فينك, وينك, متاح`")
        return

    if data == b"start":
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        asyncio.create_task(start_posting_uid(uid, user['active_account']))
        return

    if data == b"stop":
        if not acc:
            return await event.answer("❌ اختار حساب أول", alert=True)
        acc['is_posting'] = False
        save_db()
        await event.answer("🔴 تم إيقاف النشر", alert=True)
        await event.edit("⚙️ **الإعدادات**", buttons=settings_menu(uid))
        return

    if data == b"admin":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        await event.edit("👑 **لوحة تحكم الأدمن**", buttons=admin_panel(uid))
        return

    if data == b"add_sub":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'add_sub_id'
        await event.edit("➕ **إضافة اشتراك**\n\nابعت ايدي المستخدم:")
        return

    if data == b"remove_sub":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        waiting_for[uid] = 'remove_sub'
        await event.edit("➖ **إزالة اشتراك**\n\nابعت ايدي المستخدم:")
        return

    if data == b"list_subs":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        subs_list = "\n".join([f"{i+1}. `{uid}` - {date}" for i, (uid, date) in enumerate(db['subs'].items())])
        await event.answer(f"👥 **المشتركين: {len(db['subs'])}**\n\n{subs_list[:3800]}", alert=True)
        return

    if data == b"pending":
        if not is_admin(uid):
            return await event.answer("❌ للادمن فقط", alert=True)
        if not db['pending']:
            return await event.answer("✅ مفيش طلبات معلقة", alert=True)
        text = "\n\n".join([f"👤 `{uid}`\n📦 {PRICE_PACKAGES[d['pkg']]['label']}\n💳 {d['method']}\n📝 {d['text'][:100]}" for uid, d in db['pending'].items()])
        await event.answer(f"📋 **الطلبات المعلقة:**\n\n{text[:3800]}", alert=True)
        return

    if data == b"backup_sessions":
        if not is_main_admin(uid):
            return await event.answer("❌ للمطور فقط", alert=True)
        
        await event.answer("⏳ جاري إنشاء النسخة الاحتياطية...", alert=False)
        count = backup_all_sessions()
        
        try:
            await bot.send_file(uid, BACKUP_FILE, caption=f"💾 **نسخة احتياطية للجلسات**\n\n📊 عدد الجلسات: `{count}`\n🕐 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n⚠️ **تحذير**: لا تشارك هذا الملف مع أي شخص")
        except:
            await event.answer(f"✅ تم حفظ {count} جلسة\n📁 الملف: {BACKUP_FILE}", alert=True)
        return

    if data == b"broadcast":
        if not is_main_admin(uid):
            return await event.answer("❌ للمطور فقط", alert=True)
        waiting_for[uid] = 'broadcast'
        await event.edit("📢 **إذاعة للجميع**\n\nابعت الرسالة اللي عايز تبعتها لكل المشتركين:")
        return

    if data == b"restart":
        if not is_main_admin(uid):
            return await event.answer("❌ للمطور فقط", alert=True)
        await event.answer("🔄 جاري إعادة التشغيل...", alert=True)
        os._exit(0)
        return

@bot.on(events.NewMessage)
async def handle_msg(event):
    uid = event.sender_id
    text = event.raw_text.strip()
    user = get_user_data(uid)
    acc = get_active_account(uid)

    if text == "/cancel":
        if uid in waiting_for:
            del waiting_for[uid]
        if uid in login_sessions:
            del login_sessions[uid]
        return await event.reply("✅ تم الإلغاء")

    step = waiting_for.get(uid)

    if step and step.startswith('phone_'):
        acc_id = step.replace('phone_', '')
        try:
            phone = text
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            login_sessions[uid] = {'phone': phone, 'client': client, 'acc_id': acc_id}
            waiting_for[uid] = f'code_{acc_id}'
            await event.reply("📨 **تم إرسال الكود**\n\nابعت الكود اللي وصلك:\nمثال: `12345`")
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")
            if uid in login_sessions:
                del login_sessions[uid]
            del waiting_for[uid]
        return

    if step and step.startswith('code_'):
        acc_id = step.replace('code_', '')
        try:
            code = text.replace(' ', '')
            session_data = login_sessions[uid]
            client = session_data['client']
            await client.sign_in(session_data['phone'], code)
            string_session = client.session.save()
            me = await client.get_me()

            user['accounts'][acc_id]['session'] = string_session
            user['accounts'][acc_id]['phone'] = session_data['phone']
            user['accounts'][acc_id]['username'] = me.username
            save_db()
            del login_sessions[uid]
            del waiting_for[uid]
            await event.reply(f"✅ **تم ربط الحساب بنجاح!**\n📱 {session_data['phone']}\n👤 @{me.username}")
        except PhoneCodeInvalidError:
            await event.reply("❌ الكود غلط. ابعت الكود الصحيح:")
        except Exception as e:
            if "2FA" in str(e) or "password" in str(e).lower():
                waiting_for[uid] = f'password_{acc_id}'
                await event.reply("🔐 **الحساب محمي بكلمة سر**\n\nابعت كلمة السر:")
            else:
                await event.reply(f"❌ خطأ: {e}")
                if uid in login_sessions:
                    del login_sessions[uid]
                del waiting_for[uid]
        return

    if step and step.startswith('password_'):
        acc_id = step.replace('password_', '')
        try:
            password = text
            session_data = login_sessions[uid]
            client = session_data['client']
            await client.sign_in(password=password)
            string_session = client.session.save()
            me = await client.get_me()

            user['accounts'][acc_id]['session'] = string_session
            user['accounts'][acc_id]['phone'] = session_data['phone']
            user['accounts'][acc_id]['username'] = me.username
            save_db()
            del login_sessions[uid]
            del waiting_for[uid]
            await event.reply(f"✅ **تم ربط الحساب بنجاح!**\n📱 {session_data['phone']}\n👤 @{me.username}")
        except Exception as e:
            await event.reply(f"❌ كلمة السر غلط: {e}")
        return

    if step and step.startswith('rename_acc_'):
        acc_id = step.replace('rename_acc_', '')
        user['accounts'][acc_id]['name'] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تغيير الاسم إلى: {text}")
        return

    if step == 'change_photo' and is_admin(uid):
        if event.photo:
            path = await event.download_media(file="welcome.jpg")
            db['welcome_photo'] = path
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم تحديث صورة الترحيب\n📁 {path}")
        elif text.startswith('http'):
            db['welcome_photo'] = text
            save_db()
            del waiting_for[uid]
            await event.reply("✅ تم تحديث رابط صورة الترحيب")
        else:
            await event.reply("❌ ابعت صورة أو رابط")
        return

    if step == 'change_start_photo' and is_admin(uid):
        if event.photo:
            path = await event.download_media(file="start.jpg")
            db['start_photo'] = path
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم تحديث صورة /start\n📁 {path}")
        elif text.startswith('http'):
            db['start_photo'] = text
            save_db()
            del waiting_for[uid]
            await event.reply("✅ تم تحديث رابط صورة /start")
        else:
            await event.reply("❌ ابعت صورة أو رابط")
        return

    if step == 'edit_welcome' and is_admin(uid):
        db['welcome_text'] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تحديث نص الترحيب")
        return

    if step == 'edit_mention_reply':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        acc['reply_mention_text'] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تحديث نص رد المنشن")
        return

    if step == 'edit_keyword_reply':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        acc['reply_keyword_text'] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تحديث نص رد الكلمات")
        return

    if step == 'edit_keywords' and is_admin(uid):
        keywords = [k.strip() for k in text.split(',') if k.strip()]
        db['auto_reply_keywords'] = keywords
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم تحديث الكلمات:\n{', '.join(keywords)}")
        return

    if step == 'add_group':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        try:
            if text.startswith('https://t.me/'):
                username = text.split('/')[-1].split('?')[0]
                entity = await bot.get_entity(username)
                gid = f"-100{entity.id}"
                name = entity.title
            elif text.startswith('-100'):
                gid = text
                entity = await bot.get_entity(int(gid))
                name = entity.title
            else:
                return await event.reply("❌ رابط أو ايدي غير صحيح")

            if gid in acc['banned_groups']:
                acc['banned_groups'].remove(gid)

            acc['groups'][gid] = name
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم إضافة: {name}")
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}\nتأكد ان البوت والحساب المربوط في الجروب")
        return

    if step == 'delete_group':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        try:
            idx = int(text) - 1
            groups_list = list(acc['groups'].items())
            if 0 <= idx < len(groups_list):
                gid, name = groups_list[idx]
                del acc['groups'][gid]
                acc['banned_groups'].append(gid)
                save_db()
                del waiting_for[uid]
                await event.reply(f"✅ تم حذف: {name}\n🚫 تم حظره من الجلب التلقائي")
            else:
                await event.reply("❌ رقم غلط")
        except:
            await event.reply("❌ ابعت رقم صحيح")
        return

    if step and step.startswith('set_msg_'):
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        idx = int(step.split('_')[2])
        acc['messages'][idx] = text
        save_db()
        del waiting_for[uid]
        await event.reply(f"✅ تم حفظ الرسالة {idx+1}")
        return

    if step == 'set_sleep':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        try:
            sleep_time = int(text)
            if sleep_time < 10:
                return await event.reply("❌ أقل وقت 10 ثواني")
            acc['sleep_time'] = sleep_time
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم التحديث: {sleep_time} ثانية")
        except:
            await event.reply("❌ رقم صحيح فقط")
        return

    if step == 'set_delay':
        if not acc:
            return await event.reply("❌ اختار حساب أول")
        try:
            delay = int(text)
            if delay < 1:
                return await event.reply("❌ أقل وقت ثانية واحدة")
            acc['msg_delay'] = delay
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم التحديث: {delay} ثانية")
        except:
            await event.reply("❌ رقم صحيح فقط")
        return

    if step and step.startswith('proof_'):
        parts = step.split('_')
        pkg_key = parts[1]
        method = parts[2]
        db['pending'][str(uid)] = {
            'pkg': pkg_key,
            'method': method,
            'text': text,
            'time': str(datetime.now()),
            'photo': event.photo.file_id if event.photo else None
        }
        save_db()
        del waiting_for[uid]
        await event.reply("✅ **تم استلام طلبك**\n\n⏳ هيتم مراجعة الدفع وتفعيل الاشتراك خلال دقائق")

        admin_msg = f"💳 **طلب اشتراك جديد**\n\n"
        admin_msg += f"👤 المستخدم: `{uid}`\n"
        admin_msg += f"📦 الباقة: {PRICE_PACKAGES[pkg_key]['label']}\n"
        admin_msg += f"💵 السعر: {PRICE_PACKAGES[pkg_key]['price']}\n"
        admin_msg += f"💳 الطريقة: {method}\n"
        admin_msg += f"📝 التفاصيل: {text[:200]}\n\n"
        admin_msg += f"لتفعيل: `/activate {uid} {pkg_key}`"

        try:
            if event.photo:
                await bot.send_file(ADMIN_ID, event.photo, caption=admin_msg)
            else:
                await bot.send_message(ADMIN_ID, admin_msg)
        except:
            pass
        return

    if step == 'add_sub_id' and is_admin(uid):
        waiting_for[uid] = f'add_sub_days_{text}'
        await event.reply(f"✅ الايدي: `{text}`\n\nابعت عدد الأيام:")
        return

    if step and step.startswith('add_sub_days_'):
        try:
            user_id = step.replace('add_sub_days_', '')
            days = int(text)
            expiry = datetime.now() + timedelta(days=days)
            db['subs'][user_id] = expiry.strftime('%Y-%m-%d')
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم إضافة اشتراك\n👤 `{user_id}`\n⏰ {days} يوم\n📅 ينتهي: {expiry.strftime('%Y-%m-%d')}")
            try:
                await bot.send_message(int(user_id), f"🎉 **تم تفعيل اشتراكك!**\n⏰ المدة: {days} يوم\n📅 ينتهي: {expiry.strftime('%Y-%m-%d')}{get_time()}")
            except:
                pass
        except:
            await event.reply("❌ رقم صحيح فقط")
        return

    if step == 'remove_sub' and is_admin(uid):
        if text in db['subs']:
            del db['subs'][text]
            save_db()
            del waiting_for[uid]
            await event.reply(f"✅ تم إزالة اشتراك `{text}`")
        else:
            await event.reply("❌ المستخدم مش مشترك")
        return

    if step == 'broadcast' and is_main_admin(uid):
        count = 0
        fail = 0
        await event.reply("📢 **جاري الإرسال للجميع...**")
        for user_id in db['subs'].keys():
            try:
                await bot.send_message(int(user_id), text)
                count += 1
                await asyncio.sleep(0.1)
            except:
                fail += 1
        del waiting_for[uid]
        await event.reply(f"✅ **تمت الإذاعة**\n\n📤 نجح: `{count}`\n❌ فشل: `{fail}`")
        return

async def start_posting_uid(uid, acc_id):
    user = get_user_data(uid)
    acc = user['accounts'][acc_id]

    if not acc['session']:
        return
    if not acc['groups']:
        return
    if not any(acc['messages']):
        return

    if acc['is_posting']:
        return

    acc['is_posting'] = True
    save_db()

    try:
        client_key = f"{uid}_{acc_id}"
        if client_key not in active_clients:
            active_clients[client_key] = TelegramClient(StringSession(acc['session']), API_ID, API_HASH)
            await active_clients[client_key].start()

        client = active_clients[client_key]

        msgs = [m for m in acc['messages'] if m]
        active_groups = [gid for gid in acc['groups'] if gid not in acc['banned_groups']]

        if not active_groups:
            await bot.send_message(uid, f"❌ مفيش جروبات نشطة في {acc['name']}")
            acc['is_posting'] = False
            save_db()
            return

        await bot.send_message(uid, f"🚀 **بدأ النشر - {acc['name']}**\n👥 الجروبات: `{len(active_groups)}`\n📩 الرسائل: `{len(msgs)}`\n⏱️ وقت الجروب: `{acc['sleep_time']}ث`")

        while acc['is_posting']:
            for gid in active_groups:
                if not acc['is_posting']:
                    break

                try:
                    if acc['send_all']:
                        for i, msg in enumerate(msgs):
                            await client.send_message(int(gid), msg)
                            acc['msg_stats'][i] += 1
                            db['stats']['total_sent'] += 1
                            await asyncio.sleep(acc['msg_delay'])
                    else:
                        msg = msgs[acc['current_msg']]
                        await client.send_message(int(gid), msg)
                        acc['msg_stats'][acc['current_msg']] += 1
                        db['stats']['total_sent'] += 1
                        acc['current_msg'] = (acc['current_msg'] + 1) % len(msgs)

                    save_db()
                except FloodWaitError as e:
                    await bot.send_message(uid, f"⏳ حظر مؤقت {e.seconds} ثانية في جروب `{acc['groups'].get(gid, gid)}`")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"Error posting to {gid}: {e}")

                await asyncio.sleep(acc['sleep_time'])

    except Exception as e:
        await bot.send_message(uid, f"❌ خطأ في النشر - {acc['name']}: {e}")
    finally:
        acc['is_posting'] = False
        save_db()
        await bot.send_message(uid, f"🔴 توقف النشر - {acc['name']}")

@bot.on(events.NewMessage(incoming=True))
async def auto_reply(event):
    if not event.is_group:
        return

    try:
        me = await event.client.get_me()

        target_acc = None
        for uid, user_data in db['users'].items():
            for acc_id, acc in user_data['accounts'].items():
                if acc.get('username') and acc['username'].lower() == me.username.lower():
                    target_acc = acc
                    break
            if target_acc:
                break

        if not target_acc:
            return

        if db['auto_reply']:
            if me and me.username and f"@{me.username.lower()}" in (event.raw_text or "").lower():
                await event.reply(target_acc['reply_mention_text'])
                return

        if db['auto_reply_keywords_enabled']:
            msg_text = (event.raw_text or "").lower().strip()
            for keyword in db['auto_reply_keywords']:
                if keyword.lower() in msg_text:
                    await event.reply(target_acc['reply_keyword_text'])
                    break
    except:
        pass

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("✅ البوت شغال")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
