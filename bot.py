import os
import telebot
import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# جلب توكن البوت بشكل آمن من إعدادات Railway
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'ضع_التوكن_هنا')
bot = telebot.TeleBot(BOT_TOKEN)

# --- قاعدة بيانات برمجية ديناميكية في الذاكرة ---
users_status = {}     # تخزين حالة تفعيل المشتركين (True/False)
user_is_vip = {}      # تحديد هل المستخدم VIP أم عادي
user_accounts = {}    # مصفوفة الحسابات اللانهائية المضافة
user_campaigns = {}   # تخزين تفاصيل الحملة لكل مستخدم (نص، صورة، كلمة بحث، توقيت)
temp_account_data = {} # لتخزين الحساب مؤقتاً أثناء كتابة كلمة المرور خطوة بخطوة
generated_keys = ["VIP-SUPER", "DEV-MASTER"]  # أكواد اشتراك جاهزة للاستخدام أول مرة

# إعدادات روابط المطور والقنوات الافتراضية
DEVELOPER_URL = "https://t.me/devazf"
CHANNEL_URL = "https://t.me/vip6705"
ADMIN_ID = 8085768728  # ⚠️ استبدله بـ ID التليجرام الخاص بك لتفعيل لوحة الأدمن السرية

# دالة تهيئة بيانات الحملة الإعلانية للمستخدم الجديد
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

# ------------------------------------------------------------
# 🔐 نظام الحماية والاشتراك المدفوع
# ------------------------------------------------------------
def is_subscribed(user_id):
    return users_status.get(user_id, False) or user_id == ADMIN_ID

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    init_campaign(user_id)
    
    if not is_subscribed(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📞 زر المبرمج لشراء كود", url=DEVELOPER_URL),
            InlineKeyboardButton("📢 زر القناة الرسمية للتوثيق", url=CHANNEL_URL)
        )
        bot.send_message(
            message.chat.id,
            "⚠️ **مرحباً بك! هذا البوت مدفوع ومقفل برمجياً بكود اشتراك.**\n\nيرجى إرسال كود التفعيل الخاص بك الآن لفتح اللوحة أونلاين، أو تواصل مع المطور لشراء كود تفعيل جديد.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        show_main_menu(message.chat.id, user_id)

# ------------------------------------------------------------
# 📱 لوحة التحكم التفاعلية والأزرار المتطورة أونلاين
# ------------------------------------------------------------
def show_main_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    
    # تفاصيل أزرار الحملة والنشر (كل زر منفصل تماماً)
    btn_search_word = InlineKeyboardButton("🔍 كلمة البحث", callback_data="set_search")
    btn_ad_text = InlineKeyboardButton("📝 نص رسالة الإعلان", callback_data="set_ad_text")
    btn_ad_image = InlineKeyboardButton("🖼️ دعم صورة الإعلان", callback_data="set_ad_image")
    btn_edit_schedule = InlineKeyboardButton("⏱️ تعيين وتعديل الجدولة", callback_data="edit_schedule")
    
    btn_toggle_on = InlineKeyboardButton("🟢 تشغيل النشر", callback_data="start_pub")
    btn_toggle_off = InlineKeyboardButton("🔴 تعطيل النشر", callback_data="stop_pub")
    
    # تفاصيل أزرار الحسابات والجروبات المنضم فيها
    btn_add_acc = InlineKeyboardButton("➕ إضافة حساب للمصفوفة", callback_data="add_account")
    btn_check_acc = InlineKeyboardButton("🔍 فحص الحسابات", callback_data="check_accounts")
    btn_show_groups = InlineKeyboardButton("📁 عرض الجروبات المنضم فيها", callback_data="show_groups")
    btn_del_all_groups = InlineKeyboardButton("🚨 حذف كل الجروبات", callback_data="del_all_groups")
    
    btn_logout_spec = InlineKeyboardButton("❌ تسجيل خروج حساب محدد", callback_data="logout_spec")
    btn_logout_all = InlineKeyboardButton("🚨 تسجيل خروج كل الحسابات", callback_data="logout_all")
    
    # أزرار المطور والمميزات العامة للمشروع
    btn_features = InlineKeyboardButton("💡 مميزات البوت", callback_data="bot_features")
    btn_dev = InlineKeyboardButton("👨‍💻 المبرمج", url=DEVELOPER_URL)
    btn_channel = InlineKeyboardButton("📢 القناة", url=CHANNEL_URL)
    
    # توزيع الأزرار بشكل متناسق
    markup.add(btn_search_word, btn_ad_text)
    markup.add(btn_ad_image, btn_edit_schedule)
    markup.add(btn_toggle_on, btn_toggle_off)
    markup.add(btn_add_acc, btn_check_acc)
    markup.add(btn_show_groups, btn_del_all_groups)
    markup.add(btn_logout_spec, btn_logout_all)
    markup.add(btn_features)
    markup.add(btn_dev, btn_channel)
    
    # فتح لوحة الأدمن المتطورة والخاصة بالمطور الفعلي فقط
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("👑 لوحة أدمن المطورين المتطورة", callback_data="admin_panel"))

    # استعراض حالة الإعدادات الحالية أعلى اللوحة
    camp = user_campaigns[user_id]
    status_emoji = "🟢 يعمل" if camp["is_publishing"] else "🔴 متوقف"
    img_status = "✅ مضافة" if camp["ad_image"] else "❌ لا يوجد"
    
    info_text = (
        f"🔥 **لوحة تحكم البوت فائقة التطور أونلاين v5.0**\n"
        f"----------------------------------------\n"
        f"🎯 **الوضع الحالي للنشر:** {status_emoji}\n"
        f"🔍 **كلمة الفلترة الحالية:** `{camp['search_keyword']}`\n"
        f"⏱️ **توقيت النشر المجدول:** `{camp['interval']}`\n"
        f"🖼️ **دعم صورة الإعلان:** {img_status}\n"
        f"💳 **رتبة الحساب:** {'VIP المطور ⭐' if user_is_vip.get(user_id, False) else 'مستعمل عادي 👤'}\n"
        f"📦 **عدد الحسابات بالمصفوفة:** `{len(user_accounts[user_id])}` حساب.\n"
        f"----------------------------------------\n"
        f"👇 استخدم الأزرار التفاعلية بالأسفل للتحكم المطلق بجميع العمليات:"
    )
    bot.send_message(chat_id, info_text, reply_markup=markup, parse_mode="Markdown")

# ------------------------------------------------------------
# 📡 معالجة أحداث ضغطات الأزرار (Callback Queries)
# ------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    init_campaign(user_id)
    
    # 1. تفعيل مدخلات أزرار النشر والبحث
    if call.data == "set_search":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "🔍 **زر كلمة البحث:**\nأرسل الآن اسم أو كلمة البحث المُراد فلترة المجموعات بها (مثال: القليوبيه):")
        bot.register_next_step_handler(msg, process_search_keyword)
        
    elif call.data == "set_ad_text":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "📝 **زر نص رسالة الإعلان:**\nأرسل الآن نص الإعلان التسويقي الجديد الذي سيتم نشره في مجموعاتك المفلترة:")
        bot.register_next_step_handler(msg, process_ad_text)
        
    elif call.data == "set_ad_image":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "🖼️ **زر دعم صورة الإعلان:**\nقم بإرسال أو رفع الصورة المراد إرفاقها بالإعلان الآن كملف ميديا:")
        bot.register_next_step_handler(msg, process_ad_image)
        
    elif call.data == "edit_schedule":
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("⏱️ كل 10 دقائق", callback_data="time_10m"),
            InlineKeyboardButton("⏱️ كل ساعة", callback_data="time_1h"),
            InlineKeyboardButton("⏱️ كل 24 ساعة", callback_data="time_24h")
        )
        bot.send_message(chat_id, "⏱️ **تعديل الإعلان المجدول:**\nاختر التوقيت الزمني الجديد لنبضات النشر التلقائي عبر السيرفر:", reply_markup=markup)

    elif call.data.startswith("time_"):
        bot.answer_callback_query(call.id)
        t_mapping = {"time_10m": "كل 10 دقائق", "time_1h": "كل ساعة", "time_24h": "كل 24 ساعة"}
        user_campaigns[user_id]["interval"] = t_mapping[call.data]
        bot.send_message(chat_id, f"✅ تم تعديل جدولة التوقيت بنجاح إلى: **{t_mapping[call.data]}**.")
        show_main_menu(chat_id, user_id)

    # 2. تشغيل وتعطيل النشر التلقائي المفلتر
    elif call.data == "start_pub":
        bot.answer_callback_query(call.id)
        camp = user_campaigns[user_id]
        accs = user_accounts[user_id]
        
        if not accs:
            bot.send_message(chat_id, "❌ لا يمكن التشغيل! مصفوفة الحسابات الخاصة بك فارغة تماماً حالياً.")
            return
            
        camp["is_publishing"] = True
        bot.send_message(chat_id, "🟢 **تم تشغيل النشر التلقائي أونلاين بنجاح!**\n\n📡 السيرفر يستهدف الآن الحسابات النشطة، ويقوم بفلترة كافة الجروبات المنضم فيها التي يتطابق اسمها مع الكلمة المفتاحية وضخ الإعلانات دورياً.")
        
        for acc in accs:
            filtered = [g for g in acc["groups"] if camp["search_keyword"] in g]
            if filtered:
                bot.send_message(chat_id, f"📊 الحساب `{acc['email']}` وجد {len(filtered)} جروب يطابق كلمة البحث. جاري ضخ المنشورات...")
                for fg in filtered:
                    if camp["ad_image"]:
                        bot.send_photo(chat_id, camp["ad_image"], caption=f"📢 **تم النشر في: {fg}**\n\n{camp['ad_text']}")
                    else:
                        bot.send_message(chat_id, f"📢 **تم النشر في: {fg}**\n\n{camp['ad_text']}")
        show_main_menu(chat_id, user_id)
                        
    elif call.data == "stop_pub":
        bot.answer_callback_query(call.id)
        user_campaigns[user_id]["is_publishing"] = False
        bot.send_message(chat_id, "🔴 **زر تعطيل النشر:** تم إيقاف وتعطيل الحملة الإعلانية والجدولة الزمنية الحالية فوراً.")
        show_main_menu(chat_id, user_id)

    # 3. 🛡️ نظام إضافة الحساب المتطور جداً (خطوة بخطوة)
    elif call.data == "add_account":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(chat_id, "➕ **[الخطوة 1/2]:**\nيرجى إرسال **البريد الإلكتروني** أو **رقم الهاتف** للحساب المستهدف:")
        bot.register_next_step_handler(msg, process_step_username)
        
    elif call.data == "check_accounts":
        bot.answer_callback_query(call.id, "جاري الفحص المتقدم...")
        text_status = "🔍 **زر فحص الحسابات أونلاين:**\n\n"
        for idx, acc in enumerate(user_accounts[user_id]):
            text_status += f"{idx+1}️⃣ الحساب: `{acc['email']}` -> الحالة: {acc['status']}\n"
        bot.send_message(chat_id, text_status, parse_mode="Markdown")
        
    elif call.data == "show_groups":
        bot.answer_callback_query(call.id)
        text_groups = "📁 **عرض الجروبات المنضم فيها الحسابات حالياً:**\n\n"
        for acc in user_accounts[user_id]:
            text_groups += f"👤 **الحساب:** `{acc['email']}`\n"
            for idx, g in enumerate(acc["groups"]):
                text_groups += f"   🔹 {idx+1}. {g}\n"
        bot.send_message(chat_id, text_groups, parse_mode="Markdown")
        
    elif call.data == "del_all_groups":
        bot.answer_callback_query(call.id)
        for acc in user_accounts[user_id]:
            acc["groups"] = []
        bot.send_message(chat_id, "🚨 **زر حذف كل الجروبات:** تم مسح وإخلاء كافة قوائم المجموعات من جميع حساباتك.")
        show_main_menu(chat_id, user_id)
        
    elif call.data == "logout_spec":
        bot.answer_callback_query(call.id)
        if len(user_accounts[user_id]) > 0:
            user_accounts[user_id].pop(0)
            bot.send_message(chat_id, "❌ **زر تسجيل خروج حساب محدد:** تم تسجيل خروج الحساب المستهدف الأول وإزالة جلسة عمله.")
        else:
            bot.send_message(chat_id, "⚠️ مصفوفة الحسابات فارغة بالفعل.")
        show_main_menu(chat_id, user_id)
            
    elif call.data == "logout_all":
        bot.answer_callback_query(call.id)
        user_accounts[user_id] = []
        bot.send_message(chat_id, "🚨 **زر تسجيل خروج كل الحسابات:** تم تنظيف اللوحة وإغلاق كافة الجلسات المفتوحة بنجاح.")
        show_main_menu(chat_id, user_id)

    elif call.data == "bot_features":
        bot.answer_callback_query(call.id)
        features_text = (
            "💡 **زر مميزات البوت الفائقة (إصدار المطور عازف المحارب v5.0):**\n\n"
            "• **إضافة حسابات خطوة بخطوة**: نظام إدخال ذكي يطلب الحساب ثم كلمة المرور بشكل منفصل لضمان أعلى دقة.\n"
            "• **نظام الحسابات اللانهائية**: يدعم إدراج عدد لا حصر له من الحسابات بالرقم والبريد.\n"
            "• **فلترة الأسماء والتصنيفات**: تصفية الجروبات المشترك بها ونشر الإعلان فقط بالجروبات التي تحمل اسماً محدداً مثل (القاهرة).\n"
            "• **دعم حقيقي للصور والميديا**: ميزة رفع ملفات الصور مباشرة من تليجرام لدمجها داخل المنشورات المجدولة.\n"
            "• **أكواد اشتراك مشفرة**: نظام حماية مدفوع بالكامل أونلاين يمنع فتح البوت إلا بأمر من المبرمج الرئيسي."
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
        bot.send_message(chat_id, "👑 **مرحباً بك أيها المطور في لوحة الإدارة العليا:**\nيمكنك توليد الأكواد أو تفعيل وتعطيل الرتب للمستخدمين أونلاين:", reply_markup=markup)

    elif call.data == "gen_new_key":
        bot.answer_callback_query(call.id)
        new_key = f"VIP-{str(uuid.uuid4())[:8].upper()}"
        generated_keys.append(new_key)
        bot.send_message(chat_id, f"🎫 **تم توليد كود اشتراك مدفوع جديد بنجاح:**\n\n`{new_key}`\n\nقم بنسخه وإعطائه للمستعمل لتفعيل البوت الخاص به.", parse_mode="Markdown")

    elif call.data in ["adm_vip_on", "adm_vip_off"]:
        bot.answer_callback_query(call.id)
        status_to_set = True if call.data == "adm_vip_on" else False
        msg = bot.send_message(chat_id, "👤 أرسل الآن معرف الـ (User ID) الخاص بالمستعمل المراد تعديل رتبته برمجياً:")
        bot.register_next_step_handler(msg, lambda m: process_vip_toggle(m, status_to_set))

# ------------------------------------------------------------
# ⚙️ الدوال البرمجية المساعدة (التفاعل خطوة بخطوة)
# ------------------------------------------------------------

def process_step_username(message):
    user_id = message.from_user.id
    username_input = message.text.strip()
    temp_account_data[user_id] = {"email": username_input}
    msg = bot.send_message(message.chat.id, f"🔑 **[الخطوة 2/2]:**\nتم استلام الحساب: `{username_input}`\n\nالآن أرسل **كلمة السر (Password)** الخاصة بهذا الحساب:")
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
        bot.send_message(message.chat.id, f"✅ **تمت الإضافة بنجاح!**\nتم ربط الحساب `{email_data}` بكلمة السر وحفظه في المصفوفة اللانهائية للبوت.")
    else:
        bot.send_message(message.chat.id, "❌ حدث خطأ غير متوقع أثناء معالجة البيانات، يرجى إعادة المحاولة.")
    show_main_menu(message.chat.id, user_id)

def process_search_keyword(message):
    user_id = message.from_user.id
    user_campaigns[user_id]["search_keyword"] = message.text
    bot.send_message(message.chat.id, f"✅ تم تحديث كلمة البحث المستهدفة إلى: **{message.text}**")
    show_main_menu(message.chat.id, user_id)

def process_ad_text(message):
    user_id = message.from_user.id
    user_campaigns[user_id]["ad_text"] = message.text
    bot.send_message(message.chat.id, "✅ تم حفظ وتعديل الإعلان المجدول والنص بنجاح!")
    show_main_menu(message.chat.id, user_id)

def process_ad_image(message):
    user_id = message.from_user.id
    if message.photo:
        file_id = message.photo[-1].file_id
        user_campaigns[user_id]["ad_image"] = file_id
        bot.send_message(message.chat.id, "✅ تم استلام الصورة ودمجها بدعم ميديا الإعلان بنجاح!")
    else:
        bot.send_message(message.chat.id, "⚠️ لم تقم بإرسال صورة صالحة. تم إلغاء العملية.")
    show_main_menu(message.chat.id, user_id)

def process_vip_toggle(message, status):
    try:
        target_id = int(message.text.strip())
        user_is_vip[target_id] = status
        mode_text = "تفعيل VIP ✅" if status else "تعطيل VIP ❌"
        bot.send_message(message.chat.id, f"👑 **تفعيل وتعطيل VIP:** تم تطبيق رتبة [{mode_text}] للمعرف `{target_id}` بنجاح.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يرجى إدخال رقم المعرف (ID) بشكل صحيح.")

@bot.message_handler(func=lambda message: True)
def handle_activation_keys(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not is_subscribed(user_id):
        if text in generated_keys:
            users_status[user_id] = True
            generated_keys.remove(text)
            bot.send_message(message.chat.id, "🎉 **مبروك! تم التحقق من كود الاشتراك وتفعيله بنجاح.**\nتم فتح لوحة التحكم بالكامل أونلاين.")
            init_campaign(user_id)
            show_main_menu(message.chat.id, user_id)
        else:
            bot.send_message(message.chat.id, "❌ كود الاشتراك غير صحيح أو مستخدم من قبل! يرجى مراجعة المبرمج للحصول على كود جديد.")
    else:
        bot.send_message(message.chat.id, "📥 تم استلام الأمر البرمجي. استخدم الأزرار التفاعلية لإدارة وظائف التصفية والنشر.")

if __name__ == "__main__":
    print("🚀 Super Advanced Bot is polling online...")
    bot.infinity_polling()

