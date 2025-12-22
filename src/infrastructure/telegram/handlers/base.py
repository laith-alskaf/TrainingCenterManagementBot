"""
Base handler utilities and decorators for Telegram bot.
"""
import logging
from functools import wraps
from typing import Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from  config import config
from  domain.entities import Language
from  infrastructure.telegram.localization_service import t

logger = logging.getLogger(__name__)


def admin_required(func: Callable):
    """
    Decorator to restrict handler to admin users only.
    Uses the is_admin check from config.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not config.telegram.is_admin(user_id):
            # Get user language for error message
            lang = context.user_data.get('language', Language.ARABIC)
            await update.message.reply_text(t('admin.not_authorized', lang))
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def get_user_language(context: ContextTypes.DEFAULT_TYPE) -> Language:
    """Get the user's language preference from context."""
    lang_value = context.user_data.get('language', 'ar')
    try:
        return Language(lang_value)
    except ValueError:
        return Language.ARABIC


async def get_user_language_async(
    telegram_id: int,
    get_language_use_case,
    context: ContextTypes.DEFAULT_TYPE,
) -> Language:
    """
    Get user language from database or context.
    Updates context with the retrieved language.
    """
    # Check context first
    if 'language' in context.user_data:
        return Language(context.user_data['language'])
    
    # Get from database
    lang = await get_language_use_case.execute(telegram_id)
    context.user_data['language'] = lang.value
    return lang


def log_handler(handler_name: str):
    """Decorator to log handler calls."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id if update.effective_user else 'unknown'
            logger.info(f"Handler {handler_name} called by user {user_id}")
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in handler {handler_name}: {e}", exc_info=True)
                lang = get_user_language(context)
                try:
                    await update.message.reply_text(t('errors.general', lang))
                except Exception:
                    pass
                raise
        return wrapper
    return decorator


async def send_error_to_admin(
    context: ContextTypes.DEFAULT_TYPE,
    error_message: str,
) -> None:
    """Send an error notification to the primary admin."""
    admin_ids = config.telegram.admin_user_ids
    if not admin_ids:
        logger.warning("No admin IDs configured for error notifications")
        return
    
    primary_admin = admin_ids[0]
    try:
        await context.bot.send_message(
            chat_id=primary_admin,
            text=f"⚠️ System Error:\n\n{error_message}"
        )
        logger.info(f"Error notification sent to admin {primary_admin}")
    except Exception as e:
        logger.error(f"Failed to send error notification to admin: {e}")
