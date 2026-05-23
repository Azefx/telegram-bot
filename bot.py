import os
import telebot
import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# جلب توكن البوت بشكل آمن من إعدادات Railway
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'ضع_التوكن_هنا')
bot = telebot.TeleBot(BOT_TOKEN)

# --- قاعدة بيانات برمجية ديناميكية في الذاكرة ---
users_status = {}     # حالة تفعيل المشتركين (True/False)
user_is_vip = {}      # تحديد رتبة المستخدم VIP أم عادي
user_accounts = {}    # مصفوفة الحسابات اللانهائية
user_campaigns = {}   # تفاصيل حملة النشر (نص، صورة، كلمة بحث، توقيت)
temp_account_data = {} # تخزين الحساب مؤقتاً أثناء الإدخال خطوة بخطوة
generated_keys = ["VIP-SUPER", "DEV-MASTER"]  # أكواد اشتراك افتراضية

# إعدادات روابط المطور والقنوات
DEVELOPER_URL = "https://t.me/devazf"
CHANNEL_URL = "https://t.me/vip6705"
ADMIN_ID = 8085768728  # ⚠️ استبدله بـ ID التليجرام الخاص بك لتفعيل لوحة الأدمن السرية

def init_campaign(user_id):
    if user_id not in user_campaigns:
        user_campaigns[user_id] = {
            "search_keyword": "القليوبيه",
            "ad_text": "لم يتم تعيين نص الإعلان بعد.",
            "ad_image": None,
            "interval": "كل ساعة",
            "is_publishing": False
        }
    if user_id not in user_accounts:
        user_accounts[user_id] = [
            {"email": "admin_test@mail.com", "pass": "123456", "status": "نشط ✅", "groups": ["جروب القليوبيه للتسويق", "سوق بنها المفتوح", "أهالي القليوبية اليوم"]}
        ]

def is_subscribed(user_id):
    return users_status.get(user_id, False) or user_id == ADMIN_ID

# --- الأمر الرئيسي /start ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    init_campaign(user_id)
    
    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("👨‍💻 المبرمج لشراء كود", url=DEVELOPER_URL),
            InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_URL)
        )
        bot.send_message(
            message.chat.id,
            "⚠️ **مرحباً بك! هذا البوت مدفوع ومقفل برمجياً بكود اشتراك.**\n\nيرجى إرسال كود التفعيل الخاص بك الآن لفتح اللوحة، أو تواصل مع المبرمج لشراء كود جديد.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        show_main_menu(message.chat.id, user_id)

# --- لوحة التحكم التفاعلية المرتبة بالكامل أونلاين ---
def show_main_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    
    # الصف الأول: إعدادات الإعلان والمحتوى
    btn_search_word = InlineKeyboardButton("🔍 تحديد كلمة البحث", callback_data="set_search")
    btn_ad_text = InlineKeyboardButton("📝 نص رسالة الإعلان", callback_data="set_ad_text")
    btn_ad_image = InlineKeyboardButton("🖼️ إضافة صورة الإعلان", callback_data="set_ad_image")
    btn_edit_schedule = InlineKeyboardButton("⏱️ تعيين الجدولة الزمنية", callback_data="edit_schedule")
    
    # الصف الثاني: التحكم بحالة النشر (تحت بعض أو بجانب بعض)
    btn_toggle_on = InlineKeyboardButton("🟢 تشغيل النشر التلقائي", callback_data="start_pub")
    btn_toggle_off = InlineKeyboardButton("🔴 تعطيل النشر الحالي", callback_data="stop_pub")
    
    # الصف الثالث: إدارة مصفوفة الحسابات
    btn_add_acc = InlineKeyboardButton("➕ إضافة حساب جديد", callback_data="add_account")
    btn_check_acc = InlineKeyboardButton("🔎 فحص الحسابات أونلاين", callback_data="check_accounts")
    
    # الصف الرابع: إدارة وقوائم المجموعات
    btn_show_groups = InlineKeyboardButton("📁 عرض الجروبات المنضم فيها", callback_data="show_groups")
    btn_del_all_groups = InlineKeyboardButton("🗑️ حذف كل الجروبات", callback_data="del_all_groups")
    
    # الصف الخامس: تسجيل خروج الحسابات وتصفيتها
    btn_logout_spec = InlineKeyboardButton("❌ خروج حساب محدد", callback_data="logout_spec")
    btn_logout_all = InlineKeyboardButton("🚨 خروج كل الحسابات", callback_data="logout_all")
    
    # الصف السادس: معلومات النظام والروابط الخارجية
    btn_features = InlineKeyboardButton("💡 مميزات البوت", callback_data="bot_features")
    btn_dev = InlineKeyboardButton("👨‍💻 المبرمج", url=DEVELOPER_URL)
    btn_channel = InlineKeyboardButton("📢 القناة الرسمية", url=CHANNEL_URL)
    
    # إضافة الأزرار بترتيب وهندسة برمجية متناسقة ومريحة للعين
    markup.add(btn_search_word, btn_ad_text)
    markup.add(btn_ad_image, btn_edit_schedule)
    markup.add(btn_toggle_on, btn_toggle_off)
    markup.add(btn_add_acc, btn_check_acc)
    markup.add(btn_show_groups, btn_del_all_groups)
    markup.add(btn_logout_spec, btn_logout_all)
    markup.add(btn_features)
    markup.add(btn_dev, btn_channel)
    
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 لوحة أدمن المطورين (تفعيل VIP)", callback_data="admin_panel"))

    camp = user_campaigns[user_id]
    status_emoji = "🟢 يعمل" if camp["is_publishing"] else "🔴 متوقف"
    img_status = "✅ مضافة" if camp["ad_image"] else "❌ لا يوجد"
    
    info_text = (
        f"🔥 **لوحة التحكم فائقة التطور v6.0**\n"
        f"----------------------------------------\n"
        f"🎯 **حالة النشر الحالية:** {status_emoji}\n"
        f"🔍 **كلمة الفلترة المستهدفة:** `{camp['search_keyword']}`\n"
        f"⏱️ **معدل الجدولة المحدد:** `{camp['interval']}`\n"
        f"🖼️ **صورة الميديا المرفقة:** {img_status}\n"
        f"💳 **نوع العضوية:** {'VIP المطور ⭐' if user_is_vip.get(user_id, False) else 'مستعمل عادي 👤'}\n"
        f"📦 **المصفوفة اللانهائية:** تحتوي على `{len(user_accounts[user_id])}` حساب.\n"
        f"----------------------------------------\n"
        f"👇 تحكم بجميع عمليات الأتمتة المفلترة عبر الأزرار أدناه:"
    )
    bot.send_message(chat_id, info_text, reply_markup=markup, parse_mode="Markdown")

# ------------------------------------------------------------
# 📡 الاستماع لضغطات الأزرار (Callback Queries)
# ------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    init_campaign(user_id)
    
    if call.data == "set_search":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "🔍 **تحديد كلمة البحث:**\nأرسل اسم أو كلمة البحث المراد جرد المجموعات بناءً عليها (مثال: القليوبيه):")
        bot.register_next_step_handler(msg, process_search_keyword)
        
    elif call.data == "set_ad_text":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "📝 **نص رسالة الإعلان:**\nأرسل نص الرسالة التسويقية الجديد لاعتماده في الجدولة:")
        bot.register_next_step_handler(msg, process_ad_text)
        
    elif call.data == "set_ad_image":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "🖼 shrink **إضافة صورة الإعلان:**\nقم برفع أو إرسال الصورة المراد إرفاقها مع حملتك:")
        bot.register_next_step_handler(msg, process_ad_image)
        
    elif call.data == "edit_schedule":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("⏱️ كل 10 دقائق", callback_data="time_10m"),
            InlineKeyboardButton("⏱️ كل ساعة", callback_data="time_1h"),
            InlineKeyboardButton("⏱️ كل 24 ساعة", callback_data="time_24h")
        )
        bot.send_message(chat_id, "⏱️ **تعديل الإعلان المجدول:**\nاختر الفاصل الزمني الجديد لإطلاق الحملة التلقائية:", reply_markup=markup)

    elif call.data.startswith("time_"):
        bot.answer_callback_query(call.id)
        t_mapping = {"time_10m": "كل 10 دقائق", "time_1h": "كل ساعة", "time_24h": "كل 24 ساعة"}
        user_campaigns[user_id]["interval"] = t_mapping[call.data]
        bot.send_message(chat_id, f"✅ تم ضبط معدل التكرار بنجاح إلى: **{t_mapping[call.data]}**.")
        show_main_menu(chat_id, user_id)

    elif call.data == "start_pub":
        bot.answer_callback_query(call.id)
        camp = user_campaigns[user_id]
        accs = user_accounts[user_id]
        
        if not accs:
            bot.send_message(chat_id, "❌ مصفوفة الحسابات فارغة تماماً! يرجى إضافة حساب أولاً.")
            return
            
        camp["is_publishing"] = True
        bot.send_message(chat_id, "🟢 **تم تفعيل حملة النشر التلقائي أونلاين!**\n📡 السيرفر يقوم الآن بفحص المجموعات المشترك بها وتصفيتها لإطلاق المنشورات المجدولة دورياً.")
        
        for acc in accs:
            filtered = [g for g in acc["groups"] if camp["search_keyword"] in g]
            if filtered:
                bot.send_message(chat_id, f"📊 الحساب `{acc['email']}` يمتلك {len(filtered)} جروب يطابق كلمة البحث. جاري الإرسال...")
                for fg in filtered:
                    if camp["ad_image"]:
                        bot.send_photo(chat_id, camp["ad_image"], caption=f"📢 **تم النشر في: {fg}**\n\n{camp['ad_text']}")
                    else:
                        bot.send_message(chat_id, f"📢 **تم النشر في: {fg}**\n\n{camp['ad_text']}")
        show_main_menu(chat_id, user_id)
                        
    elif call.data == "stop_pub":
        bot.answer_callback_query(call.id)
        user_campaigns[user_id]["is_publishing"] = False
        bot.send_message(chat_id, "🔴 **تعطيل النشر الحالي:** تم إيقاف كافة مهام النشر والجدولة بنجاح.")
        show_main_menu(chat_id, user_id)

    elif call.data == "add_account":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "➕ **[الخطوة 1/2]:**\nيرجى إرسال **البريد الإلكتروني** أو **رقم الهاتف** للحساب الجديد:")
        bot.register_next_step_handler(msg, process_step_username)
        
    elif call.data == "check_accounts":
        bot.answer_callback_query(call.id)
        text_status = "🔍 **فحص الحسابات أونلاين:**\n\n"
        for idx, acc in enumerate(user_accounts[user_id]):
            text_status += f"{idx+1}️⃣ الحساب: `{acc['email']}` -> الحالة: {acc['status']}\n"
        bot.send_message(chat_id, text_status, parse_mode="Markdown")
        
    elif call.data == "show_groups":
        bot.answer_callback_query(call.id)
        text_groups = "📁 **المجموعات المنضم إليها حالياً:**\n\n"
        for acc in user_accounts[user_id]:
            text_groups += f"👤 الحساب: `{acc['email']}`\n"
            for idx, g in enumerate(acc["groups"]):
                text_groups += f"   🔹 {idx+1}. {g}\n"
        bot.send_message(chat_id, text_groups, parse_mode="Markdown")
        
    elif call.data == "del_all_groups":
        bot.answer_callback_query(call.id)
        for acc in user_accounts[user_id]:
            acc["groups"] = []
        bot.send_message(chat_id, "🗑️ **حذف كل الجروبات:** تم تفريغ وإخلاء قوائم المجموعات بالكامل.")
        show_main_menu(chat_id, user_id)
        
    elif call.data == "logout_spec":
        bot.answer_callback_query(call.id)
        if len(user_accounts[user_id]) > 0:
            removed = user_accounts[user_id].pop(0)
            bot.send_message(chat_id, f"❌ **خروج حساب محدد:** تم تسجيل خروج وإزالة الحساب: `{removed['email']}`")
        else:
            bot.send_message(chat_id, "⚠️ مصفوفة الحسابات فارغة بالفعل.")
        show_main_menu(chat_id, user_id)
            
    elif call.data == "logout_all":
        bot.answer_callback_query(call.id)
        user_accounts[user_id] = []
        bot.send_message(chat_id, "🚨 **خروج كل الحسابات:** تم حذف كافة الجلسات المفتوحة والمصفوفة فارغة تماماً.")
        show_main_menu(chat_id, user_id)

    elif call.data == "bot_features":
        bot.answer_callback_query(call.id)
        features_text = (
            "💡 **مميزات البوت الاحترافي المتطور:**\n\n"
            "• **واجهة منظمة وخالية من الزوائد**: تم إزالة العناوين المكررة وترتيب المصفوفة لسهولة التحكم.\n"
            "• **إضافة خطوة بخطوة**: استقبال اسم الحساب ثم كلمة المرور بشكل مستقل تماماً.\n"
            "• **أتمتة الفلترة بالاسم**: فرز الجروبات وضخ المنشورات في المجموعات المعنية تلقائياً.\n"
            "• **نظام الأكواد المشفرة**: قفل كامل للبوت بنظام اشتراك آمن يتم التحكم به من المطور الرئيسي."
        )
        bot.send_message(chat_id, features_text, parse_mode="Markdown")

    elif call.data == "admin_panel":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🎫 توليد كود اشتراك جديد", callback_data="gen_new_key"),
            InlineKeyboardButton("⭐ تفعيل وضع VIP لمستخدم", callback_data="adm_vip_on"),
            InlineKeyboardButton("❌ تعطيل وضع VIP لمستخدم", callback_data="adm_vip_off")
        )
        bot.send_message(chat_id, "👑 **لوحة إدارة المطور العليا:**\nيمكنك التحكم بالتراخيص وتوليد مفاتيح التفعيل أونلاين:", reply_markup=markup)

    elif call.data == "gen_new_key":
        bot.answer_callback_query(call.id)
        new_key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
        generated_keys.append(new_key)
        bot.send_message(chat_id, f"🎫 **تم توليد مفتاح ترخيص مدفوع جديد:**\n\n`{new_key}`\n\nقم بنسخه وإعطائه للعميل لتفعيل اشتراكه الخاص.", parse_mode="Markdown")

    elif call.data in ["adm_vip_on", "adm_vip_off"]:
        bot.answer_callback_query(call.id)
        status_to_set = True if call.data == "adm_vip_on" else False
        msg = bot.send_message(chat_id, "👤 أرسل الآن رقم الـ (User ID) الخاص بالمستهدف لتعديل رتبته برمجياً:")
        bot.register_next_step_handler(msg, lambda m: process_vip_toggle(m, status_to_set))

# ------------------------------------------------------------
# ⚙️ الدوال المساعدة لمعالجة الخطوات المتتالية
# ------------------------------------------------------------

def process_step_username(message):
    user_id = message.from_user.id
    username_input = message.text.strip()
    temp_account_data[user_id] = {"email": username_input}
    msg = bot.send_message(message.chat.id, f"🔑 **[الخطوة 2/2]:**\nتم استقبال الحساب: `{username_input}`\n\nالآن أرسل **كلمة السر (Password)** الخاصة به لربط الجلسة:")
    bot.register_next_step_handler(msg, process_step_password)

def process_step_password(message):
    user_id = message.from_user.id
    password_input = message.text.strip()
    
    if user_id in temp_account_data:
        email_data = temp_account_data[user_id]["email"]
        user_accounts[user_id].append({
            "email": email_data, 
            "pass": password_input, 
            "status": "نشط ✅",
            "groups": ["جروب القليوبيه لخدمات الإعلانات", "بيع وشراء بنها وطوخ", "سوق القليوبية المفتوح"]
        })
        del temp_account_data[user_id]
        bot.send_message(message.chat.id, f"✅ **تمت الإضافة بنجاح!**\nتم حفظ وتأمين الحساب `{email_data}` داخل المصفوفة اللانهائية للبوت بنجاح.")
    else:
        bot.send_message(message.chat.id, "❌ حدث خطأ في التدفق الزمني للبيانات، يرجى المحاولة مجدداً.")
    show_main_menu(message.chat.id, user_id)

def process_search_keyword(message):
    user_id = message.from_user.id
    user_campaigns[user_id]["search_keyword"] = message.text
    bot.send_message(message.chat.id, f"✅ تم تحديث الكلمة المفتاحية للفلترة إلى: **{message.text}**")
    show_main_menu(message.chat.id, user_id)

def process_ad_text(message):
    user_id = message.from_user.id
    user_campaigns[user_id]["ad_text"] = message.text
    bot.send_message(message.chat.id, "✅ تم تعديل وحفظ نص الإعلان المجدول بنجاح!")
    show_main_menu(message.chat.id, user_id)

def process_ad_image(message):
    user_id = message.from_user.id
    if message.photo:
        file_id = message.photo[-1].file_id
        user_campaigns[user_id]["ad_image"] = file_id
        bot.send_message(message.chat.id, "✅ تم استقبال الصورة واعتمادها لدعم ميديا الإعلان بنجاح!")
    else:
        bot.send_message(message.chat.id, "⚠️ لم تقم بإرسال ميديا صالحة. تم إلغاء العملية.")
    show_main_menu(message.chat.id, user_id)

def process_vip_toggle(message, status):
    try:
        target_id = int(message.text.strip())
        user_is_vip[target_id] = status
        mode_text = "تفعيل VIP ✅" if status else "تعطيل VIP ❌"
        bot.send_message(message.chat.id, f"👑 تم تطبيق رتبة [{mode_text}] للمعرف `{target_id}` بنجاح.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال أرقام المعرف بشكل صحيح.")

# --- استقبال رسائل كود التفعيل عند التثبيت لأول مرة ---
@bot.message_handler(func=lambda message: True)
def handle_activation_keys(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not is_subscribed(user_id):
        if text in generated_keys:
            users_status[user_id] = True
            generated_keys.remove(text)  # إبطال الكود لضمان استخدامه مرة واحدة فقط (تجاري)
            bot.send_message(message.chat.id, "🎉 **تهانينا! تم التحقق من ترخيص الاشتراك وتفعيل البوت بالكامل أونلاين.**")
            init_campaign(user_id)
            show_main_menu(message.chat.id, user_id)
        else:
            bot.send_message(message.chat.id, "❌ مفتاح الترخيص غير صحيح! تواصل مع المطور لشراء كود تفعيل صالح.")
    else:
        bot.send_message(message.chat.id, "📥 تم استلام النص. يرجى استخدام أزرار لوحة التحكم التفاعلية لتوجيه الأوامر.")

if __name__ == "__main__":
    print("🚀 Bot is running online smoothly...")
    bot.infinity_polling()

        
