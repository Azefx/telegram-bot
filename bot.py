import sqlite3
import time
import asyncio
import os
import re
from datetime import datetime
from telethon import TelegramClient, events, Button
from fbchat import Client
from fbchat_mqtt.models import Message, ImageAttachment, ThreadType

API_ID = 35380416
API_HASH = "2f9ae5ae25a7f159fdba987c1e3f6a82"
BOT_TOKEN = "8871570320:AAHkP8QKQatQaaRzr08zNaR4-ljUcUGyCJw"
ADMIN_ID = 8085768728

client = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

conn = sqlite3.connect('bot.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS fb_accounts
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, email TEXT, session TEXT, status TEXT DEFAULT 'active', active INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS fb_groups
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, group_id TEXT, group_name TEXT, search_term TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, search_term TEXT, text TEXT, image_path TEXT, interval_min INTEGER, active INTEGER DEFAULT 0)''')
conn.commit()

scheduled_tasks = {}

async def get_fb_client(user_id):
    c.execute("SELECT session FROM fb_accounts WHERE user_id =? AND active=1 AND status='active' LIMIT 1", (user_id,))
    row = c.fetchone()
    if not row: return None
    try:
        return Client(session_cookies=eval(row[0]))
    except:
        return None

async def join_and_get_groups(fb_client, user_id, search_term):
    c.execute("SELECT group_id FROM fb_groups WHERE user_id =? AND search_term =?", (user_id, search_term))
    joined = [g[0] for g in c.fetchall()]
    if joined:
        return joined

    results = fb_client.searchForGroups(search_term)
    new_groups = []
    for group in results[:20]:
        try:
            fb_client.joinGroup(group.uid)
            c.execute("INSERT INTO fb_groups (user_id, group_id, group_name, search_term) VALUES (?,?,?,?)",
                      (user_id, group.uid, group.name, search_term))
            conn.commit()
            new_groups.append(group.uid)
            await asyncio.sleep(8)
        except:
            pass
    return joined + new_groups

async def post_to_groups(user_id, search_term, text, image_path=None):
    fb_client = await get_fb_client(user_id)
    if not fb_client:
        return 0, "مفيش حساب فيسبوك شغال"

    c.execute("SELECT group_id FROM fb_groups WHERE user_id =? AND search_term =?", (user_id, search_term))
    groups = [g[0] for g in c.fetchall()]
    if not groups:
        return 0, "مفيش جروبات للكلمة دي"

    sent = 0
    attachment = None
    if image_path:
        try:
            attachment = ImageAttachment(open(image_path, 'rb'))
        except:
            pass

    for gid in groups:
        try:
            if attachment:
                fb_client.send(Message(text=text, attachments=[attachment]), thread_id=gid, thread_type=ThreadType.GROUP)
            else:
                fb_client.send(Message(text=text), thread_id=gid, thread_type=ThreadType.GROUP)
            sent += 1
            await asyncio.sleep(35)
        except:
            await asyncio.sleep(60)
    return sent, f"تم النشر في {sent} جروب"

async def scheduler_task(user_id, post_id):
    while True:
        c.execute("SELECT search_term, text, image_path, interval_min, active FROM scheduled_posts WHERE id =?", (post_id,))
        row = c.fetchone()
        if not row or row[4] == 0:
            break
        search_term, text, image_path, interval_min, _ = row
        sent, msg = await post_to_groups(user_id, search_term, text, image_path)
        try:
            await client.send_message(user_id, f"📢 تقرير النشر\n{msg}\nالوقت: {datetime.now().strftime('%H:%M')}")
        except:
            pass
        await asyncio.sleep(interval_min * 60)

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline("➕ إضافة حساب فيسبوك", b"add_fb")],
        [Button.inline("🔍 فحص الحسابات", b"check_accounts")],
        [Button.inline("🚪 تسجيل خروج حساب محدد", b"logout_one")],
        [Button.inline("🚪 تسجيل خروج كل الحسابات", b"logout_all")],
        [Button.inline("🔄 تغيير الحساب النشط", b"change_active")],
        [Button.inline("🔍 تعيين كلمة البحث", b"set_search")],
        [Button.inline("✍️ تعيين نص الإعلان", b"set_ad")],
        [Button.inline("▶️ تشغيل النشر", b"start_post")],
        [Button.inline("⏹️ إيقاف النشر", b"stop_post")],
        [Button.inline("📋 عرض الجروبات", b"show_groups")],
        [Button.inline("✏️ تعديل الإعلان", b"edit_ad")],
        [Button.inline("🗑️ حذف جروب", b"delete_group")],
        [Button.inline("🗑️ حذف كل الجروبات", b"delete_all_groups")],
        [Button.inline("⭐ مميزات البوت", b"features")]
    ]
    if event.sender_id == ADMIN_ID:
        buttons.append([Button.inline("⚙️ زر المبرمج", b"dev_panel")])
    await event.reply("مرحباً في بوت النشر الذكي", buttons=buttons)

# فحص الحسابات
@client.on(events.CallbackQuery(data=b"check_accounts"))
async def check_accounts(event):
    c.execute("SELECT id, email, status, active FROM fb_accounts WHERE user_id =?", (event.sender_id,))
    accounts = c.fetchall()
    if not accounts:
        await event.edit("مفيش حسابات مضافة")
        return
    text = "حساباتك:\n"
    for acc_id, email, status, active in accounts:
        active_txt = "🟢 شغال" if active else "⚪ متوقف"
        text += f"ID:{acc_id} | {email} | {status} | {active_txt}\n"
    await event.edit(text)

# تسجيل خروج حساب محدد
@client.on(events.CallbackQuery(data=b"logout_one"))
async def logout_one(event):
    c.execute("SELECT id, email FROM fb_accounts WHERE user_id =?", (event.sender_id,))
    accounts = c.fetchall()
    if not accounts:
        await event.edit("مفيش حسابات")
        return
    buttons = [[Button.inline(f"{email}", f"logout_{acc_id}")] for acc_id, email in accounts]
    await event.edit("اختار الحساب اللي عايز تسجل خروجه:", buttons=buttons)

@client.on(events.CallbackQuery(data=re.compile(b"logout_(\\d+)")))
async def logout_confirm(event):
    acc_id = int(event.data_match.group(1).decode())
    c.execute("DELETE FROM fb_accounts WHERE id=?", (acc_id,))
    conn.commit()
    await event.edit("✅ تم تسجيل خروج الحساب وحذفه من البوت")

# تسجيل خروج كل الحسابات - الجديد
@client.on(events.CallbackQuery(data=b"logout_all"))
async def logout_all(event):
    c.execute("DELETE FROM fb_accounts WHERE user_id=?", (event.sender_id,))
    conn.commit()
    await event.edit("✅ تم تسجيل خروج كل الحسابات وحذفها من البوت")

# تغيير الحساب النشط
@client.on(events.CallbackQuery(data=b"change_active"))
async def change_active(event):
    c.execute("SELECT id, email, active FROM fb_accounts WHERE user_id =?", (event.sender_id,))
    accounts = c.fetchall()
    if not accounts:
        await event.edit("مفيش حسابات")
        return
    buttons = [[Button.inline(f"{'🟢' if active else '⚪'} {email}", f"setact_{acc_id}")] for acc_id, email, active in accounts]
    await event.edit("اختار الحساب اللي عايزه ينشر. الأخضر = شغال دلوقتي", buttons=buttons)

@client.on(events.CallbackQuery(data=re.compile(b"setact_(\\d+)")))
async def set_active_account(event):
    acc_id = int(event.data_match.group(1).decode())
    c.execute("UPDATE fb_accounts SET active=0 WHERE user_id=?", (event.sender_id,))
    c.execute("UPDATE fb_accounts SET active=1 WHERE id=?", (acc_id,))
    conn.commit()
    await event.edit("✅ تم تغيير الحساب النشط")

# عرض الجروبات
@client.on(events.CallbackQuery(data=b"show_groups"))
async def show_groups(event):
    c.execute("SELECT id, search_term, group_name FROM fb_groups WHERE user_id =?", (event.sender_id,))
    rows = c.fetchall()
    if not rows:
        await event.edit("مفيش جروبات")
        return
    text = "جروباتك:\n"
    for gid, search_term, group_name in rows:
        text += f"ID:{gid} | {group_name} | {search_term}\n"
    await event.edit(text)

# تعديل الإعلان المجدول
@client.on(events.CallbackQuery(data=b"edit_ad"))
async def edit_ad(event):
    c.execute("SELECT id, text, interval_min FROM scheduled_posts WHERE user_id =?", (event.sender_id,))
    posts = c.fetchall()
    if not posts:
        await event.edit("مفيش إعلانات مجدولة")
        return
    buttons = [[Button.inline(f"ID:{pid} | {text[:20]}...", f"edit_{pid}")] for pid, text, _ in posts]
    await event.edit("اختار الإعلان اللي عايز تعدله:", buttons=buttons)

@client.on(events.CallbackQuery(data=re.compile(b"edit_(\\d+)")))
async def edit_ad_selected(event):
    post_id = int(event.data_match.group(1).decode())
    await event.edit("ابعت النص الجديد|المدة الجديدة\nمثال: إعلان جديد|30")
    client.conversation(event.sender_id).set_state(("editing_ad", post_id))

@client.on(events.NewMessage)
async def handle_edit_ad(event):
    state = client.conversation(event.sender_id).get_state()
    if not state or state[0]!= "editing_ad":
        return
    post_id = state[1]
    if '|' not in event.text:
        await event.reply("❌ الصيغة غلط")
        return
    text, interval = event.text.split('|', 1)
    c.execute("UPDATE scheduled_posts SET text=?, interval_min=? WHERE id=?", (text, int(interval), post_id))
    conn.commit()
    await event.reply("✅ تم تعديل الإعلان")
    client.conversation(event.sender_id).set_state(None)

# حذف جروب محدد
@client.on(events.CallbackQuery(data=b"delete_group"))
async def delete_group(event):
    c.execute("SELECT id, group_name, search_term FROM fb_groups WHERE user_id =?", (event.sender_id,))
    groups = c.fetchall()
    if not groups:
        await event.edit("مفيش جروبات")
        return
    buttons = [[Button.inline(f"{name} | {term}", f"delg_{gid}")] for gid, name, term in groups[:20]]
    await event.edit("اختار الجروب اللي عايز تحذفه:", buttons=buttons)

@client.on(events.CallbackQuery(data=re.compile(b"delg_(\\d+)")))
async def delete_group_confirm(event):
    gid = int(event.data_match.group(1).decode())
    c.execute("DELETE FROM fb_groups WHERE id=?", (gid,))
    conn.commit()
    await event.edit("✅ تم حذف الجروب")

# حذف كل الجروبات
@client.on(events.CallbackQuery(data=b"delete_all_groups"))
async def delete_all_groups(event):
    c.execute("DELETE FROM fb_groups WHERE user_id=?", (event.sender_id,))
    conn.commit()
    await event.edit("✅ تم حذف كل الجروبات")

# مميزات البوت
@client.on(events.CallbackQuery(data=b"features"))
async def features(event):
    text = """⭐ مميزات بوت النشر الذكي:

1️⃣ إدارة حسابات فيسبوك
- إضافة عدد لا نهائي من الحسابات
- فحص حالة الحساب شغال/موقوف
- تسجيل خروج حساب محدد أو الكل
- تغيير الحساب اللي بينشر

2️⃣ إدارة الجروبات
- بحث عن جروبات بكلمة مفتاحية
- انضمام تلقائي للجروبات
- عرض كل الجروبات المنضم فيها
- حذف جروب محدد أو حذف الكل

3️⃣ النشر الذكي
- تكتب كلمة البحث لوحدها
- تكتب نص الإعلان لوحدها
- دعم الصور مع الإعلان
- لو منضم في الجروبات ينشر علطول
- لو مش منضم ينضم الأول وبعدين ينشر

4️⃣ النشر التلقائي
- جدولة النشر كل 10 دقايق/ساعة/أي مدة
- تشغيل وإيقاف النشر بضغطة
- تعديل الإعلان والمدة في أي وقت
- تقرير بعد كل عملية نشر

5️⃣ الأمان
- تأخير 35 ثانية بين كل بوست
- تجنب السبام والبلوك
- كل مستخدم شغال على حساباته بس"""

    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back_menu")]])

@client.on(events.CallbackQuery(data=b"back_menu"))
async def back_menu(event):
    await start(event)

# إضافة حساب فيسبوك
@client.on(events.CallbackQuery(data=b"add_fb"))
async def add_fb(event):
    await event.edit("ابعت: email|password")
    client.conversation(event.sender_id).set_state("waiting_fb_login")

@client.on(events.NewMessage)
async def handle_fb_login(event):
    if client.conversation(event.sender_id).get_state()!= "waiting_fb_login":
        return
    try:
        email, password = event.text.split('|')
        await event.reply("⏳ بجرب أسجل دخول...")
        fb_client = Client(email, password)
        session = fb_client.getSession()
        c.execute("INSERT INTO fb_accounts (user_id, email, session, active) VALUES (?,?,?,1)", (event.sender_id, email, str(session)))
        conn.commit()
        await event.reply(f"✅ تم إضافة الحساب: {email}")
        client.conversation(event.sender_id).set_state(None)
    except Exception as e:
        await event.reply(f"❌ فشل: {e}")
        client.conversation(event.sender_id).set_state(None)

# تعيين كلمة البحث
@client.on(events.CallbackQuery(data=b"set_search"))
async def set_search(event):
    await event.edit("اكتب كلمة البحث، مثال: القليوبية")
    client.conversation(event.sender_id).set_state("waiting_search")

@client.on(events.NewMessage)
async def handle_search(event):
    if client.conversation(event.sender_id).get_state()!= "waiting_search":
        return
    search_term = event.text.strip()
    fb_client = await get_fb_client(event.sender_id)
    if not fb_client:
        await event.reply("❌ مفيش حساب فيسبوك شغال")
        client.conversation(event.sender_id).set_state(None)
        return
    await event.reply("⏳ ببحث وبنضم للجروبات...")
    groups = await join_and_get_groups(fb_client, event.sender_id, search_term)
    await event.reply(f"✅ خلصت، لقيت وانضميت لـ {len(groups)} جروب عن '{search_term}'")
    client.conversation(event.sender_id).set_state(None)

# تعيين نص الإعلان
@client.on(events.CallbackQuery(data=b"set_ad"))
async def set_ad(event):
    await event.edit("ابعت نص الإعلان|المدة بالدقايق\nمثال: شقة للبيع 3 غرف|60")
    client.conversation(event.sender_id).set_state("waiting_ad")

@client.on(events.NewMessage)
async def handle_ad(event):
    if client.conversation(event.sender_id).get_state()!= "waiting_ad":
        return
    if '|' not in event.text:
        await event.reply("❌ الصيغة غلط")
        return
    text, interval = event.text.split('|', 1)
    c.execute("INSERT INTO scheduled_posts (user_id, text, interval_min) VALUES (?,?,?)",
              (event.sender_id, text, int(interval)))
    post_id = c.lastrowid
    conn.commit()
    await event.reply(f"✅ تم حفظ الإعلان. ابعت الصورة لو عايز، أو ابعت 'تم' للتشغيل")
    client.conversation(event.sender_id).set_state(("waiting_image", post_id))

@client.on(events.NewMessage)
async def handle_image(event):
    state = client.conversation(event.sender_id).get_state()
    if not state or state[0]!= "waiting_image":
        return
    post_id = state[1]
    image_path = None
    if event.media:
        image_path = await event.download_media(file="./")
        c.execute("UPDATE scheduled_posts SET image_path =? WHERE id =?", (image_path, post_id))
        conn.commit()
    await event.reply("✅ تم حفظ الصورة")

# تشغيل النشر
@client.on(events.CallbackQuery(data=b"start_post"))
async def start_post(event):
    c.execute("SELECT id FROM scheduled_posts WHERE user_id =? AND active=0 LIMIT 1", (event.sender_id,))
    row = c.fetchone()
    if not row:
        await event.edit("❌ مفيش إعلان متوقف")
        return
    post_id = row[0]
    c.execute("UPDATE scheduled_posts SET active=1 WHERE id =?", (post_id,))
    conn.commit()
    task = asyncio.create_task(scheduler_task(event.sender_id, post_id))
    scheduled_tasks[post_id] = task
    await event.edit("▶️ تم تشغيل النشر")

# إيقاف النشر
@client.on(events.CallbackQuery(data=b"stop_post"))
async def stop_post(event):
    c.execute("SELECT id FROM scheduled_posts WHERE user_id =? AND active=1", (event.sender_id,))
    posts = c.fetchall()
    for (post_id,) in posts:
        c.execute("UPDATE scheduled_posts SET active=0 WHERE id =?", (post_id,))
        if post_id in scheduled_tasks:
            scheduled_tasks[post_id].cancel()
    conn.commit()
    await event.edit("⏹️ تم إيقاف كل المهام")

# لوحة المبرمج
@client.on(events.CallbackQuery(data=b"dev_panel"))
async def dev_panel(event):
    if event.sender_id!= ADMIN_ID:
        return
    c.execute("SELECT COUNT(*) FROM fb_accounts")
    accounts = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM fb_groups")
    groups = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM scheduled_posts WHERE active=1")
    active_posts = c.fetchone()[0]
    await event.edit(f"لوحة المبرمج\nالحسابات: {accounts}\nالجروبات: {groups}\nالمهام الشغالة: {active_posts}")

print("البوت شغال...")
client.run_until_disconnected()
