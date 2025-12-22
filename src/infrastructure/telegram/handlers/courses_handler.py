"""
Courses command handler with beautiful display.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from domain.entities import Language, Course, CourseStatus
from domain.value_objects import format_datetime_syria
from application.use_cases import GetCoursesUseCase, GetCourseByIdUseCase
from infrastructure.telegram.localization_service import t
from infrastructure.telegram.handlers.base import log_handler, get_user_language


COURSE_CALLBACK_PREFIX = "course_"


def format_course_card(course: Course, lang: Language) -> str:
    """Format a course as a beautiful card."""
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


def get_courses_message(lang: Language) -> str:
    """Get courses list header message."""
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


@log_handler("courses")
async def courses_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_courses_use_case: GetCoursesUseCase,
) -> None:
    """Handle /courses command - list available courses."""
    lang = get_user_language(context)
    
    courses = await get_courses_use_case.execute(available_only=True)
    
    if not courses:
        no_courses = "📭 لا توجد دورات متاحة حالياً" if lang == Language.ARABIC else "📭 No courses available at the moment"
        await update.message.reply_text(no_courses)
        return
    
    # Build course list with buttons
    keyboard = []
    for course in courses:
        status_emoji = "🟢" if course.status == CourseStatus.PUBLISHED else "🟡"
        keyboard.append([
            InlineKeyboardButton(
                f"{status_emoji} {course.name}",
                callback_data=f"{COURSE_CALLBACK_PREFIX}{course.id}"
            )
        ])
    
    # Add back button
    back_text = "🔙 العودة" if lang == Language.ARABIC else "🔙 Back"
    keyboard.append([
        InlineKeyboardButton(back_text, callback_data=f"{COURSE_CALLBACK_PREFIX}back")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = get_courses_message(lang)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def course_detail_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_course_use_case: GetCourseByIdUseCase,
) -> None:
    """Handle course detail callback."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    data = query.data.replace(COURSE_CALLBACK_PREFIX, "")
    
    if data == "back":
        back_msg = "استخدم /start للقائمة الرئيسية" if lang == Language.ARABIC else "Use /start for main menu"
        await query.edit_message_text(back_msg)
        return
    
    course = await get_course_use_case.execute(data)
    
    if course is None:
        error = "❌ خطأ في استرجاع الدورة" if lang == Language.ARABIC else "❌ Error retrieving course"
        await query.edit_message_text(error)
        return
    
    message = format_course_card(course, lang)
    
    # Add register and back buttons
    register_text = "📝 سجل الآن" if lang == Language.ARABIC else "📝 Register Now"
    back_text = "🔙 العودة" if lang == Language.ARABIC else "🔙 Back"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(register_text, callback_data=f"reg_{course.id}")],
        [InlineKeyboardButton(back_text, callback_data=f"{COURSE_CALLBACK_PREFIX}back")],
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')


def get_courses_handler(get_courses_use_case: GetCoursesUseCase) -> CommandHandler:
    """Get the courses command handler with injected use case."""
    async def handler_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await courses_handler(update, context, get_courses_use_case)
    
    return CommandHandler("courses", handler_wrapper)


def get_course_detail_callback_handler(
    get_course_use_case: GetCourseByIdUseCase
) -> CallbackQueryHandler:
    """Get the course detail callback handler."""
    async def callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await course_detail_callback(update, context, get_course_use_case)
    
    return CallbackQueryHandler(callback_wrapper, pattern=f"^{COURSE_CALLBACK_PREFIX}")
