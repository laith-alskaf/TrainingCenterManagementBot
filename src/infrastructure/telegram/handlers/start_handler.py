"""
Start command handler with fully button-based navigation.
All interactions are via inline buttons - no commands needed.
Includes admin-specific interface with detailed tutorials.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from domain.entities import Language, CourseStatus
from domain.value_objects import format_datetime_syria
from infrastructure.telegram.localization_service import t
from infrastructure.telegram.handlers.base import log_handler, get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, format_loading,
    divider, get_back_and_home_keyboard, get_home_keyboard,
)
from config import config


# Callback prefixes (imported from ui_components but also defined here for compatibility)
MENU_PREFIX = "menu_"
NAV_PREFIX = CallbackPrefix.NAV
ADMIN_PREFIX = CallbackPrefix.ADMIN


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)

def get_main_menu_keyboard(lang: Language, is_admin_user: bool = False) -> InlineKeyboardMarkup:
    """Create the main menu keyboard with beautiful buttons."""
    builder = KeyboardBuilder()
    
    # For admins: show only admin panel
    if is_admin_user:
        builder.add_button_row(
            f"{Emoji.ADMIN} " + ("لوحة الإدارة" if lang == Language.ARABIC else "Admin Panel"),
            f"{ADMIN_PREFIX}panel"
        )
        builder.add_button(
            f"{Emoji.LANGUAGE} " + ("اللغة" if lang == Language.ARABIC else "Language"),
            f"{NAV_PREFIX}language"
        )
        builder.add_button(
            f"{Emoji.HELP} " + ("مساعدة" if lang == Language.ARABIC else "Help"),
            f"{NAV_PREFIX}help"
        )
        builder.add_row()
        return builder.build()
    
    # For students: show student navigation
    builder.add_button_row(
        f"{Emoji.COURSES} " + ("الدورات المتاحة" if lang == Language.ARABIC else "Available Courses"),
        f"{NAV_PREFIX}courses"
    )
    builder.add_button_row(
        f"{Emoji.REGISTER} " + ("التسجيل في دورة" if lang == Language.ARABIC else "Register for Course"),
        f"{NAV_PREFIX}register"
    )
    builder.add_button_row(
        f"{Emoji.MATERIALS} " + ("مواد الدورة" if lang == Language.ARABIC else "Course Materials"),
        f"{NAV_PREFIX}materials"
    )
    
    # Language and Help in same row
    builder.add_button(
        f"{Emoji.LANGUAGE} " + ("اللغة" if lang == Language.ARABIC else "Language"),
        f"{NAV_PREFIX}language"
    )
    builder.add_button(
        f"{Emoji.HELP} " + ("مساعدة" if lang == Language.ARABIC else "Help"),
        f"{NAV_PREFIX}help"
    )
    builder.add_row()
    
    return builder.build()


def get_admin_panel_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Create admin panel keyboard."""
    builder = KeyboardBuilder()
    
    # Pending registrations
    builder.add_button_row(
        f"📝 " + ("طلبات التسجيل" if lang == Language.ARABIC else "Pending Registrations"),
        "regadm_list"
    )
    
    # Payment management - select course first
    builder.add_button_row(
        f"💰 " + ("إدارة المدفوعات" if lang == Language.ARABIC else "Payment Management"),
        f"{ADMIN_PREFIX}payments"
    )
    
    # Student management
    builder.add_button_row(
        f"👥 " + ("إدارة الطلاب" if lang == Language.ARABIC else "Student Management"),
        "stdview_menu"
    )
    
    # Course management
    builder.add_button_row(
        f"📚 " + ("إدارة الدورات" if lang == Language.ARABIC else "Course Management"),
        "cmgr_list"
    )
    
    # Targeted notification
    builder.add_button_row(
        f"📢 " + ("إرسال إشعار" if lang == Language.ARABIC else "Send Notification"),
        "adnotif_start"
    )
    
    # Create course button
    builder.add_button_row(
        f"{Emoji.CREATE} " + ("إنشاء دورة" if lang == Language.ARABIC else "Create Course"),
        f"{ADMIN_PREFIX}create_course"
    )
    
    # Publish post
    builder.add_button_row(
        f"{Emoji.POST} " + ("نشر منشور" if lang == Language.ARABIC else "Publish Post"),
        f"{ADMIN_PREFIX}post"
    )
    
    # Broadcast
    builder.add_button_row(
        f"{Emoji.BROADCAST} " + ("رسالة جماعية" if lang == Language.ARABIC else "Broadcast Message"),
        f"{ADMIN_PREFIX}broadcast"
    )
    
    # Upload file
    builder.add_button_row(
        f"{Emoji.UPLOAD} " + ("رفع ملف" if lang == Language.ARABIC else "Upload File"),
        f"{ADMIN_PREFIX}upload"
    )
    
    # Stats
    builder.add_button_row(
        f"{Emoji.STATS} " + ("إحصائيات" if lang == Language.ARABIC else "Statistics"),
        f"{ADMIN_PREFIX}stats"
    )
    
    # User guide
    builder.add_button_row(
        f"{Emoji.GUIDE} " + ("دليل الاستخدام" if lang == Language.ARABIC else "User Guide"),
        f"{ADMIN_PREFIX}guide"
    )
    
    # Home button
    builder.add_home_button(lang)
    
    return builder.build()



def get_back_button(lang: Language) -> InlineKeyboardMarkup:
    """Get a back to main menu button."""
    return get_home_keyboard(lang)


def get_admin_back_button(lang: Language) -> InlineKeyboardMarkup:
    """Get a back to admin panel button."""
    return get_back_and_home_keyboard(lang, f"{ADMIN_PREFIX}panel")


def get_welcome_message(lang: Language, is_admin_user: bool = False) -> str:
    """Create a beautiful welcome message."""
    admin_badge = ""
    if is_admin_user:
        admin_badge = "\n👑 " + ("*أنت مسؤول*" if lang == Language.ARABIC else "*You are an Admin*") + "\n"
    
    if lang == Language.ARABIC:
        return f"""
🎓 *مرحباً بك في منصة مركز التدريب!*
{admin_badge}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

نحن نقدم لك أفضل الدورات التدريبية في مجالات متعددة لتطوير مهاراتك المهنية والشخصية.

✨ *ما يمكنك فعله هنا:*

📚 استعراض الدورات المتاحة
📝 التسجيل في الدورات
📁 الوصول لمواد التعلم
🌍 تغيير اللغة

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر أحد الخيارات أدناه للبدء 👇
"""
    else:
        return f"""
🎓 *Welcome to the Training Center Platform!*
{admin_badge}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

We offer you the best training courses in multiple fields to develop your professional and personal skills.

✨ *What you can do here:*

📚 Browse available courses
📝 Register for courses
📁 Access learning materials
🌍 Change language

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose an option below to get started 👇
"""


def get_admin_panel_message(lang: Language) -> str:
    """Get admin panel message."""
    if lang == Language.ARABIC:
        return """
⚙️ *لوحة الإدارة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

مرحباً بك في لوحة الإدارة!
اختر أحد الخيارات أدناه:

📣 *نشر منشور* - نشر على السوشيال ميديا
📢 *رسالة جماعية* - إرسال رسالة لجميع الطلاب
📤 *رفع ملف* - رفع ملف إلى Google Drive
📊 *إحصائيات* - عرض إحصائيات المنصة
📖 *دليل الاستخدام* - شرح كيفية استخدام كل ميزة

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        return """
⚙️ *Admin Panel*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Welcome to the Admin Panel!
Choose an option below:

📣 *Publish Post* - Post to social media
📢 *Broadcast* - Send message to all students
📤 *Upload File* - Upload file to Google Drive
📊 *Statistics* - View platform statistics
📖 *User Guide* - Learn how to use each feature

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def get_admin_guide_message(lang: Language) -> str:
    """Get comprehensive admin guide message."""
    if lang == Language.ARABIC:
        return """
📖 *دليل استخدام لوحة الإدارة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📣 *نشر منشور:*
├ 1️⃣ اضغط على "نشر منشور"
├ 2️⃣ اكتب محتوى المنشور
├ 3️⃣ اختر المنصة (Facebook/Instagram/كلاهما)
├ 4️⃣ سيتم النشر تلقائياً
└ ⚠️ Instagram يتطلب صورة

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📢 *رسالة جماعية:*
├ 1️⃣ اضغط على "رسالة جماعية"
├ 2️⃣ اكتب الرسالة التي تريد إرسالها
└ 3️⃣ سيتم إرسالها لجميع الطلاب المسجلين

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📤 *رفع ملف:*
├ 1️⃣ اضغط على "رفع ملف"
├ 2️⃣ أرسل الملف مباشرة
├ 3️⃣ سيتم رفعه إلى Google Drive
└ 4️⃣ ستحصل على رابط مشاركة

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 *إحصائيات:*
└ عرض عدد الطلاب والدورات والتسجيلات

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *نصائح:*
• استخدم /start للعودة للقائمة الرئيسية
• جميع العمليات تتم عبر الأزرار
• الإحصائيات تتحدث تلقائياً
"""
    else:
        return """
📖 *Admin Panel User Guide*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📣 *Publish Post:*
├ 1️⃣ Click "Publish Post"
├ 2️⃣ Write your post content
├ 3️⃣ Select platform (Facebook/Instagram/Both)
├ 4️⃣ Post will be published automatically
└ ⚠️ Instagram requires an image

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📢 *Broadcast Message:*
├ 1️⃣ Click "Broadcast Message"
├ 2️⃣ Write the message you want to send
└ 3️⃣ It will be sent to all registered students

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📤 *Upload File:*
├ 1️⃣ Click "Upload File"
├ 2️⃣ Send the file directly
├ 3️⃣ It will be uploaded to Google Drive
└ 4️⃣ You'll get a shareable link

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 *Statistics:*
└ View students, courses & registrations count

━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *Tips:*
• Use /start to return to main menu
• All operations are button-based
• Statistics update automatically
"""


def get_post_tutorial_message(lang: Language) -> str:
    """Get detailed post tutorial."""
    if lang == Language.ARABIC:
        return """
📣 *نشر منشور جديد*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *كيفية النشر:*

1️⃣ اكتب محتوى المنشور في الرسالة التالية
   مثال: "مرحباً! تابعونا للمزيد من الدورات..."

2️⃣ اختر المنصة:
   • 📘 Facebook - للنشر على فيسبوك
   • 📸 Instagram - يتطلب صورة!
   • 📱 كلاهما - للنشر على المنصتين

📌 *ملاحظات مهمة:*
• Instagram يتطلب رابط صورة صالح
• المنشور سيُنشر فوراً
• ستصلك رسالة تأكيد

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✏️ *أرسل محتوى المنشور الآن:*
"""
    else:
        return """
📣 *Create New Post*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *How to Post:*

1️⃣ Write your post content in the next message
   Example: "Hello! Follow us for more courses..."

2️⃣ Select platform:
   • 📘 Facebook - post to Facebook
   • 📸 Instagram - requires an image!
   • 📱 Both - post to both platforms

📌 *Important Notes:*
• Instagram requires a valid image URL
• Post will be published immediately
• You'll receive a confirmation message

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✏️ *Send your post content now:*
"""


def get_broadcast_tutorial_message(lang: Language) -> str:
    """Get detailed broadcast tutorial."""
    if lang == Language.ARABIC:
        return """
📢 *رسالة جماعية*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *كيفية الإرسال:*

1️⃣ اكتب رسالتك في الرسالة التالية
   مثال: "تذكير: دورة Python تبدأ غداً!"

2️⃣ سيتم إرسالها لجميع الطلاب المسجلين

📌 *ملاحظات مهمة:*
• الرسالة ستصل لكل من فعّل الإشعارات
• ستحصل على تقرير بعدد المستلمين
• لا يمكن التراجع بعد الإرسال

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✏️ *أرسل رسالتك الآن:*
"""
    else:
        return """
📢 *Broadcast Message*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *How to Broadcast:*

1️⃣ Write your message in the next message
   Example: "Reminder: Python course starts tomorrow!"

2️⃣ It will be sent to all registered students

📌 *Important Notes:*
• Message will reach everyone with notifications on
• You'll get a report of recipients count
• Cannot be undone after sending

━━━━━━━━━━━━━━━━━━━━━━━━━━━

✏️ *Send your message now:*
"""


def get_upload_tutorial_message(lang: Language) -> str:
    """Get detailed upload tutorial."""
    if lang == Language.ARABIC:
        return """
📤 *رفع ملف*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *كيفية الرفع:*

1️⃣ أرسل الملف مباشرة كمستند
   (PDF, Word, Excel, صور, فيديو...)

2️⃣ انتظر حتى يتم الرفع

3️⃣ ستحصل على رابط مشاركة

📌 *ملاحظات مهمة:*
• سيتم الرفع إلى Google Drive
• الرابط قابل للمشاركة مع أي شخص
• الحد الأقصى للملف: 50 MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 *أرسل ملفك الآن:*
"""
    else:
        return """
📤 *Upload File*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *How to Upload:*

1️⃣ Send your file directly as a document
   (PDF, Word, Excel, images, video...)

2️⃣ Wait for the upload to complete

3️⃣ You'll get a shareable link

📌 *Important Notes:*
• File will be uploaded to Google Drive
• Link is shareable with anyone
• Maximum file size: 50 MB

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 *Send your file now:*
"""


def get_help_message(lang: Language) -> str:
    """Create a help message."""
    if lang == Language.ARABIC:
        return """
❓ *المساعدة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 *كيفية الاستخدام:*

• اضغط على الأزرار للتنقل
• 📚 لعرض الدورات المتاحة
• 📝 للتسجيل في دورة
• 📁 لعرض مواد دوراتك
• 🌍 لتغيير اللغة

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 *للتواصل معنا:*
في حال واجهتك أي مشكلة، تواصل مع الإدارة.
"""
    else:
        return """
❓ *Help*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 *How to use:*

• Press buttons to navigate
• 📚 View available courses
• 📝 Register for a course
• 📁 View your course materials
• 🌍 Change language

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 *Contact Us:*
If you encounter any issues, contact the administration.
"""


def get_language_selection_message(lang: Language) -> str:
    """Get language selection message."""
    if lang == Language.ARABIC:
        return """
🌍 *اختيار اللغة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر لغتك المفضلة:
"""
    else:
        return """
🌍 *Language Selection*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose your preferred language:
"""


def get_language_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Create language selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("🇸🇦 العربية", callback_data=f"{NAV_PREFIX}setlang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data=f"{NAV_PREFIX}setlang_en")],
        [InlineKeyboardButton(
            "🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
            callback_data=f"{NAV_PREFIX}main"
        )],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_no_courses_message(lang: Language) -> str:
    """Message when no courses available."""
    if lang == Language.ARABIC:
        return """
📭 *لا توجد دورات متاحة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

عذراً، لا توجد دورات متاحة حالياً.
يرجى التحقق لاحقاً.
"""
    else:
        return """
📭 *No Courses Available*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sorry, no courses are available at the moment.
Please check back later.
"""


def get_courses_header(lang: Language) -> str:
    """Get courses list header."""
    if lang == Language.ARABIC:
        return """
📚 *الدورات المتاحة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر دورة لعرض تفاصيلها:
"""
    else:
        return """
📚 *Available Courses*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select a course to view details:
"""


def format_course_detail(course, lang: Language) -> str:
    """Format course details beautifully."""
    if lang == Language.ARABIC:
        status_map = {
            CourseStatus.PUBLISHED: "🟢 متاحة للتسجيل",
            CourseStatus.ONGOING: "🟡 قيد التنفيذ",
            CourseStatus.COMPLETED: "⚫ مكتملة",
            CourseStatus.CANCELLED: "🔴 ملغاة",
        }
        return f"""
📚 *{course.name}*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *الوصف:*
{course.description}

👨‍🏫 *المدرب:* {course.instructor}
📅 *التاريخ:* {format_datetime_syria(course.start_date, False)} - {format_datetime_syria(course.end_date, False)}
💰 *السعر:* {course.price} $
🪑 *الحد الأقصى:* {course.max_students} طالب
📊 *الحالة:* {status_map.get(course.status, course.status.value)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    else:
        status_map = {
            CourseStatus.PUBLISHED: "🟢 Open for Registration",
            CourseStatus.ONGOING: "🟡 In Progress",
            CourseStatus.COMPLETED: "⚫ Completed",
            CourseStatus.CANCELLED: "🔴 Cancelled",
        }
        return f"""
📚 *{course.name}*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 *Description:*
{course.description}

👨‍🏫 *Instructor:* {course.instructor}
📅 *Dates:* {format_datetime_syria(course.start_date, False)} - {format_datetime_syria(course.end_date, False)}
💰 *Price:* ${course.price}
🪑 *Max Students:* {course.max_students}
📊 *Status:* {status_map.get(course.status, course.status.value)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


def get_no_registrations_message(lang: Language) -> str:
    """Message when user has no registrations."""
    if lang == Language.ARABIC:
        return """
📭 *لم تسجل في أي دورة بعد*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

يمكنك التسجيل في دورة من القائمة الرئيسية.
"""
    else:
        return """
📭 *You haven't registered for any course yet*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

You can register for a course from the main menu.
"""


def get_materials_header(lang: Language) -> str:
    """Get materials list header."""
    if lang == Language.ARABIC:
        return """
📁 *مواد الدورات*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر دورة لعرض موادها:
"""
    else:
        return """
📁 *Course Materials*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select a course to view its materials:
"""


@log_handler("start")
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with beautiful welcome message and menu."""
    lang = get_user_language(context)
    user_id = update.effective_user.id
    is_admin_user = is_admin(user_id)
    
    message = get_welcome_message(lang, is_admin_user)
    keyboard = get_main_menu_keyboard(lang, is_admin_user)
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def navigation_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_courses_use_case=None,
    get_course_by_id_use_case=None,
    get_registrations_use_case=None,
    get_materials_use_case=None,
    set_language_use_case=None,
    register_student_use_case=None,
) -> None:
    """Handle all navigation callbacks - fully button-based."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    is_admin_user = is_admin(user_id)
    action = query.data.replace(NAV_PREFIX, "")
    
    # === MAIN MENU ===
    if action == "main":
        message = get_welcome_message(lang, is_admin_user)
        keyboard = get_main_menu_keyboard(lang, is_admin_user)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # === HELP ===
    elif action == "help":
        message = get_help_message(lang)
        await query.edit_message_text(message, reply_markup=get_back_button(lang), parse_mode='Markdown')
    
    # === LANGUAGE SELECTION ===
    elif action == "language":
        message = get_language_selection_message(lang)
        keyboard = get_language_keyboard(lang)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    elif action.startswith("setlang_"):
        lang_code = action.replace("setlang_", "")
        try:
            new_lang = Language(lang_code)
        except ValueError:
            new_lang = Language.ARABIC
        
        # Update in database
        if set_language_use_case:
            await set_language_use_case.execute(user_id, new_lang)
        
        # Update context
        context.user_data['language'] = new_lang.value
        
        # Show success and return to main menu
        if new_lang == Language.ARABIC:
            success = "✅ تم تغيير اللغة إلى العربية بنجاح!"
        else:
            success = "✅ Language changed to English successfully!"
        
        keyboard = get_main_menu_keyboard(new_lang, is_admin_user)
        message = get_welcome_message(new_lang, is_admin_user)
        await query.edit_message_text(
            f"{success}\n{message}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
    # === COURSES LIST ===
    elif action == "courses":
        if get_courses_use_case:
            courses = await get_courses_use_case.execute(available_only=True)
            
            if not courses:
                message = get_no_courses_message(lang)
                await query.edit_message_text(message, reply_markup=get_back_button(lang), parse_mode='Markdown')
            else:
                message = get_courses_header(lang)
                keyboard = []
                for course in courses:
                    status_emoji = "🟢" if course.status == CourseStatus.PUBLISHED else "🟡"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{status_emoji} {course.name}",
                            callback_data=f"{NAV_PREFIX}course_{course.id}"
                        )
                    ])
                keyboard.append([
                    InlineKeyboardButton(
                        "🏠 " + ("القائمة الرئيسية" if lang == Language.ARABIC else "Main Menu"),
                        callback_data=f"{NAV_PREFIX}main"
                    )
                ])
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text("Error loading courses", reply_markup=get_back_button(lang))
    
    # === COURSE DETAIL ===
    elif action.startswith("course_"):
        course_id = action.replace("course_", "")
        if get_course_by_id_use_case:
            course = await get_course_by_id_use_case.execute(course_id)
            if course:
                message = format_course_detail(course, lang)
                register_text = "📝 " + ("سجل الآن" if lang == Language.ARABIC else "Register Now")
                back_text = "🔙 " + ("الدورات" if lang == Language.ARABIC else "Courses")
                main_text = "🏠 " + ("الرئيسية" if lang == Language.ARABIC else "Main")
                
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(register_text, callback_data=f"{NAV_PREFIX}enroll_{course_id}")],
                    [
                        InlineKeyboardButton(back_text, callback_data=f"{NAV_PREFIX}courses"),
                        InlineKeyboardButton(main_text, callback_data=f"{NAV_PREFIX}main"),
                    ],
                ])
                await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
            else:
                error = "❌ خطأ" if lang == Language.ARABIC else "❌ Error"
                await query.edit_message_text(error, reply_markup=get_back_button(lang))
    
    # === REGISTRATION ===
    elif action == "register":
        # Show courses to register for
        if get_courses_use_case:
            courses = await get_courses_use_case.execute(available_only=True)
            
            if not courses:
                message = get_no_courses_message(lang)
                await query.edit_message_text(message, reply_markup=get_back_button(lang), parse_mode='Markdown')
            else:
                if lang == Language.ARABIC:
                    message = """
📝 *التسجيل في دورة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر الدورة التي تريد التسجيل فيها:
"""
                else:
                    message = """
📝 *Course Registration*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select the course you want to register for:
"""
                keyboard = []
                for course in courses:
                    if course.status == CourseStatus.PUBLISHED:
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📚 {course.name}",
                                callback_data=f"{NAV_PREFIX}enroll_{course.id}"
                            )
                        ])
                keyboard.append([
                    InlineKeyboardButton(
                        "🏠 " + ("القائمة الرئيسية" if lang == Language.ARABIC else "Main Menu"),
                        callback_data=f"{NAV_PREFIX}main"
                    )
                ])
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
    
    # === ENROLL IN COURSE ===
    elif action.startswith("enroll_"):
        course_id = action.replace("enroll_", "")
        # Store course for registration flow
        context.user_data['enrolling_course_id'] = course_id
        
        if lang == Language.ARABIC:
            message = """
📝 *التسجيل في الدورة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

للتسجيل، يرجى إرسال اسمك الكامل في الرسالة التالية.

أو اضغط إلغاء للعودة.
"""
        else:
            message = """
📝 *Course Registration*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

To register, please send your full name in the next message.

Or press Cancel to go back.
"""
        cancel_text = "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cancel_text, callback_data=f"{NAV_PREFIX}main")]
        ])
        context.user_data['awaiting_name'] = True
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # === MATERIALS ===
    elif action == "materials":
        if get_registrations_use_case:
            registrations = await get_registrations_use_case.execute(user_id)
            
            if not registrations:
                message = get_no_registrations_message(lang)
                await query.edit_message_text(message, reply_markup=get_back_button(lang), parse_mode='Markdown')
            else:
                message = get_materials_header(lang)
                keyboard = []
                for reg, course in registrations:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📁 {course.name}",
                            callback_data=f"{NAV_PREFIX}mat_{course.id}"
                        )
                    ])
                keyboard.append([
                    InlineKeyboardButton(
                        "🏠 " + ("القائمة الرئيسية" if lang == Language.ARABIC else "Main Menu"),
                        callback_data=f"{NAV_PREFIX}main"
                    )
                ])
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        else:
            message = get_no_registrations_message(lang)
            await query.edit_message_text(message, reply_markup=get_back_button(lang), parse_mode='Markdown')
    
    # === VIEW MATERIALS FOR COURSE ===
    elif action.startswith("mat_"):
        course_id = action.replace("mat_", "")
        if get_materials_use_case:
            materials = await get_materials_use_case.execute(course_id)
            
            if not materials:
                if lang == Language.ARABIC:
                    message = "📭 لا توجد مواد متاحة لهذه الدورة حالياً"
                else:
                    message = "📭 No materials available for this course yet"
            else:
                if lang == Language.ARABIC:
                    lines = ["📁 *مواد الدورة*", "", "━━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]
                else:
                    lines = ["📁 *Course Materials*", "", "━━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]
                
                for item in materials:
                    name = item.get('name', 'Unknown')
                    link = item.get('webViewLink', '')
                    lines.append(f"📄 [{name}]({link})")
                
                message = "\n".join(lines)
            
            back_text = "🔙 " + ("المواد" if lang == Language.ARABIC else "Materials")
            main_text = "🏠 " + ("الرئيسية" if lang == Language.ARABIC else "Main")
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(back_text, callback_data=f"{NAV_PREFIX}materials"),
                    InlineKeyboardButton(main_text, callback_data=f"{NAV_PREFIX}main"),
                ]
            ])
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )


async def admin_callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    student_repo=None,
    course_repo=None,
    registration_repo=None,
) -> None:
    """Handle admin panel callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(context)
    
    # Security check
    if not is_admin(user_id):
        error = "⛔ غير مصرح" if lang == Language.ARABIC else "⛔ Unauthorized"
        await query.edit_message_text(error)
        return
    
    action = query.data.replace(ADMIN_PREFIX, "")
    
    # === ADMIN PANEL ===
    if action == "panel":
        message = get_admin_panel_message(lang)
        keyboard = get_admin_panel_keyboard(lang)
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # === ADMIN GUIDE ===
    elif action == "guide":
        message = get_admin_guide_message(lang)
        await query.edit_message_text(message, reply_markup=get_admin_back_button(lang), parse_mode='Markdown')
    
    # === STATISTICS ===
    elif action == "stats":
        # Get statistics
        students_count = 0
        courses_count = 0
        registrations_count = 0
        
        if student_repo:
            students = await student_repo.get_all()
            students_count = len(students)
        
        if course_repo:
            courses = await course_repo.get_all()
            courses_count = len(courses)
        
        if registration_repo:
            from infrastructure.database import MongoDB
            collection = MongoDB.get_collection("registrations")
            registrations_count = await collection.count_documents({})
        
        if lang == Language.ARABIC:
            message = f"""
📊 *إحصائيات المنصة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 *عدد الطلاب:* {students_count}
📚 *عدد الدورات:* {courses_count}
📝 *عدد التسجيلات:* {registrations_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            message = f"""
📊 *Platform Statistics*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 *Students:* {students_count}
📚 *Courses:* {courses_count}
📝 *Registrations:* {registrations_count}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.edit_message_text(message, reply_markup=get_admin_back_button(lang), parse_mode='Markdown')
    
    # === POST with Tutorial ===
    elif action == "post":
        message = get_post_tutorial_message(lang)
        cancel_text = "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cancel_text, callback_data=f"{ADMIN_PREFIX}panel")]
        ])
        context.user_data['awaiting_post_content'] = True
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # === BROADCAST with Tutorial ===
    elif action == "broadcast":
        message = get_broadcast_tutorial_message(lang)
        cancel_text = "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cancel_text, callback_data=f"{ADMIN_PREFIX}panel")]
        ])
        context.user_data['awaiting_broadcast'] = True
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # === UPLOAD with Tutorial ===
    elif action == "upload":
        message = get_upload_tutorial_message(lang)
        cancel_text = "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(cancel_text, callback_data=f"{ADMIN_PREFIX}panel")]
        ])
        context.user_data['awaiting_file'] = True
        await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


def get_start_handler() -> CommandHandler:
    """Get the start command handler."""
    return CommandHandler("start", start_handler)


def create_navigation_callback_handler(
    get_courses_use_case,
    get_course_by_id_use_case,
    get_registrations_use_case,
    get_materials_use_case,
    set_language_use_case,
    register_student_use_case,
) -> CallbackQueryHandler:
    """Create the navigation callback handler with all use cases."""
    
    async def callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await navigation_callback_handler(
            update,
            context,
            get_courses_use_case=get_courses_use_case,
            get_course_by_id_use_case=get_course_by_id_use_case,
            get_registrations_use_case=get_registrations_use_case,
            get_materials_use_case=get_materials_use_case,
            set_language_use_case=set_language_use_case,
            register_student_use_case=register_student_use_case,
        )
    
    return CallbackQueryHandler(callback_wrapper, pattern=f"^{NAV_PREFIX}")


def create_admin_callback_handler(
    student_repo,
    course_repo,
    registration_repo,
) -> CallbackQueryHandler:
    """Create the admin callback handler with repositories."""
    
    async def callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await admin_callback_handler(
            update,
            context,
            student_repo=student_repo,
            course_repo=course_repo,
            registration_repo=registration_repo,
        )
    
    return CallbackQueryHandler(callback_wrapper, pattern=f"^{ADMIN_PREFIX}")
