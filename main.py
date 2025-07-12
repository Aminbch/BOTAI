import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)
from telegram.constants import ParseMode

# --- 1. الإعدادات ---
# التوكن الخاص بالبوت الرئيسي
MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "7885095446:AAHrqDP_AYb3Zk6Omj9eRCzZ-kVS_TlH998")
# التوكن الخاص ببوت التحكم (الإشعارات)
CONTROL_BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "8116069580:AAG9GFpj89FUArrqopdSuuIF9STOL_KJtug")
# الأيدي الخاص بك لاستقبال الإشعارات في بوت التحكم
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6072979272") # استخدم نفس الـ ID الخاص بك

# --- 2. إعداد تسجيل المعلومات ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. إعداد بوت التحكم ---
# نقوم بإنشاء كائن Bot منفصل لبوت التحكم
# هذا يسمح للبوت الرئيسي بإرسال رسائل عبر بوت التحكم
control_bot = Bot(token=CONTROL_BOT_TOKEN)

# --- 4. دالة إرسال الإشعارات للأدمن ---
async def send_admin_notification(text: str):
    """
    ترسل رسالة من بوت التحكم إلى الأدمن.
    """
    try:
        await control_bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info(f"تم إرسال إشعار إلى الأدمن بنجاح.")
    except Exception as e:
        logger.error(f"فشل في إرسال إشعار للأدمن: {e}")

# --- 5. دوال إنشاء القوائم (Menus) ---
def get_main_menu(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    user_data = context.user_data
    balance = user_data.setdefault('balance', 0)
    user_id = context._user_id
    text = (
        "مرحباً بك في بوت كريك ✨\n\n"
        f"👈 رصيد حسابك: <b>{balance}</b> نقطة\n"
        f"👈 ايدي حسابك: <code>{user_id}</code>"
    )
    keyboard = [
        [InlineKeyboardButton("الخدمات 🛒", callback_data='menu_services')],
        [
            InlineKeyboardButton("تجميع 💚", callback_data='menu_collect'),
            InlineKeyboardButton("الحساب 🎗️", callback_data='menu_account')
        ],
        [InlineKeyboardButton("الهدية اليومية 🎁", callback_data='action_daily_gift')]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def get_services_menu() -> tuple[str, InlineKeyboardMarkup]:
    text = "اختر التطبيق الذي توده 📱"
    keyboard = [
        [
            InlineKeyboardButton("تيلغرام 🩵", callback_data='service_telegram'),
            InlineKeyboardButton("انستغرام 🧡", callback_data='service_instagram')
        ],
        [InlineKeyboardButton("تيك توك 🖤", callback_data='service_tiktok')],
        [InlineKeyboardButton("العودة ✔️", callback_data='back_to_main')]
    ]
    return text, InlineKeyboardMarkup(keyboard)

# --- 6. دوال معالجة الأوامر والضغطات ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يعالج الأمر /start، يرسل إشعاراً للأدمن، ويعرض القائمة الرئيسية.
    """
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} ({user.id}) بدأ/عاد إلى البوت.")
    
    # التحقق إذا كان هذا هو أول تفاعل للمستخدم مع البوت
    is_new_user = 'balance' not in context.user_data
    
    # عرض القائمة الرئيسية للمستخدم
    text, keyboard = get_main_menu(context)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    # إذا كان مستخدماً جديداً، أرسل إشعاراً للأدمن
    if is_new_user:
        logger.info(f"مستخدم جديد! {user.first_name} ({user.id}). إرسال إشعار...")
        # إنشاء رسالة الإشعار
        notification_text = (
            "<b>🎉 مستخدم جديد انضم إلى البوت!</b>\n\n"
            f"<b>الاسم:</b> {user.full_name}\n"
            f"<b>المعرف:</b> @{user.username if user.username else 'لا يوجد'}\n"
            f"<b>الأيدي:</b> <code>{user.id}</code>\n"
            f"<b>رابط مباشر:</b> <a href='tg://user?id={user.id}'>اضغط هنا</a>"
        )
        # إرسال الإشعار
        await send_admin_notification(notification_text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action = query.data
    logger.info(f"المستخدم {query.from_user.id} ضغط على زر: {action}")

    if action == 'menu_services':
        text, keyboard = get_services_menu()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    elif action == 'back_to_main':
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    elif action == 'action_daily_gift':
        await handle_daily_gift(query, context)
    elif action == 'menu_collect':
        await query.answer(text="قسم تجميع النقاط - سيتم إضافته قريباً!", show_alert=True)
    elif action == 'menu_account':
        await query.answer(text="قسم الحساب - سيتم إضافته قريباً!", show_alert=True)
    elif action.startswith('service_'):
        service_name = action.split('_')[1].capitalize()
        await query.answer(text=f"خدمات {service_name} - سيتم إضافتها قريباً!", show_alert=True)

async def handle_daily_gift(query, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    last_gift_time = user_data.get('last_gift_time')
    
    if last_gift_time and (datetime.now() - last_gift_time) < timedelta(hours=24):
        remaining_time = (last_gift_time + timedelta(hours=24)) - datetime.now()
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await query.answer(text=f"⏳ عذراً، لقد استلمت هديتك بالفعل. عد بعد {hours} ساعة و {minutes} دقيقة.", show_alert=True)
    else:
        user_data['balance'] = user_data.setdefault('balance', 0) + 40
        user_data['last_gift_time'] = datetime.now()
        logger.info(f"المستخدم {query.from_user.id} حصل على الهدية اليومية (40 نقطة).")
        
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        await query.answer(text="🎉 تهانينا! لقد حصلت على 40 نقطة كهدية يومية.", show_alert=True)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("حدث استثناء:", exc_info=context.error)

# --- 7. الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    logger.info("🚀 بدء تشغيل البوت الرئيسي...")
    
    if not MAIN_BOT_TOKEN or not CONTROL_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.critical("خطأ فادح: أحد التوكنات أو ايدي الأدمن غير موجود. يرجى إعدادهم كمتغيرات بيئة.")
        return
        
    persistence = PicklePersistence(filepath=Path("bot_data.pickle"))
    
    application = (
        Application.builder()
        .token(MAIN_BOT_TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    application.run_polling()
    logger.info("🛑 تم إيقاف البوت الرئيسي.")

if __name__ == "__main__":
    main()
