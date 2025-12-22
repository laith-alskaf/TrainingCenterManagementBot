"""
Admin handlers for posting, broadcasting, and file uploads.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters,
)

from  domain.entities import Language, Platform, ScheduledPost
from  domain.value_objects import now_syria
from  application.use_cases import (
    PublishPostUseCase, BroadcastMessageUseCase, UploadFileUseCase,
)
from  infrastructure.telegram.localization_service import t
from  infrastructure.telegram.handlers.base import (
    admin_required, log_handler, get_user_language, send_error_to_admin,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Post Handler
# ============================================================================

POST_CONTENT, POST_PLATFORM, POST_IMAGE = range(3)
POST_CALLBACK_PREFIX = "post_"


@admin_required
@log_handler("post")
async def post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start post creation conversation."""
    lang = get_user_language(context)
    
    await update.message.reply_text(t('admin.post.enter_content', lang))
    return POST_CONTENT


async def post_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle post content input."""
    lang = get_user_language(context)
    content = update.message.text.strip()
    
    context.user_data['post_content'] = content
    
    # Show platform selection
    keyboard = [
        [
            InlineKeyboardButton(
                t('buttons.facebook', lang),
                callback_data=f"{POST_CALLBACK_PREFIX}facebook"
            ),
        ],
        [
            InlineKeyboardButton(
                t('buttons.instagram', lang),
                callback_data=f"{POST_CALLBACK_PREFIX}instagram"
            ),
        ],
        [
            InlineKeyboardButton(
                t('buttons.both', lang),
                callback_data=f"{POST_CALLBACK_PREFIX}both"
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        t('admin.post.select_platform', lang),
        reply_markup=reply_markup,
    )
    
    return POST_PLATFORM


async def post_platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle platform selection."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    platform = query.data.replace(POST_CALLBACK_PREFIX, "")
    context.user_data['post_platform'] = platform
    
    await query.edit_message_text(t('admin.post.enter_image', lang))
    
    return POST_IMAGE


async def post_image_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    publish_use_case: PublishPostUseCase,
) -> int:
    """Handle image input and publish post."""
    lang = get_user_language(context)
    
    image_url = None
    
    # Check if it's a skip command
    if update.message.text and update.message.text.lower() == '/skip':
        pass
    elif update.message.text:
        # Text = image URL
        image_url = update.message.text.strip()
    elif update.message.photo:
        # Photo uploaded - get largest size
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_url = file.file_path
    
    content = context.user_data.get('post_content', '')
    platform_str = context.user_data.get('post_platform', 'facebook')
    
    # Clean up context
    context.user_data.pop('post_content', None)
    context.user_data.pop('post_platform', None)
    
    # Check Instagram requirement
    try:
        platform = Platform(platform_str)
    except ValueError:
        platform = Platform.FACEBOOK
    
    if platform in (Platform.INSTAGRAM, Platform.BOTH) and not image_url:
        await update.message.reply_text(t('admin.post.instagram_requires_image', lang))
        if platform == Platform.INSTAGRAM:
            return ConversationHandler.END
        # If BOTH, continue with Facebook only
        platform = Platform.FACEBOOK
    
    # Publish
    await update.message.reply_text(t('admin.post.publishing', lang))
    
    post = ScheduledPost.create(
        content=content,
        scheduled_datetime=now_syria(),
        platform=platform,
        image_url=image_url,
    )
    
    result = await publish_use_case.execute(post)
    
    if result.success:
        await update.message.reply_text(t('admin.post.success', lang))
    elif result.facebook_result and result.facebook_result.success:
        await update.message.reply_text(t('admin.post.partial_success', lang))
    else:
        error_msg = result.error or "Unknown error"
        await update.message.reply_text(f"{t('admin.post.failed', lang)}\n{error_msg}")
    
    return ConversationHandler.END


async def post_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel post creation."""
    lang = get_user_language(context)
    context.user_data.pop('post_content', None)
    context.user_data.pop('post_platform', None)
    await update.message.reply_text(t('errors.cancelled', lang))
    return ConversationHandler.END


# ============================================================================
# Broadcast Handler
# ============================================================================

BROADCAST_MESSAGE = 0


@admin_required
@log_handler("broadcast")
async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast conversation."""
    lang = get_user_language(context)
    await update.message.reply_text(t('admin.broadcast.enter_message', lang))
    return BROADCAST_MESSAGE


async def broadcast_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    broadcast_use_case: BroadcastMessageUseCase,
) -> int:
    """Handle broadcast message and send."""
    lang = get_user_language(context)
    message = update.message.text.strip()
    
    await update.message.reply_text(t('admin.broadcast.sending', lang))
    
    # Set up the send callback
    async def send_message(chat_id: int, text: str):
        await context.bot.send_message(chat_id=chat_id, text=text)
    
    broadcast_use_case.set_send_callback(send_message)
    
    result = await broadcast_use_case.execute(message)
    
    if result.total_users == 0:
        await update.message.reply_text(t('admin.broadcast.no_users', lang))
    else:
        await update.message.reply_text(
            t('admin.broadcast.success', lang,
              successful=result.successful, total=result.total_users)
        )
    
    return ConversationHandler.END


async def broadcast_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel broadcast."""
    lang = get_user_language(context)
    await update.message.reply_text(t('errors.cancelled', lang))
    return ConversationHandler.END


# ============================================================================
# Upload Handler
# ============================================================================

UPLOAD_FILE = 0


@admin_required
@log_handler("upload")
async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start file upload conversation."""
    lang = get_user_language(context)
    await update.message.reply_text(t('admin.upload.send_file', lang))
    return UPLOAD_FILE


async def upload_file_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    upload_use_case: UploadFileUseCase,
) -> int:
    """Handle file upload."""
    lang = get_user_language(context)
    
    if not update.message.document:
        await update.message.reply_text(t('errors.invalid_input', lang))
        return UPLOAD_FILE
    
    await update.message.reply_text(t('admin.upload.uploading', lang))
    
    # Download file
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Upload to Google Drive
    result = await upload_use_case.execute(
        file_bytes=bytes(file_bytes),
        file_name=doc.file_name or "uploaded_file",
        mime_type=doc.mime_type or "application/octet-stream",
    )
    
    if result.success:
        await update.message.reply_text(
            t('admin.upload.success', lang, link=result.shareable_link)
        )
    else:
        error_msg = result.error or "Unknown error"
        await update.message.reply_text(
            t('admin.upload.failed', lang, error=error_msg)
        )
        # Notify admin of failure
        await send_error_to_admin(context, f"File upload failed: {error_msg}")
    
    return ConversationHandler.END


async def upload_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel upload."""
    lang = get_user_language(context)
    await update.message.reply_text(t('errors.cancelled', lang))
    return ConversationHandler.END


# ============================================================================
# Handler Builders
# ============================================================================

def get_post_conversation_handler(
    publish_use_case: PublishPostUseCase,
) -> ConversationHandler:
    """Get the post conversation handler."""
    
    async def image_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await post_image_handler(update, context, publish_use_case)
    
    return ConversationHandler(
        entry_points=[CommandHandler("post", post_handler)],
        states={
            POST_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, post_content_handler)
            ],
            POST_PLATFORM: [
                CallbackQueryHandler(post_platform_callback, pattern=f"^{POST_CALLBACK_PREFIX}")
            ],
            POST_IMAGE: [
                MessageHandler(
                    (filters.TEXT | filters.PHOTO) & ~filters.COMMAND,
                    image_wrapper
                ),
                CommandHandler("skip", image_wrapper),
            ],
        },
        fallbacks=[CommandHandler("cancel", post_cancel_handler)],
        allow_reentry=True,
    )


def get_broadcast_conversation_handler(
    broadcast_use_case: BroadcastMessageUseCase,
) -> ConversationHandler:
    """Get the broadcast conversation handler."""
    
    async def message_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await broadcast_message_handler(update, context, broadcast_use_case)
    
    return ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_handler)],
        states={
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, message_wrapper)
            ],
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel_handler)],
        allow_reentry=True,
    )


def get_upload_conversation_handler(
    upload_use_case: UploadFileUseCase,
) -> ConversationHandler:
    """Get the upload conversation handler."""
    
    async def file_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await upload_file_handler(update, context, upload_use_case)
    
    return ConversationHandler(
        entry_points=[CommandHandler("upload", upload_handler)],
        states={
            UPLOAD_FILE: [
                MessageHandler(filters.Document.ALL, file_wrapper)
            ],
        },
        fallbacks=[CommandHandler("cancel", upload_cancel_handler)],
        allow_reentry=True,
    )
