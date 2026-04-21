import os
import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerEmpty, Channel, Chat
from telethon.errors import FloodWaitError, SlowModeWaitError, ChatWriteForbiddenError, UserBannedInChannelError, SessionPasswordNeededError

SOURCE_NAME = "Azef" # اسم السورس بتاعنا
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DEVELOPER_USERNAME = "@devazf" # غير ده ليوزرك عشان زرار راسل المطور

bot = None
conn = None
c = None
waiting_for = {}
temp_data = {}
broadcast_tasks = {}
TEMP_MEDIA = {}

def init_db():
    global conn, c
    conn = sqlite3.connect('broadcaster.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, is_vip INTEGER DEFAULT 0, vip_expires TEXT, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, session_string TEXT, phone TEXT, username TEXT, is_active INTEGER DEFAULT 1, last_used TEXT, groups_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT, media_id TEXT, style TEXT DEFAULT 'normal', emoji TEXT, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, post_id INTEGER, delay_min INTEGER, delay_max INTEGER, status TEXT DEFAULT 'running', sent_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0, started_at TEXT)''')
    conn.commit()

def safe_parse_date(date_string):
    try:
        return datetime.fromisoformat(date_string)
    except:
        return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f")

def is_admin(user_id):
    return user_id == int(ADMIN_ID)

def is_vip(user_id):
    if is_admin(user_id):
        return True
    c.execute("SELECT vip_expires FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or not row[0]:
        return False
    expires = safe_parse_date(row[0])
    return expires > datetime.now()

def create_user(user_id, username):
    c.execute("INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?,?,?)", (user_id, username, datetime.now().isoformat()))
    conn.commit()

def add_vip(user_id, days):
    expires = datetime.now() + timedelta(days=days)
    c.execute("UPDATE users SET is_vip=1, vip_expires=? WHERE user_id=?", (expires.isoformat(), user_id))
    conn.commit()
    return expires

def remove_vip(user_id):
    c.execute("UPDATE users SET is_vip=0, vip_expires=NULL WHERE user_id=?", (user_id,))
    conn.commit()

def get_all_vips():
    c.execute("SELECT * FROM users WHERE is_vip=1 AND vip_expires >? ORDER BY vip_expires DESC", (datetime.now().isoformat(),))
    return c.fetchall()

def add_account(owner_id, session_string, phone, username):
    c.execute("INSERT INTO accounts (owner_id, session_string, phone, username, last_used) VALUES (?,?,?,?,?)", (owner_id, session_string, phone, username, datetime.now().isoformat()))
    conn.commit()

def get_user_accounts(user_id):
    c.execute("SELECT * FROM accounts WHERE owner_id=? AND is_active=1 ORDER BY last_used ASC", (user_id,))
    return c.fetchall()

def delete_account(acc_id, owner_id):
    c.execute("DELETE FROM accounts WHERE id=? AND owner_id=?", (acc_id, owner_id))
    conn.commit()

def save_post(user_id, content, media_id=None, style='normal', emoji=''):
    c.execute("INSERT INTO posts (user_id, content, media_id, style, emoji, created_at) VALUES (?,?,?,?,?,?)", (user_id, content, media_id, style, emoji, datetime.now().isoformat()))
    conn.commit()
    return c.lastrowid

def get_post(post_id):
    c.execute("SELECT * FROM posts WHERE id=?", (post_id,))
    return c.fetchone()

def format_post(content, style, emoji):
    if emoji:
        content = f"{emoji} {content}"
    if style == 'quote':
        lines = content.split('\n')
        content = '\n'.join([f"> {line}" for line in lines])
    elif style == 'bold':
        content = f"**{content}**"
    elif style == 'bold_quote':
        lines = content.split('\n')
        content = '\n'.join([f"> **{line}**" for line in lines])
    elif style == 'fancy':
        content = f"✨ **{content}** ✨"
    return content

def create_campaign(user_id, post_id, delay_min, delay_max):
    c.execute("INSERT INTO campaigns (user_id, post_id, delay_min, delay_max, started_at) VALUES (?,?,?,?,?)", (user_id, post_id, delay_min, delay_max, datetime.now().isoformat()))
    conn.commit()
    return c.lastrowid

def update_campaign_stats(campaign_id, sent, failed):
    c.execute("UPDATE campaigns SET sent_count=sent_count+?, failed_count=failed_count+? WHERE id=?", (sent, failed, campaign_id))
    conn.commit()

def stop_campaign(campaign_id):
    c.execute("UPDATE campaigns SET status='stopped' WHERE id=?", (campaign_id,))
    conn.commit()

def get_campaign_stats():
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status='running'")
    running = c.fetchone()[0]
    c.execute("SELECT SUM(sent_count), SUM(failed_count) FROM campaigns")
    stats = c.fetchone()
    return running, stats[0] or 0, stats[1] or 0

async def get_all_groups(client):
    groups = []
    try:
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            if isinstance(entity, Chat):
                groups.append(entity)
            elif isinstance(entity, Channel):
                if entity.broadcast or not entity.megagroup:
                    continue
                groups.append(entity)
    except Exception as e:
        print(f"Error getting groups: {e}")
    return groups

async def broadcast_task(user_id, campaign_id, post_id, accounts, delay_min, delay_max):
    post = get_post(post_id)
    if not post:
        return
    _, _, raw_content, media_id, style, emoji, _ = post
    content = format_post(raw_content, style, emoji)
    total_sent = 0
    total_failed = 0
    await bot.send_message(user_id, f"🚀 **بدأت الحملة - {SOURCE_NAME}**\n\n📊 الحسابات: {len(accounts)}\n⏱️ التأخير: {delay_min}-{delay_max}ث\n🎨 الاستايل: {style}\n\nجاري النشر...")
    for acc in accounts:
        if broadcast_tasks.get(user_id)!= asyncio.current_task():
            break
        acc_id, _, session_string, phone, username, _, _, _ = acc
        client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
        try:
            await client.start()
            groups = await get_all_groups(client)
            await bot.send_message(user_id, f"📱 {phone or username}\n📊 لقيت {len(groups)} جروب")
            for group in groups:
                if broadcast_tasks.get(user_id)!= asyncio.current_task():
                    break
                if hasattr(group, 'broadcast') and group.broadcast:
                    continue
                try:
                    if media_id:
                        await client.send_file(group, media_id, caption=content, parse_mode='md')
                    else:
                        await client.send_message(group, content, parse_mode='md')
                    total_sent += 1
                    update_campaign_stats(campaign_id, 1, 0)
                    sleep_time = random.randint(delay_min, delay_max)
                    await asyncio.sleep(sleep_time)
                except FloodWaitError as e:
                    await bot.send_message(user_id, f"⏳ {phone}: انتظار {e.seconds}ث...")
                    await asyncio.sleep(e.seconds)
                except (ChatWriteForbiddenError, UserBannedInChannelError, SlowModeWaitError):
                    total_failed += 1
                    update_campaign_stats(campaign_id, 0, 1)
                except Exception:
                    total_failed += 1
                    update_campaign_stats(campaign_id, 0, 1)
                    await asyncio.sleep(5)
            c.execute("UPDATE accounts SET last_used=?, groups_count=? WHERE id=?", (datetime.now().isoformat(), len(groups), acc_id))
            conn.commit()
        except Exception as e:
            await bot.send_message(user_id, f"❌ خطأ في {phone}: {str(e)}")
        finally:
            await client.disconnect()
        await asyncio.sleep(random.randint(30, 60))
    await bot.send_message(user_id, f"✅ **انتهت الحملة - {SOURCE_NAME}**\n\n📤 نجح: {total_sent}\n❌ فشل: {total_failed}")
    stop_campaign(campaign_id)
    if user_id in broadcast_tasks:
        del broadcast_tasks[user_id]

def main_keyboard(user_id):
    buttons = []
    if is_vip(user_id):
        buttons.append([Button.inline('📝 إنشاء منشور', 'create_post')])
        buttons.append([Button.inline('🚀 بدء حملة نشر', 'start_broadcast')])
        buttons.append([Button.inline('🛑 إيقاف الحملة', 'stop_broadcast')])
        buttons.append([Button.inline('📱 إضافة حساب', 'add_account')])
        buttons.append([Button.inline('📋 حساباتي', 'my_accounts')])
    else:
        buttons.append([Button.inline('💎 الاشتراك المدفوع', 'contact_dev')]) # جديد
        buttons.append([Button.inline('❌ حسابك غير مفعل', 'contact_admin')])
    if is_admin(user_id):
        buttons.append([Button.inline('👑 لوحة الأدمن', 'admin_panel')])
    return buttons

def admin_keyboard():
    return [[Button.inline('➕ تفعيل VIP', 'admin_add_vip'), Button.inline('❌ إلغاء VIP', 'admin_remove_vip')], [Button.inline('👥 قائمة الـVIP', 'admin_list_vips'), Button.inline('📊 إحصائيات', 'admin_stats')], [Button.inline('🔙 رجوع', 'back_main')]]

def style_keyboard():
    return [[Button.inline('عادي', 'style_normal'), Button.inline('اقتباس >', 'style_quote')], [Button.inline('**عريض**', 'style_bold'), Button.inline('**اقتباس عريض**', 'style_bold_quote')], [Button.inline('✨ فخم ✨', 'style_fancy')], [Button.inline('تخطي التنسيق', 'style_skip')]]

def emoji_keyboard():
    return [[Button.inline('🔥', 'emoji_fire'), Button.inline('📢', 'emoji_megaphone')], [Button.inline('⭐', 'emoji_star'), Button.inline('💎', 'emoji_gem')], [Button.inline('✨ اكتب إيموجي مخصص', 'emoji_custom')], [Button.inline('بدون إيموجي', 'emoji_none')]]

def setup_handlers():
    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        user_id = event.sender_id
        username = event.sender.username or f"user{user_id}"
        is_new = False
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not c.fetchone():
            is_new = True
        create_user(user_id, username)

        # جديد: ترحيب لكل شخص + إشعار للأدمن
        if is_new:
            await bot.send_message(int(ADMIN_ID), f"🆕 **يوزر جديد دخل بوت {SOURCE_NAME}**\n\nID: `{user_id}`\nUsername: @{username}")

        if not is_vip(user_id):
            await event.reply(f"👋 **أهلاً بيك في {SOURCE_NAME}**\n\n❌ حسابك غير مفعل حالياً\n\n💎 للتفعيل والاشتراك المدفوع دوس الزرار تحت", buttons=main_keyboard(user_id))
            return

        c.execute("SELECT vip_expires FROM users WHERE user_id=?", (user_id,))
        exp = safe_parse_date(c.fetchone()[0])
        accounts = get_user_accounts(user_id)
        await event.reply(f"🔥 **أهلاً بيك في {SOURCE_NAME}**\n\n📅 صالح لحد: {exp.strftime('%Y-%m-%d')}\n📱 الحسابات: {len(accounts)}\n\n💾 لحفظ صورة: ابعتها مع `/save اسم`\n📤 لإرسال محفوظ: `/send اسم`\n📋 لعرض المحفوظ: `/list`", buttons=main_keyboard(user_id))

    @bot.on(events.NewMessage(pattern='/activate'))
    async def activate_cmd(event):
        if not is_admin(event.sender_id):
            return
        try:
            args = event.text.split()[1:]
            target_id = int(args[0])
            days = int(args[1])
            expires = add_vip(target_id, days=days)
            await event.reply(f"✅ تم التفعيل\nID: `{target_id}`\nينتهي: {expires.strftime('%Y-%m-%d')}")
            try:
                await bot.send_message(target_id, f"💎 **تم تفعيل حسابك في {SOURCE_NAME}** ✅\nصالح لحد: {expires.strftime('%Y-%m-%d')}")
            except:
                pass
        except Exception as e:
            await event.reply(f"خطأ: {str(e)}\nالاستخدام: /activate user_id days")

    @bot.on(events.NewMessage(pattern='/save'))
    async def save_media(event):
        user_id = event.sender_id
        if not is_vip(user_id): return
        if not event.photo:
            await event.reply("❌ لازم تبعت الأمر مع صورة\nمثال: ابعت صورة والكابشن `/save عروض`")
            return
        try:
            name = event.text.split(' ', 1)[1].strip()
            if user_id not in TEMP_MEDIA: TEMP_MEDIA[user_id] = {}
            TEMP_MEDIA[user_id][name] = event.photo
            await event.reply(f"✅ تم حفظ الصورة باسم `{name}`\nلإرسالها اكتب `/send {name}`")
        except IndexError:
            await event.reply("❌ اكتب اسم بعد /save\nمثال: `/save عروض_اليوم`")

    @bot.on(events.NewMessage(pattern='/send'))
    async def send_media(event):
        user_id = event.sender_id
        if not is_vip(user_id): return
        try:
            name = event.text.split(' ', 1)[1].strip()
            if user_id not in TEMP_MEDIA or name not in TEMP_MEDIA[user_id]:
                await event.reply("❌ الاسم ده مش محفوظ عندك\nاكتب `/list` عشان تشوف المحفوظ")
                return
            await event.reply(f"تمام، اختار هتبعت `{name}` فين:", buttons=[
                [Button.inline('🚀 لكل الجروبات', f'sendto_all_{name}')],
                [Button.inline('🔙 إلغاء', 'back_main')]
            ])
        except IndexError:
            await event.reply("اكتب `/send اسم_الصورة`")

    @bot.on(events.NewMessage(pattern='/list'))
    async def list_media(event):
        user_id = event.sender_id
        if not is_vip(user_id): return
        if user_id not in TEMP_MEDIA or not TEMP_MEDIA[user_id]:
            await event.reply("مفيش صور محفوظة عندك")
            return
        text = f"🖼 **الصور المحفوظة في {SOURCE_NAME}:**\n\n"
        for name in TEMP_MEDIA[user_id].keys():
            text += f"- `{name}`\n"
        await event.reply(text + "\nلإرسال أي واحدة اكتب `/send الاسم`")

    @bot.on(events.CallbackQuery)
    async def callback(event):
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        create_user(user_id, event.sender.username or f"user{user_id}")
        if data == 'contact_admin':
            await event.answer("كلم الأدمن للتفعيل", alert=True)
            return
        if data == 'contact_dev': # جديد: زرار راسل المطور
            await event.edit(f"💎 **للاشتراك المدفوع في {SOURCE_NAME}**\n\nراسل المطور عشان تعرف الأسعار والتفاصيل:", buttons=[
                [Button.url('👨‍💻 راسل المطور', f'https://t.me/{DEVELOPER_USERNAME}')],
                [Button.inline('🔙 رجوع', 'back_main')]
            ])
            return
        if data == 'create_post':
            if not is_vip(user_id):
                await event.answer("حسابك غير مفعل", alert=True)
                return
            waiting_for[user_id] = 'post_content'
            await event.edit("📝 **الخطوة 1/3: المحتوى**\n\nابعت النص اللي عايز تنشره:\n\nممكن كمان تبعت صورة مع كابشن")
        elif data.startswith('style_'):
            style = data.split('_')[1]
            if style == 'skip':
                style = 'normal'
            temp_data[user_id]['style'] = style
            waiting_for[user_id] = 'post_emoji'
            await event.edit("🎨 **الخطوة 3/3: اختار إيموجي مميز**\n\nهيتحط في بداية المنشور:", buttons=emoji_keyboard())
        elif data == 'emoji_custom':
            waiting_for[user_id] = 'emoji_custom_input'
            await event.edit("💎 **ابعت الإيموجي بتاعك**\n\nانسخ الإيموجي من تليجرام وحطه هنا\nمثال: 🦄 أو أي إيموجي بريميوم عندك")
        elif data.startswith('emoji_'):
            emoji_name = data.split('_')[1]
            emoji_map = {'fire': '🔥', 'megaphone': '📢', 'star': '⭐', 'gem': '💎'}
            emoji = emoji_map.get(emoji_name, '') if emoji_name!= 'none' else ''
            data_dict = temp_data.get(user_id, {})
            post_id = save_post(user_id, data_dict['content'], data_dict.get('media_id'), data_dict['style'], emoji)
            waiting_for[user_id] = None
            temp_data.pop(user_id, None)
            await event.edit(f"✅ **تم حفظ المنشور**\nID: {post_id}\nالإيموجي: {emoji or 'لا يوجد'}\n\nدوس 'بدء حملة نشر' عشان تبدأ", buttons=main_keyboard(user_id))
        elif data == 'start_broadcast':
            if not is_vip(user_id):
                await event.answer("حسابك غير مفعل", alert=True)
                return
            accounts = get_user_accounts(user_id)
            if not accounts:
                await event.answer("❌ ضيف حسابات الأول", alert=True)
                return
            c.execute("SELECT * FROM posts WHERE user_id=? ORDER BY created_at DESC LIMIT 1", (user_id,))
            post = c.fetchone()
            if not post:
                await event.answer("❌ اعمل منشور الأول", alert=True)
                return
            temp_data[user_id] = {'post_id': post[0], 'accounts': accounts}
            waiting_for[user_id] = 'broadcast_delay'
            await event.edit("⏱️ **ظبط التأخير**\n\nابعت رقمين: أقل وأكبر تأخير بالثواني\n\nمثال: `30 120`\nمن 30ث لدقيقتين عشوائي")
        elif data == 'stop_broadcast':
            if user_id in broadcast_tasks:
                broadcast_tasks[user_id].cancel()
                del broadcast_tasks[user_id]
                await event.edit("🛑 تم إيقاف الحملة", buttons=main_keyboard(user_id))
            else:
                await event.answer("مفيش حملة شغالة", alert=True)
        elif data == 'add_account':
            waiting_for[user_id] = 'account_phone'
            await event.edit("📱 **إضافة حساب**\n\nابعت رقم الهاتف:\nمثال: +201234567890")
        elif data == 'my_accounts':
            accounts = get_user_accounts(user_id)
            if not accounts:
                await event.edit("❌ مفيش حسابات", buttons=main_keyboard(user_id))
                return
            text = f"📱 **حساباتك في {SOURCE_NAME}** ({len(accounts)})\n\n"
            buttons = []
            for acc in accounts:
                acc_id, _, _, phone, username, _, last_used, groups_count = acc
                text += f"📞 {phone or username}\n📊 الجروبات: {groups_count}\n\n"
                buttons.append([Button.inline(f"🗑️ حذف {phone}", f'del_acc_{acc_id}')])
            buttons.append([Button.inline('🔙 رجوع', 'back_main')])
            await event.edit(text, buttons=buttons)
        elif data.startswith('del_acc_'):
            acc_id = int(data.split('_')[2])
            delete_account(acc_id, user_id)
            await event.answer("تم الحذف ✅")
            await event.edit("تم حذف الحساب", buttons=main_keyboard(user_id))
        elif data.startswith('sendto_all_'):
            name = data.split('_', 2)[2]
            if user_id not in TEMP_MEDIA or name not in TEMP_MEDIA[user_id]:
                await event.answer("الصورة مش موجودة", alert=True)
                return
            photo = TEMP_MEDIA[user_id][name]
            accounts = get_user_accounts(user_id)
            if not accounts:
                await event.answer("ضيف حسابات الأول", alert=True)
                return
            await event.edit(f"جاري إرسال `{name}` لكل الجروبات...")
            sent = 0
            for acc in accounts:
                acc_id, _, session_string, phone, username, _, _, _ = acc
                client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
                try:
                    await client.start()
                    groups = await get_all_groups(client)
                    for group in groups:
                        try:
                            await client.send_file(group, photo)
                            sent += 1
                            await asyncio.sleep(3)
                        except: pass
                    await client.disconnect()
                except: pass
            await event.edit(f"✅ تم إرسال الصورة لـ {sent} جروب تقريباً", buttons=main_keyboard(user_id))
        elif data == 'admin_panel':
            if not is_admin(user_id):
                return
            c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1 AND vip_expires >?", (datetime.now().isoformat(),))
            vip_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM accounts")
            acc_count = c.fetchone()[0]
            running, sent, failed = get_campaign_stats()
            await event.edit(f"👑 **لوحة الأدمن - {SOURCE_NAME}**\n\n👥 VIP نشط: {vip_count}\n📱 إجمالي الحسابات: {acc_count}\n🚀 حملات شغالة: {running}\n📤 إجمالي المرسل: {sent}\n❌ الفاشل: {failed}", buttons=admin_keyboard())
        elif data == 'admin_add_vip':
            if not is_admin(user_id):
                return
            waiting_for[user_id] = 'admin_add_vip_input'
            await event.edit("➕ **تفعيل VIP**\n\nابعت: user_id days\nمثال:\n123456789 30")
        elif data == 'admin_remove_vip':
            if not is_admin(user_id):
                return
            waiting_for[user_id] = 'admin_remove_vip_input'
            await event.edit("❌ **إلغاء VIP**\n\nابعت user_id:\nمثال: 123456789")
        elif data == 'admin_list_vips':
            if not is_admin(user_id):
                return
            vips = get_all_vips()
            if not vips:
                await event.edit("مفيش VIP نشط", buttons=admin_keyboard())
                return
            text = f"👑 **قائمة الـVIP في {SOURCE_NAME}** ({len(vips)})\n\n"
            for vip in vips[:20]:
                uid, uname, _, exp, _ = vip
                exp_date = safe_parse_date(exp).strftime('%Y-%m-%d')
                text += f"`{uid}` @{uname}\n📅 ينتهي: {exp_date}\n\n"
            await event.edit(text, buttons=admin_keyboard())
        elif data == 'admin_stats':
            if not is_admin(user_id):
                return
            c.execute("SELECT COUNT(*) FROM users")
            total_users = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM posts")
            total_posts = c.fetchone()[0]
            running, sent, failed = get_campaign_stats()
            await event.edit(f"📊 **إحصائيات {SOURCE_NAME}**\n\n👥 المستخدمين: {total_users}\n📝 المنشورات: {total_posts}\n🚀 حملات شغالة: {running}\n📤 المرسل: {sent}\n❌ الفاشل: {failed}", buttons=admin_keyboard())
        elif data == 'back_main':
            await event.edit("القائمة الرئيسية:", buttons=main_keyboard(user_id))

    @bot.on(events.NewMessage)
    async def handle_message(event):
        user_id = event.sender_id
        text = event.text
        if text == '/start' or text.startswith('/activate') or text.startswith('/save') or text.startswith('/send') or text.startswith('/list'):
            return
        if waiting_for.get(user_id) == 'post_content':
            media_id = None
            if event.media:
                media_id = event.file.id
            temp_data[user_id] = {'content': text or "", 'media_id': media_id}
            waiting_for[user_id] = 'post_style'
            await event.reply("🎨 **الخطوة 2/3: اختار التنسيق**", buttons=style_keyboard())
        elif waiting_for.get(user_id) == 'emoji_custom_input':
            custom_emoji = text.strip()
            data_dict = temp_data.get(user_id, {})
            post_id = save_post(user_id, data_dict['content'], data_dict.get('media_id'), data_dict['style'], custom_emoji)
            waiting_for[user_id] = None
            temp_data.pop(user_id, None)
            await event.reply(f"✅ **تم حفظ المنشور**\nID: {post_id}\nالإيموجي: {custom_emoji}\n\nدوس 'بدء حملة نشر' عشان تبدأ", buttons=main_keyboard(user_id))
        elif waiting_for.get(user_id) == 'broadcast_delay':
            try:
                parts = text.split()
                delay_min = int(parts[0])
                delay_max = int(parts[1])
                if delay_min < 10:
                    await event.reply("❌ أقل تأخير 10 ثواني")
                    return
                data = temp_data[user_id]
                campaign_id = create_campaign(user_id, data['post_id'], delay_min, delay_max)
                task = asyncio.create_task(broadcast_task(user_id, campaign_id, data['post_id'], data['accounts'], delay_min, delay_max))
                broadcast_tasks[user_id] = task
                waiting_for[user_id] = None
                temp_data.pop(user_id, None)
            except:
                await event.reply("❌ الصيغة غلط\nمثال: 30 120")
        elif waiting_for.get(user_id) == 'account_phone':
            if not text.startswith('+'):
                await event.reply("❌ لازم يبدأ بـ +\nمثال: +201234567890")
                return
            waiting_for[user_id] = 'account_code'
            temp_data[user_id] = {'phone': text}
            client = TelegramClient(StringSession(), int(API_ID), API_HASH)
            try:
                await client.connect()
                sent = await client.send_code_request(text)
                temp_data[user_id]['client'] = client
                temp_data[user_id]['phone_code_hash'] = sent.phone_code_hash
                await event.reply(f"📲 اتبعت كود لـ {text}\n\nابعته هنا:")
            except Exception as e:
                await event.reply(f"❌ خطأ: {str(e)}")
                waiting_for[user_id] = None
                await client.disconnect()
        elif waiting_for.get(user_id) == 'account_code':
            data = temp_data.get(user_id, {})
            client = data.get('client')
            if not client:
                waiting_for[user_id] = None
                return
            try:
                await client.sign_in(phone=data['phone'], code=text, phone_code_hash=data['phone_code_hash'])
                session_string = client.session.save()
                me = await client.get_me()
                add_account(user_id, session_string, data['phone'], me.username or f"user{me.id}")
                await event.reply(f"✅ تم إضافة الحساب\n@{me.username}", buttons=main_keyboard(user_id))
                await client.disconnect()
                waiting_for[user_id] = None
                temp_data.pop(user_id, None)
            except SessionPasswordNeededError:
                waiting_for[user_id] = 'account_2fa'
                await event.reply("🔒 الحساب عليه 2FA\nابعت كلمة السر:")
            except Exception as e:
                await event.reply(f"❌ الكود غلط: {str(e)}")
                waiting_for[user_id] = None
                await client.disconnect()
        elif waiting_for.get(user_id) == 'account_2fa':
            data = temp_data.get(user_id, {})
            client = data.get('client')
            if not client:
                return
            try:
                await client.sign_in(password=text)
                session_string = client.session.save()
                me = await client.get_me()
                add_account(user_id, session_string, data['phone'], me.username or f"user{me.id}")
                await event.reply(f"✅ تم إضافة الحساب\n@{me.username}", buttons=main_keyboard(user_id))
                await client.disconnect()
                waiting_for[user_id] = None
                temp_data.pop(user_id, None)
            except Exception as e:
                await event.reply(f"❌ كلمة السر غلط: {str(e)}")
                waiting_for[user_id] = None
                await client.disconnect()
        elif waiting_for.get(user_id) == 'admin_add_vip_input':
            if not is_admin(user_id):
                return
            try:
                parts = text.split()
                target_id = int(parts[0])
                days = int(parts[1])
                expires = add_vip(target_id, days)
                waiting_for[user_id] = None
                await event.reply(f"✅ تم التفعيل\nID: `{target_id}`\nينتهي: {expires.strftime('%Y-%m-%d')}", buttons=admin_keyboard())
                try:
                    await bot.send_message(target_id, f"💎 **تم تفعيل حسابك في {SOURCE_NAME}** ✅\nصالح لحد: {expires.strftime('%Y-%m-%d')}")
                except:
                    pass
            except:
                await event.reply("❌ الصيغة غلط\nuser_id days")
        elif waiting_for.get(user_id) == 'admin_remove_vip_input':
            if not is_admin(user_id):
                return
            try:
                target_id = int(text)
                remove_vip(target_id)
                waiting_for[user_id] = None
                await event.reply(f"✅ تم إلغاء VIP للـ `{target_id}`", buttons=admin_keyboard())
            except:
                await event.reply("❌ ID غلط")

def main():
    global bot
    if not all([API_ID, API_HASH, BOT_TOKEN, ADMIN_ID]):
        print("ERROR: Missing env vars")
        return
    init_db()
    bot = TelegramClient('broadcaster_bot', int(API_ID), API_HASH).start(bot_token=BOT_TOKEN)
    setup_handlers()
    print(f"{SOURCE_NAME} شغال...")
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()
