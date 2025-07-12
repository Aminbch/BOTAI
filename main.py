import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

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
MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "7885095446:AAHrqDP_AYb3Zk6Omj9eRCzZ-kVS_TlH998")
CONTROL_BOT_TOKEN = os.getenv("CONTROL_BOT_TOKEN", "8116069580:AAG9GFpj89FUArrqopdSuuIF9STOL_KJtug")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6072979272")

# --- 2. إعداد تسجيل المعلومات ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. إعداد بوت التحكم ---
control_bot = Bot(token=CONTROL_BOT_TOKEN)

# --- 4. دالة إرسال الإشعارات للأدمن ---
async def send_admin_notification(text: str):
    try:
        await control_bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info("تم إرسال إشعار إلى الأدمن بنجاح.")
    except Exception as e:
        logger.error(f"فشل في إرسال إشعار للأدمن: {e}")

# --- 5. دوال إنشاء القوائم (Menus) ---
def get_main_menu(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    user_data = context.user_data
    balance = user_data.setdefault('balance', 0)
    user_id = context._user_id

    text = (
        "أهلاً بك في عالم الخدمات الرقمية مع بوت كريك ✨\n\n"
        f"▫️ رصيدك الحالي: <b>{balance}</b> نقطة\n"
        f"▫️ معرف المستخدم: <code>{user_id}</code>"
    )
    
    # تصميم جديد ومزخرف للأزرار
    keyboard = [
        [InlineKeyboardButton("خـدمـاتـنـا 🛍️", callback_data='menu_services')],
        [
            InlineKeyboardButton("💸 تـجـمـيـع نـقـاط", callback_data='menu_collect'),
            InlineKeyboardButton("👤 حـسـابـي", callback_data='menu_account')
        ],
        [InlineKeyboardButton("🎁 الـهـديـة الـيـومـيـة", callback_data='action_daily_gift')],
        [InlineKeyboardButton("💳 شـحـن الـرصـيـد", callback_data='menu_charge_balance')]
    ]
    
    return text, InlineKeyboardMarkup(keyboard)

def get_services_menu() -> tuple[str, InlineKeyboardMarkup]:
    text = "اختر المنصة التي ترغب بخدماتها 📱"
    keyboard = [
        [
            InlineKeyboardButton("تـيـلـغـرام 🔹", callback_data='service_telegram'),
            InlineKeyboardButton("إنـسـتـغـرام 🔸", callback_data='service_instagram')
        ],
        [InlineKeyboardButton("تـيـك تـوك ▪️", callback_data='service_tiktok')],
        [InlineKeyboardButton("🔙 عــودة", callback_data='back_to_main')]
    ]
    return text, InlineKeyboardMarkup(keyboard)

# --- 6. دوال معالجة الأوامر والضغطات ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} ({user.id}) بدأ/عاد إلى البوت.")
    
    is_new_user = 'balance' not in context.user_data
    
    text, keyboard = get_main_menu(context)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    
    if is_new_user:
        logger.info(f"مستخدم جديد! {user.first_name} ({user.id}). إرسال إشعار...")
        notification_text = (
            "<b>🎉 مستخدم جديد انضم إلى البوت!</b>\n\n"
            f"<b>الاسم:</b> {user.full_name}\n"
            f"<b>المعرف:</b> @{user.username if user.username else 'لا يوجد'}\n"
            f"<b>الأيدي:</b> <code>{user.id}</code>\n"
            f"<b>رابط مباشر:</b> <a href='tg://user?id={user.id}'>اضغط هنا</a>"
        )
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
    
    # الأزرار التي لم تفعّل بعد
    elif action == 'menu_collect':
        await query.answer(text="قسم تجميع النقاط - سيتم تفعيله قريباً!", show_alert=True)
    elif action == 'menu_account':
        await query.answer(text="قسم الحساب - سيتم تفعيله قريباً!", show_alert=True)
    elif action == 'menu_charge_balance':
        # رسالة مؤقتة لزر شحن الرصيد
        await query.answer(text="طرق شحن الرصيد - سيتم إضافتها قريباً!", show_alert=True)
    elif action.startswith('service_'):
        service_name = action.split('_')[1].capitalize()
        await query.answer(text=f"خدمات {service_name} - سيتم تفعيلها قريباً!", show_alert=True)

async def handle_daily_gift(query, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    last_gift_time = user_data.get('last_gift_time')
    
    if last_gift_time and (datetime.now() - last_gift_time) < timedelta(hours=24):
        remaining_time = (last_gift_time + timedelta(hours=24)) - datetime.now()
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await query.answer(text=f"⏳ عذراً، يمكنك استلام هديتك مرة كل 24 ساعة. تبقى: {hours} س و {minutes} د.", show_alert=True)
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
        logger.critical("خطأ فادح: أحد التوكنات أو ايدي الأدمن غير موجود.")
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
