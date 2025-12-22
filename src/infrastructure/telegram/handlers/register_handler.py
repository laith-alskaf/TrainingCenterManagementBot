"""
Registration command handler with conversation flow.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
)

from  domain.entities import Language
from  application.use_cases import (
    GetCoursesUseCase, RegisterStudentUseCase, RegistrationResult,
)
from  infrastructure.telegram.localization_service import t
from  infrastructure.telegram.handlers.base import log_handler, get_user_language


# Conversation states
SELECT_COURSE, ENTER_NAME, ENTER_PHONE, ENTER_EMAIL = range(4)

# Callback prefix
REG_CALLBACK_PREFIX = "reg_"


@log_handler("register")
async def register_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_courses_use_case: GetCoursesUseCase,
) -> int:
    """Start registration conversation."""
    lang = get_user_language(context)
    
    courses = await get_courses_use_case.execute(available_only=True)
    
    if not courses:
        await update.message.reply_text(t('courses.no_courses', lang))
        return ConversationHandler.END
    
    # Build course selection keyboard
    keyboard = []
    for course in courses:
        keyboard.append([
            InlineKeyboardButton(
                f"📚 {course.name}",
                callback_data=f"{REG_CALLBACK_PREFIX}{course.id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(t('buttons.cancel', lang), callback_data=f"{REG_CALLBACK_PREFIX}cancel")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{t('registration.title', lang)}\n\n{t('registration.select_course', lang)}",
        reply_markup=reply_markup,
    )
    
    return SELECT_COURSE


async def select_course_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle course selection."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    data = query.data.replace(REG_CALLBACK_PREFIX, "")
    
    if data == "cancel":
        await query.edit_message_text(t('errors.cancelled', lang))
        return ConversationHandler.END
    
    # Store selected course
    context.user_data['reg_course_id'] = data
    
    await query.edit_message_text(t('registration.enter_name', lang))
    
    return ENTER_NAME


async def enter_name_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle name input."""
    lang = get_user_language(context)
    name = update.message.text.strip()
    
    if not name or len(name) < 2:
        await update.message.reply_text(t('errors.invalid_input', lang))
        return ENTER_NAME
    
    context.user_data['reg_name'] = name
    
    await update.message.reply_text(t('registration.enter_phone', lang))
    
    return ENTER_PHONE


async def enter_phone_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Handle phone input."""
    lang = get_user_language(context)
    phone = update.message.text.strip()
    
    if phone.lower() == '/skip':
        phone = None
    
    context.user_data['reg_phone'] = phone
    
    await update.message.reply_text(t('registration.enter_email', lang))
    
    return ENTER_EMAIL


async def enter_email_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    register_use_case: RegisterStudentUseCase,
) -> int:
    """Handle email input and complete registration."""
    lang = get_user_language(context)
    email = update.message.text.strip()
    
    if email.lower() == '/skip':
        email = None
    
    # Perform registration
    user_id = update.effective_user.id
    result = await register_use_case.execute(
        telegram_id=user_id,
        name=context.user_data.get('reg_name', ''),
        course_id=context.user_data.get('reg_course_id', ''),
        phone=context.user_data.get('reg_phone'),
        email=email,
    )
    
    # Clean up context
    for key in ['reg_course_id', 'reg_name', 'reg_phone']:
        context.user_data.pop(key, None)
    
    if result.success:
        await update.message.reply_text(t('registration.success', lang))
    else:
        error_map = {
            "Already registered for this course": 'registration.already_registered',
            "Course is full": 'registration.course_full',
            "Course is not available for registration": 'registration.course_not_available',
        }
        error_key = error_map.get(result.error, 'registration.error')
        await update.message.reply_text(t(error_key, lang))
    
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation cancellation."""
    lang = get_user_language(context)
    await update.message.reply_text(t('errors.cancelled', lang))
    return ConversationHandler.END


def get_register_conversation_handler(
    get_courses_use_case: GetCoursesUseCase,
    register_use_case: RegisterStudentUseCase,
) -> ConversationHandler:
    """Get the registration conversation handler with injected use cases."""
    
    async def start_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await register_handler(update, context, get_courses_use_case)
    
    async def email_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await enter_email_handler(update, context, register_use_case)
    
    return ConversationHandler(
        entry_points=[CommandHandler("register", start_wrapper)],
        states={
            SELECT_COURSE: [
                CallbackQueryHandler(select_course_callback, pattern=f"^{REG_CALLBACK_PREFIX}")
            ],
            ENTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name_handler)
            ],
            ENTER_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone_handler)
            ],
            ENTER_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, email_wrapper)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        allow_reentry=True,
    )
