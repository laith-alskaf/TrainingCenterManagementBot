"""
Materials command handler.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from  domain.entities import Language
from  application.use_cases import GetMaterialsUseCase, GetStudentRegistrationsUseCase
from  infrastructure.telegram.localization_service import t
from  infrastructure.telegram.handlers.base import log_handler, get_user_language


MATERIALS_CALLBACK_PREFIX = "materials_"


@log_handler("materials")
async def materials_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_registrations_use_case: GetStudentRegistrationsUseCase,
) -> None:
    """Handle /materials command - show courses for material access."""
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    # Get user's registered courses
    registrations = await get_registrations_use_case.execute(user_id)
    
    if not registrations:
        await update.message.reply_text(t('materials.no_registrations', lang))
        return
    
    # Build course selection keyboard
    keyboard = []
    for reg, course in registrations:
        keyboard.append([
            InlineKeyboardButton(
                f"📁 {course.name}",
                callback_data=f"{MATERIALS_CALLBACK_PREFIX}{course.id}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{t('materials.title', lang)}\n\n{t('materials.select_course', lang)}",
        reply_markup=reply_markup,
    )


async def materials_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_materials_use_case: GetMaterialsUseCase,
) -> None:
    """Handle materials selection callback."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    course_id = query.data.replace(MATERIALS_CALLBACK_PREFIX, "")
    
    # Get materials from Google Drive
    materials = await get_materials_use_case.execute(course_id)
    
    if not materials:
        await query.edit_message_text(t('materials.no_materials', lang))
        return
    
    # Format materials list
    lines = [t('materials.title', lang), ""]
    for item in materials:
        name = item.get('name', 'Unknown')
        link = item.get('webViewLink', '')
        lines.append(f"📄 [{name}]({link})")
    
    await query.edit_message_text(
        "\n".join(lines),
        parse_mode='Markdown',
        disable_web_page_preview=True,
    )


def get_materials_handler(
    get_registrations_use_case: GetStudentRegistrationsUseCase,
) -> CommandHandler:
    """Get the materials command handler."""
    async def handler_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await materials_handler(update, context, get_registrations_use_case)
    
    return CommandHandler("materials", handler_wrapper)


def get_materials_callback_handler(
    get_materials_use_case: GetMaterialsUseCase,
) -> CallbackQueryHandler:
    """Get the materials callback handler."""
    async def callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await materials_callback(update, context, get_materials_use_case)
    
    return CallbackQueryHandler(callback_wrapper, pattern=f"^{MATERIALS_CALLBACK_PREFIX}")
