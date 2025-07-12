import os
import logging
from pathlib import Path
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)

# --- 1. الإعدادات ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7885095446:AAHrqDP_AYb3Zk6Omj9eRCzZ-kVS_TlH998")

# --- 2. إعداد تسجيل المعلومات ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. دوال إنشاء القوائم (Menus) ---

def get_main_menu(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    """ينشئ نص ورسالة القائمة الرئيسية."""
    user_data = context.user_data
    balance = user_data.setdefault('balance', 0)
    user_id = context._user_id

    text = (
        "مرحباً بك في بوت كريك ✨\n\n"
        f"👈 رصيد حسابك: `{balance}` نقطة\n"
        f"👈 ايدي حسابك: `{user_id}`"
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
    """ينشئ نص ورسالة قائمة الخدمات."""
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

# --- 4. دوال معالجة الأوامر والضغطات ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يعالج الأمر /start ويعرض القائمة الرئيسية."""
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} ({user.id}) بدأ/عاد إلى البوت.")
    
    text, keyboard = get_main_menu(context)
    # استخدام `reply_text` للرسالة الجديدة و `edit_message_text` للتعديلات
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يعالج جميع ضغطات الأزرار الشفافة."""
    query = update.callback_query
    await query.answer()  # مهم جداً

    action = query.data
    logger.info(f"المستخدم {query.from_user.id} ضغط على زر: {action}")

    # --- التنقل بين القوائم ---
    if action == 'menu_services':
        text, keyboard = get_services_menu()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')

    elif action == 'back_to_main':
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
    
    # --- إجراءات الأزرار ---
    elif action == 'action_daily_gift':
        await handle_daily_gift(query, context)

    # --- الأزرار التي لم تفعّل بعد ---
    elif action == 'menu_collect':
        await query.answer(text="قسم تجميع النقاط - سيتم إضافته قريباً!", show_alert=True)
    
    elif action == 'menu_account':
        await query.answer(text="قسم الحساب - سيتم إضافته قريباً!", show_alert=True)

    # --- أزرار الخدمات التي لم تفعّل بعد ---
    elif action.startswith('service_'):
        service_name = action.split('_')[1].capitalize()
        await query.answer(text=f"خدمات {service_name} - سيتم إضافتها قريباً!", show_alert=True)

async def handle_daily_gift(query, context: ContextTypes.DEFAULT_TYPE):
    """يعالج منطق الهدية اليومية."""
    user_data = context.user_data
    last_gift_time = user_data.get('last_gift_time')
    
    if last_gift_time and (datetime.now() - last_gift_time) < timedelta(hours=24):
        remaining_time = (last_gift_time + timedelta(hours=24)) - datetime.now()
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await query.answer(
            text=f"⏳ عذراً، لقد استلمت هديتك بالفعل. عد بعد {hours} ساعة و {minutes} دقيقة.",
            show_alert=True
        )
    else:
        user_data['balance'] = user_data.setdefault('balance', 0) + 40
        user_data['last_gift_time'] = datetime.now()
        logger.info(f"المستخدم {query.from_user.id} حصل على الهدية اليومية (40 نقطة).")
        
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        await query.answer(text="🎉 تهانينا! لقد حصلت على 40 نقطة كهدية يومية.", show_alert=True)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء."""
    logger.error("حدث استثناء:", exc_info=context.error)

# --- 5. الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    """تشغيل البوت وإعداده."""
    logger.info("🚀 بدء تشغيل البوت...")
    
    persistence = PicklePersistence(filepath=Path("bot_data.pickle"))
    
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    application.run_polling()
    logger.info("🛑 تم إيقاف البوت.")

if __name__ == "__main__":
    main()
