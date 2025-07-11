import os
import logging
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PicklePersistence,
)

# --- 1. الإعدادات ---
# سنقرأ التوكن من متغيرات البيئة كما هو الحال في الاستضافات
# وضعنا التوكن القديم كقيمة افتراضية فقط للتوضيح، يجب عليك تغييره في الاستضافة
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7885095446:AAHrqDP_AYb3Zk6Omj9eRCzZ-kVS_TlH998")

# --- 2. إعداد تسجيل المعلومات لمتابعة عمل البوت ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. تعريف دوال الأوامر والاستجابات ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يتم استدعاء هذه الدالة عند إرسال المستخدم للأمر /start.
    ترسل رسالة ترحيب مع الرصيد الحالي وزر التجميع.
    """
    user = update.effective_user
    logger.info(f"المستخدم {user.first_name} ({user.id}) بدأ البوت.")
    
    # نحصل على رصيد المستخدم من البيانات المحفوظة. إذا لم يكن موجوداً، نبدأه بصفر.
    # context.user_data هو قاموس خاص بكل مستخدم ويتم حفظه تلقائياً.
    balance = context.user_data.setdefault('balance', 0)
    
    # نص الرسالة
    text = (
        "مرحباً بك في بوت خدمات سوشيال ميديا احترافي 💎\n\n"
        f"💰 **رصيدك الحالي:** {balance} نقطة"
    )
    
    # إنشاء الزر الشفاف (Inline Button)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 اجمع الرصيد (3+ نقاط)", callback_data='collect_points')]
    ])
    
    # إرسال الرسالة مع الزر
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    يتم استدعاء هذه الدالة عند الضغط على أي زر شفاف.
    """
    query = update.callback_query
    
    # يجب الإجابة على الـ callback query أولاً لإيقاف علامة التحميل عند المستخدم
    await query.answer()
    
    # التحقق من أن الزر المضغوط هو زر تجميع النقاط
    if query.data == 'collect_points':
        user_id = query.from_user.id
        
        # زيادة رصيد المستخدم بمقدار 3 نقاط
        current_balance = context.user_data.setdefault('balance', 0)
        new_balance = current_balance + 3
        context.user_data['balance'] = new_balance
        
        logger.info(f"المستخدم {user_id} جمع 3 نقاط. الرصيد الجديد: {new_balance}")
        
        # تحديث نص الرسالة بالرصيد الجديد
        new_text = (
            "مرحباً بك في بوت خدمات سوشيال ميديا احترافي 💎\n\n"
            f"💰 **رصيدك الحالي:** {new_balance} نقطة"
        )
        
        # إنشاء الزر مرة أخرى
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 اجمع الرصيد (3+ نقاط)", callback_data='collect_points')]
        ])
        
        try:
            # محاولة تعديل الرسالة الأصلية بالمعلومات الجديدة
            await query.edit_message_text(text=new_text, reply_markup=keyboard, parse_mode='Markdown')
            # إظهار إشعار مؤقت للمستخدم يؤكد العملية
            await query.answer(text=f"🎉 تم إضافة 3 نقاط! رصيدك الآن {new_balance}.", show_alert=False)
        except Exception as e:
            # إذا فشل التعديل (مثلاً الرسالة قديمة جداً)، نسجل الخطأ
            logger.error(f"فشل في تعديل الرسالة: {e}")
            # يمكن إرسال رسالة جديدة كبديل إذا أردنا
            # await context.bot.send_message(chat_id=query.message.chat_id, text=f"رصيدك الآن هو: {new_balance}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء التي تحدث."""
    logger.error("حدث استثناء أثناء التعامل مع تحديث:", exc_info=context.error)


# --- 4. الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    """تشغيل البوت وإعداده لحفظ البيانات."""
    logger.info("🚀 بدء تشغيل البوت...")

    # التحقق من وجود التوكن
    if not TELEGRAM_TOKEN:
        logger.critical("خطأ فادح: لم يتم العثور على TELEGRAM_TOKEN. يرجى إعداده.")
        return
        
    # إعداد نظام حفظ البيانات (Persistence)
    # سيتم إنشاء ملف "bot_data" لحفظ رصيد المستخدمين وكل المعلومات تلقائياً
    persistence = PicklePersistence(filepath=Path("bot_data.pickle"))
    
    # إنشاء التطبيق وربطه بالتوكن ونظام حفظ البيانات
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence)
        .build()
    )

    # إضافة معالجات الأوامر والضغط على الأزرار
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # إضافة معالج الأخطاء (مهم جداً)
    application.add_error_handler(error_handler)

    # تشغيل البوت في وضع الاستطلاع (polling)
    application.run_polling()
    logger.info("🛑 تم إيقاف البوت.")


if __name__ == "__main__":
    main()
