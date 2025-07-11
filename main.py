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

# --- 3. تعريف دوال الأوامر والاستجابات ---

def get_main_menu(context: ContextTypes.DEFAULT_TYPE) -> tuple[str, InlineKeyboardMarkup]:
    """
    ينشئ نص ورسالة القائمة الرئيسية بناءً على بيانات المستخدم.
    """
    user_data = context.user_data
    balance = user_data.setdefault('balance', 0)
    user_id = context._user_id

    # نص الرسالة
    text = (
        "مرحباً بك في بوت كريك ✨\n\n"
        f"👈 رصيد حسابك: `{balance}` نقطة\n"
        f"👈 ايدي حسابك: `{user_id}`"
    )
    
    # تصميم الأزرار
    keyboard = [
        [InlineKeyboardButton("الخدمات 🛒", callback_data='services_menu')],
        [
            InlineKeyboardButton("تجميع 💚", callback_data='collect_points'),
            InlineKeyboardButton("الحساب 🎗️", callback_data='account_menu')
        ],
        [InlineKeyboardButton("الهدية اليومية 🎁", callback_data='daily_gift')]
    ]
    
    return text, InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يعالج الأمر /start ويرسل القائمة الرئيسية.
    """
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} ({user.id}) بدأ/عاد إلى البوت.")
    
    text, keyboard = get_main_menu(context)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يعالج جميع ضغطات الأزرار الشفافة.
    """
    query = update.callback_query
    await query.answer()  # مهم جداً لإيقاف علامة التحميل

    # استخراج البيانات من الزر المضغوط
    action = query.data

    if action == 'collect_points':
        # زيادة الرصيد بـ 3 نقاط (مثل ما كان سابقاً)
        context.user_data['balance'] = context.user_data.setdefault('balance', 0) + 3
        
        # تحديث القائمة الرئيسية
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        await query.answer(text="✅ تم إضافة 3 نقاط بنجاح!", show_alert=False)

    elif action == 'daily_gift':
        user_data = context.user_data
        last_gift_time = user_data.get('last_gift_time')
        
        # التحقق إذا كان قد مر 24 ساعة على آخر هدية
        if last_gift_time and (datetime.now() - last_gift_time) < timedelta(hours=24):
            # لم يمر الوقت الكافي
            remaining_time = (last_gift_time + timedelta(hours=24)) - datetime.now()
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await query.answer(
                text=f"⏳ عذراً، لقد استلمت هديتك بالفعل. عد بعد {hours} ساعة و {minutes} دقيقة.",
                show_alert=True
            )
        else:
            # مر الوقت الكافي، يمكن إعطاء الهدية
            user_data['balance'] = user_data.setdefault('balance', 0) + 40
            user_data['last_gift_time'] = datetime.now()
            logger.info(f"المستخدم {query.from_user.id} حصل على الهدية اليومية (40 نقطة).")
            
            # تحديث القائمة الرئيسية
            text, keyboard = get_main_menu(context)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
            await query.answer(text="🎉 تهانينا! لقد حصلت على 40 نقطة كهدية يومية.", show_alert=True)
            
    elif action == 'account_menu':
        # هنا يمكن إضافة وظائف خاصة بالحساب مستقبلاً
        await query.answer(text="قائمة الحساب - سيتم إضافتها قريباً!", show_alert=True)

    elif action == 'services_menu':
        # هنا يمكن إضافة قائمة الخدمات مستقبلاً
        await query.answer(text="قائمة الخدمات - سيتم إضافتها قريباً!", show_alert=True)
        
    elif action == 'back_to_main':
        # زر للعودة للقائمة الرئيسية (سنحتاجه لاحقاً)
        text, keyboard = get_main_menu(context)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='MarkdownV2')
        
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء."""
    logger.error("حدث استثناء:", exc_info=context.error)

# --- 4. الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    """تشغيل البوت وإعداده."""
    logger.info("🚀 بدء تشغيل البوت...")
    
    # إعداد نظام حفظ البيانات
    persistence = PicklePersistence(filepath=Path("bot_data.pickle"))
    
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence)
        .build()
    )

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)

    # تشغيل البوت
    application.run_polling()
    logger.info("🛑 تم إيقاف البوت.")

if __name__ == "__main__":
    main()
