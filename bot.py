import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, LabeledPrice
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# --- البيانات الأساسية ---
API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = '5759866264:AAEwiaoo-lT-SI6TQhHMTC59umgnkV5zIm4'
ADMIN_ID = 154919127 # المطور الرئيسي
DEVELOPER_USERNAME = "Devazf" # غير ده ليوزرك من غير @
MANDATORY_CHANNEL = "Spraize" # حط @قناتك أو سيبه فاضي ""
DB_FILE = 'hero_data.json'

STAR_PACKAGES = {
    '7_days': {'days': 7, 'stars': 50, 'label': '7 أيام'},
    '15_days': {'days': 15, 'stars': 100, 'label': '15 يوم'},
    '30_days': {'days': 30, 'stars': 150, 'label': 'شهر كامل'}
}

# --- نظام الحفظ والاشتراكات ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'session': None,
        'super_groups': [],
        'sleep_time': 30,
        'msg_text': '',
        'subs': {str(ADMIN_ID): '2099-01-01'},
        'admins': [ADMIN_ID] # قائمة الأدمنز
    }

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()
waiting_for = {}
login_temp = {}
is_posting = False

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
            expiry = datetime.strptime(db['subs'][uid], '%Y-%m-%d')
            if expiry > datetime.now():
                return True
        except:
            pass
    return False

async def send_log(event, action, text=""):
    try:
        user = await event.get_sender()
        name = user.first_name if user else "Unknown"
        uid = user.id if user else "Unknown"
        log_msg = f"🔔 **إشعار مراقبة جديد**\n👤 المستخدم: {name}\n🆔 الايدي: `{uid}`\n🔘 الإجراء: {action}\n📥 النص: {text[:100]}"
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
        btns.append([Button.inline("💫 اشترك بالنجوم", b"stars_menu")])
    if is_admin(uid):
        btns.append([Button.inline("🔐 لوحة الأدمن", b"admin_panel")])
    btns.append([Button.url('👨‍💻 مراسلة المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')])
    return btns

# 🔘 واجهة الإعدادات
def settings_menu():
    status = "🟢 مفعل ومربوط" if db['session'] else "🔴 غير مربوط"
    groups_count = len(db['super_groups'])
    return [
        [Button.inline(status, b"none")],
        [Button.inline("📥 جلب المجموعات تلقائي", b"fetch_groups")],
        [Button.inline(f"👥 السوبرات: {groups_count}", b"show_links")],
        [Button.inline("➕ إضافة يدوي", b"add_links"), Button.inline("👤 ربط حساب", b"login_phone")],
        [Button.inline("⏱️ الوقت", b"set_time"), Button.inline("📩 نص الرسالة", b"add_msg")],
        [Button.inline("🔴 إيقاف", b"stop_post"), Button.inline("🟢 بدء النشر", b"start_post")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]

# 🔘 لوحة الأدمن
def admin_panel(uid):
    btns = [
        [Button.inline("➕ تفعيل مشترك", b"add_sub")],
        [Button.inline("👥 قائمة المشتركين", b"list_subs")],
    ]
    if is_main_admin(uid): # بس المطور الرئيسي يقدر يرفع أدمن
        btns.append([Button.inline("⬆️ رفع أدمن", b"add_admin"), Button.inline("⬇️ تنزيل أدمن", b"remove_admin")])
        btns.append([Button.inline("👑 قائمة الأدمنز", b"list_admins")])
    btns.append([Button.inline("🔙 رجوع", b"back_main")])
    return btns

# 🔘 قائمة النجوم
def stars_menu_keyboard():
    return [
        [Button.inline(f'7 أيام - 50⭐', 'buy_7_days')],
        [Button.inline(f'15 يوم - 100⭐', 'buy_15_days')],
        [Button.inline(f'شهر كامل - 150⭐', 'buy_30_days')],
        [Button.inline('🔙 رجوع', 'back_main')]
    ]

# --- استقبال الأوامر ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if not is_sub(uid):
        return await event.reply(f"⚠️ **عذراً، اشتراكك غير مفعل**\n\n💫 تقدر تشترك بالنجوم أو راسل المطور:\n🆔 الايدي: `{uid}`", buttons=[[Button.inline("💫 اشترك بالنجوم", b"stars_menu")], [Button.url('👨‍💻 راسل المبرمج', f'https://t.me/{DEVELOPER_USERNAME}')]])
    await event.reply("🚀 **بوت النشر التلقائي المطور - Programmer Azef**", buttons=main_menu(uid))

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_cmd(event):
    if is_admin(event.sender_id):
        await event.reply("👑 **لوحة التحكم:**", buttons=admin_panel(event.sender_id))

# --- محرك النشر الذكي ---
async def auto_publisher(event):
    global is_posting
    if not db['session']:
        return await event.reply("⚠️ سجل دخول أولاً!")
    if not db['msg_text']:
        return await event.reply("⚠️ ضيف نص الرسالة أولاً من الإعدادات!")
    if not db['super_groups']:
        return await event.reply("⚠️ ضيف سوبرات أولاً أو دوس 'جلب المجموعات تلقائي'!")

    is_posting = True
    client = TelegramClient(StringSession(db['session']), API_ID, API_HASH)
    try:
        await client.connect()
        await event.reply(f"✅ **تم تشغيل المحرك الذكي للنشر..**\n📊 عدد الجروبات: {len(db['super_groups'])}")
        while is_posting:
            for target in db['super_groups']:
                if not is_posting:
                    break
                try:
                    await client.send_message(int(target), db['msg_text'])
                    await asyncio.sleep(db['sleep_time'])
                except FloodWaitError as e:
                    await event.reply(f"⚠️ حماية: سأنتظر {e.seconds} ثانية.")
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

    if data == b"stars_menu":
        await event.edit("💫 **اشترك بالنجوم**\n\nاختر الباقة اللي تناسبك:", buttons=stars_menu_keyboard())
        return

    if data.startswith(b'buy_'):
        package = data.decode().split('_')[1] + '_' + data.decode().split('_')[2]
        if package not in STAR_PACKAGES:
            return
        pkg = STAR_PACKAGES[package]
        await event.edit(f"💫 **تأكيد الشراء**\n\nالباقة: {pkg['label']}\nالسعر: {pkg['stars']} نجمة\n\nدوس الدفع تحت عشان تكمل", buttons=[
            [Button.buy(f'💫 ادفع {pkg["stars"]} نجمة')],
            [Button.inline('🔙 رجوع', 'stars_menu')]
        ])
        await bot.send_invoice(
            uid,
            title=f"Programmer Azef - {pkg['label']}",
            description=f"اشتراك VIP لمدة {pkg['label']} في بوت Programmer Azef",
            currency='XTR',
            prices=[LabeledPrice(label=pkg['label'], amount=pkg['stars'])],
            payload=f"vip_{package}_{uid}"
        )
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
    elif data in [b"add_links", b"set_time", b"add_msg", b"login_phone", b"show_links"]:
        if data == b"show_links":
            res = "\n".join(db['super_groups']) if db['super_groups'] else "لا يوجد."
            return await event.reply(f"👥 السوبرات المضافة حالياً: {len(db['super_groups'])}\n\n{res}")

        waiting_for[uid] = data.decode()

        if data == b"login_phone":
            await event.reply("🔄 أرسل رقم الهاتف المراد ربطه (مع رمز الدولة):")
        elif data == b"add_links":
            await event.reply("🔗 **أرسل روابط السوبرات الآن**\n(كل رابط في سطر واحد، أو معرف المجموعة)")
        elif data == b"set_time":
            await event.reply("⏱️ **أدخل مدة الانتظار بالثواني**")
        elif data == b"add_msg":
            await event.reply("📩 **أرسل نص الرسالة التي تريد نشرها الآن:**")

@bot.on(events.NewMessage)
async def inputs(event):
    uid = event.sender_id
    if not event.text or event.text.startswith('/'):
        return
    step = waiting_for.get(uid)

    if step == 'get_id':
        waiting_for[uid] = f"get_days_{event.text.strip()}"
        await event.reply("🕒 كم عدد أيام الاشتراك؟")
    elif step == 'get_admin_id':
        try:
            new_admin = int(event.text.strip())
            if new_admin not in db['admins']:
                db['admins'].append(new_admin)
                save_db()
                await event.reply(f"✅ تم رفع `{new_admin}` أدمن بنجاح")
            else:
                await event.reply("⚠️ ده أدمن أصلاً")
            waiting_for[uid] = None
        except:
            await event.reply("❌ ارسل ايدي صحيح")
    elif step == 'remove_admin_id':
        try:
            admin_to_remove = int(event.text.strip())
            if admin_to_remove == ADMIN_ID:
                await event.reply("❌ ماتقدرش تنزل المطور الرئيسي")
            elif admin_to_remove in db['admins']:
                db['admins'].remove(admin_to_remove)
                save_db()
                await event.reply(f"✅ تم تنزيل `{admin_to_remove}` من الأدمنز")
            else:
                await event.reply("⚠️ ده مش أدمن أصلاً")
            waiting_for[uid] = None
        except:
            await event.reply("❌ ارسل ايدي صحيح")
    elif step and step.startswith('get_days_'):
        target_id = step.split('_')[-1]
        try:
            days = int(event.text)
            expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            db['subs'][target_id] = expiry
            save_db()
            await event.reply(f"✅ تم تفعيل {target_id} لمدة {days} يوم.")
            waiting_for[uid] = None
        except:
            await event.reply("❌ ارسل رقم صحيح للأيام.")
    elif step == 'add_links':
        db['super_groups'] = [l.strip() for l in event.text.split('\n') if l.strip()]
        save_db()
        await event.reply(f"✅ تم حفظ {len(db['super_groups'])} سوبر.")
        waiting_for[uid] = None
    elif step == 'set_time':
        try:
            db['sleep_time'] = int(event.text)
            save_db()
            await event.reply("✅ تم حفظ وقت الانتظار.")
            waiting_for[uid] = None
        except:
            await event.reply("❌ يرجى إرسال رقم صحيح فقط.")
    elif step == 'add_msg':
        db['msg_text'] = event.text
        save_db()
        await event.reply("✅ تم حفظ نص الرسالة الجديد.")
        waiting_for[uid] = None
    elif step == 'login_phone':
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            req = await client.send_code_request(event.text.strip())
            login_temp[uid] = {'c': client, 'p': event.text.strip(), 'h': req.phone_code_hash}
            waiting_for[uid] = 'get_code'
            await event.reply("✅ أرسل الكود الآن:")
        except Exception as e:
            await client.disconnect()
            await event.reply(f"❌ خطأ: {e}")
            waiting_for[uid] = None
    elif step == 'get_code':
        try:
            t = login_temp[uid]
            await t['c'].sign_in(t['p'], event.text.strip(), phone_code_hash=t['h'])
            db['session'] = t['c'].session.save()
            save_db()
            await t['c'].disconnect()
            await event.reply("🎉 تم ربط الحساب الشخصي بنجاح!", buttons=main_menu(uid))
            waiting_for[uid] = None
            login_temp.pop(uid, None)
        except SessionPasswordNeededError:
            waiting_for[uid] = 'get_pass'
            await event.reply("🔐 الحساب محمي، أرسل رمز التحقق بخطوتين:")
        except Exception as e:
            await event.reply(f"❌ الكود غلط: {e}")
    elif step == 'get_pass':
        try:
            await login_temp[uid]['c'].sign_in(password=event.text.strip())
            db['session'] = login_temp[uid]['c'].session.save()
            save_db()
            await login_temp[uid]['c'].disconnect()
            await event.reply("🎉 تم التحقق والحفظ بنجاح!")
            waiting_for[uid] = None
            login_temp.pop(uid, None)
        except Exception as e:
            await event.reply(f"❌ كلمة السر غلط: {e}")

    if is_sub(uid) and event.text:
        await send_log(event, "إرسال نص", event.text)

# --- معالجة الدفع بالنجوم ---
@bot.on(events.RawUpdate)
async def payment_handler(update):
    if hasattr(update, 'message') and hasattr(update.message, 'successful_payment'):
        payment = update.message.successful_payment
        payload = payment.invoice_payload
        user_id = update.message.peer_id.user_id

        if payload.startswith('vip_'):
            parts = payload.split('_')
            package = parts[1] + '_' + parts[2]
            if package in STAR_PACKAGES:
                days = STAR_PACKAGES[package]['days']
                expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
                db['subs'][str(user_id)] = expiry
                save_db()
                await bot.send_message(user_id, f"✅ **تم تفعيل اشتراكك بنجاح!**\n\n🎁 الباقة: {STAR_PACKAGES[package]['label']}\n📅 صالح لحد: {expiry}\n\nدوس /start عشان تبدأ")

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    print("🚀 البوت شغال تمام - Programmer Azef!")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
