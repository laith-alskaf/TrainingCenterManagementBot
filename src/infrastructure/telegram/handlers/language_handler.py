"""
Language command handler with beautiful inline buttons.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
)

from domain.entities import Language
from application.use_cases import SetLanguageUseCase
from infrastructure.telegram.localization_service import t
from infrastructure.telegram.handlers.base import log_handler, get_user_language


# Callback data prefixes
LANG_CALLBACK_PREFIX = "lang_"


def get_language_keyboard() -> InlineKeyboardMarkup:
    """Create beautiful language selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data=f"{LANG_CALLBACK_PREFIX}ar"),
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data=f"{LANG_CALLBACK_PREFIX}en"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_message(lang: Language) -> str:
    """Get language selection message."""
    if lang == Language.ARABIC:
        return """
🌍 *اختيار اللغة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر لغتك المفضلة للتعامل مع البوت:

👇 *Select your preferred language:*
"""
    else:
        return """
🌍 *Language Selection*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose your preferred language:

👇 *اختر لغتك المفضلة:*
"""


@log_handler("language")
async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language command - show language selection."""
    lang = get_user_language(context)
    
    message = get_language_message(lang)
    keyboard = get_language_keyboard()
    
    await update.message.reply_text(
        message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def language_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    set_language_use_case: SetLanguageUseCase,
) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    
    # Extract language from callback data
    lang_code = query.data.replace(LANG_CALLBACK_PREFIX, "")
    
    try:
        new_lang = Language(lang_code)
    except ValueError:
        new_lang = Language.ARABIC
    
    # Update in database
    user_id = update.effective_user.id
    await set_language_use_case.execute(user_id, new_lang)
    
    # Update context
    context.user_data['language'] = new_lang.value
    
    # Confirm change with success message
    if new_lang == Language.ARABIC:
        success_message = """
✅ *تم تغيير اللغة بنجاح!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

تم تعيين اللغة العربية كلغة مفضلة.

استخدم /start للعودة للقائمة الرئيسية.
"""
    else:
        success_message = """
✅ *Language Changed Successfully!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

English has been set as your preferred language.

Use /start to return to the main menu.
"""
    
    await query.edit_message_text(success_message, parse_mode='Markdown')


def get_language_handler() -> CommandHandler:
    """Get the language command handler."""
    return CommandHandler("language", language_handler)


def get_language_callback_handler(set_language_use_case: SetLanguageUseCase) -> CallbackQueryHandler:
    """Get the language callback handler with injected use case."""
    async def callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await language_callback(update, context, set_language_use_case)
    
    return CallbackQueryHandler(callback_wrapper, pattern=f"^{LANG_CALLBACK_PREFIX}")
