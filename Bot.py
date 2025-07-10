import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات وقراءة المعلومات الحساسة من متغيرات البيئة ---
# هذا هو الأسلوب الصحيح للاستضافة. لا تكتب المفاتيح هنا مباشرة.
# ستحتاج إلى ضبط هذه المتغيرات في لوحة تحكم الاستضافة الخاصة بك.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7885095446:AAHrqDP_AYb3Zk6Omj9eRCzZ-kVS_TlH998") # استبدل القيمة الافتراضية بالتوكن الجديد
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyApDdYoP_tFWKBcPRnSsMq3Arrfg0anpgw") # استبدل القيمة الافتراضية بمفتاح جوجل الجديد
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "6072979272")) # ايدي حسابك

# --- 2. إعداد تسجيل المعلومات (Logging) لمتابعة عمل البوت ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. إعداد واجهة برمجة تطبيقات Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
    logger.info("تم إعداد Gemini AI بنجاح.")
except Exception as e:
    logger.error(f"فشل في إعداد Gemini AI: {e}")
    gemini_model = None

# --- 4. تعريف دوال الأوامر والرسائل (Handlers) ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """إرسال رسالة ترحيب عند إرسال المستخدم /start."""
    user = update.effective_user
    # التحقق من هوية المستخدم قبل الرد
    if user.id != ALLOWED_USER_ID:
        logger.warning(f"تم حظر محاولة وصول من مستخدم غير مصرح له: {user.id} ({user.first_name})")
        return # لا تقم بأي رد فعل

    await update.message.reply_html(
        f"أهلاً بك يا {user.mention_html()}! 👋\n\nأنا بوت دردشة ذكاء اصطناعي. يمكنك إرسال أي سؤال لي وسأحاول الإجابة عليه.",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التعامل مع جميع الرسائل النصية من المستخدم المصرح له."""
    user_id = update.message.from_user.id
    
    # فلتر أمان: تجاهل أي رسالة ليست من المستخدم المسموح له
    if user_id != ALLOWED_USER_ID:
        logger.warning(f"تم تجاهل رسالة من مستخدم غير مصرح له: {user_id}")
        return

    message_text = update.message.text
    logger.info(f"رسالة مستلمة من المستخدم {user_id}: '{message_text}'")

    if not gemini_model:
        await update.message.reply_text("عذراً، خدمة الذكاء الاصطناعي غير متاحة حالياً.")
        return

    # إرسال رسالة "يفكر..." لإعطاء المستخدم إحساساً بالاستجابة
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    try:
        # إرسال النص إلى Gemini للحصول على رد
        response = gemini_model.generate_content(message_text)
        ai_response = response.text
    except Exception as e:
        logger.error(f"حدث خطأ أثناء الاتصال بـ Gemini API: {e}")
        ai_response = "عذراً، حدث خطأ أثناء معالجة طلبك. الرجاء المحاولة مرة أخرى."

    # إرسال رد الذكاء الاصطناعي للمستخدم
    await update.message.reply_text(ai_response)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل الأخطاء التي تسببها تحديثات Telegram."""
    logger.error("حدث استثناء أثناء التعامل مع تحديث:", exc_info=context.error)


# --- 5. الدالة الرئيسية لتشغيل البوت ---
def main() -> None:
    """تشغيل البوت."""
    logger.info("🚀 بدء تشغيل البوت...")

    # التحقق من وجود التوكن
    if not TELEGRAM_TOKEN:
        logger.critical("خطأ: لم يتم العثور على TELEGRAM_TOKEN. يرجى ضبطه كمتغير بيئة.")
        return
    if not GEMINI_API_KEY:
        logger.critical("خطأ: لم يتم العثور على GEMINI_API_KEY. يرجى ضبطه كمتغير بيئة.")
        return
        
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # تشغيل البوت حتى يتم إيقافه يدوياً (e.g., Ctrl-C)
    application.run_polling()
    logger.info("🛑 تم إيقاف البوت.")


if __name__ == "__main__":
    main()
