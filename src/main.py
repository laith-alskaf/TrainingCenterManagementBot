"""
Main entry point for the Training Center Management Platform.
Runs the Telegram bot and scheduler in the same process.
"""
import asyncio
import logging
import signal
import sys
from typing import Optional

from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters

from config import config
from presentation import create_container, shutdown_container, Container
from infrastructure.telegram.handlers import (
    get_start_handler,
    create_navigation_callback_handler,
    create_admin_callback_handler,
    get_user_language,
)
from infrastructure.telegram.handlers.admin_flow_handler import (
    handle_course_creation_text,
    confirm_course_creation,
    handle_upload_course_toggle,
    handle_upload_confirm_selection,
    handle_course_file_upload,
    COURSE_CREATE_PREFIX,
    UPLOAD_SELECT_PREFIX,
    COURSE_CREATION_STEPS,
    get_cancel_keyboard,
    get_upload_course_selection_message,
    get_upload_course_keyboard,
)
from infrastructure.telegram.handlers.admin_registration_handler import (
    handle_registration_admin_callback,
    REG_ADMIN_PREFIX,
)
from infrastructure.telegram.handlers.admin_payment_handler import (
    handle_payment_admin_callback,
    handle_payment_amount_input,
    show_course_students_for_payment,
    PAYMENT_PREFIX,
)
from infrastructure.telegram.handlers.admin_notification_handler import (
    handle_notification_admin_callback,
    handle_notification_content_input,
    NOTIF_PREFIX,
)
from infrastructure.telegram.handlers.student_registration_handler import (
    handle_registration_callback,
    handle_registration_text_input,
    start_registration_flow,
    REG_PREFIX,
)
from infrastructure.telegram.handlers.student_profile_handler import (
    handle_profile_callback,
    handle_profile_text_input,
    start_profile_flow,
    check_profile_complete,
    show_profile_required_message,
    PROFILE_PREFIX,
)
from infrastructure.telegram.handlers.admin_student_viewer_handler import (
    handle_student_viewer_callback,
    handle_search_input,
    STUDENT_VIEWER_PREFIX,
)
from infrastructure.telegram.handlers.admin_course_handler import (
    handle_course_manager_callback,
    handle_edit_input as handle_course_edit_input,
    COURSE_MGR_PREFIX,
)
from infrastructure.telegram.handlers.base import log_handler
from domain.entities import Language, Platform, ScheduledPost
from domain.value_objects import now_syria

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Global container reference for cleanup
_container: Optional[Container] = None


def setup_handlers(application: Application, container: Container) -> None:
    """
    Set up all Telegram bot handlers with injected dependencies.
    
    Args:
        application: Telegram Application instance
        container: Dependency injection container
    """
    from telegram.ext import CommandHandler
    from infrastructure.telegram.handlers.ui_components import KeyboardBuilder, divider
    
    # Custom start handler with profile check
    async def start_with_profile_check(update: Update, context):
        """Start handler that checks if student profile is complete."""
        lang = get_user_language(context)
        user_id = update.effective_user.id
        is_admin_user = config.telegram.is_admin(user_id)
        
        # Admins bypass profile check
        if is_admin_user:
            from infrastructure.telegram.handlers.start_handler import get_welcome_message, get_main_menu_keyboard
            message = get_welcome_message(lang, is_admin_user)
            keyboard = get_main_menu_keyboard(lang, is_admin_user)
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
            return
        
        # Check if student exists and has completed profile
        student = await container.student_repo.get_by_telegram_id(user_id)
        
        if not student or not student.profile_completed:
            # Show profile required message
            if lang == Language.ARABIC:
                message = f"""
🎓 *مرحباً بك في مركز التدريب!*
{divider()}

لاستخدام خدمات المركز، يرجى إكمال ملفك الشخصي أولاً.

📝 *المعلومات المطلوبة:*
• الاسم الثلاثي
• رقم الهاتف
• الجنس
• العمر
• مكان الإقامة
• المستوى الدراسي

انقر الزر أدناه للبدء:
"""
            else:
                message = f"""
🎓 *Welcome to Training Center!*
{divider()}

To use our services, please complete your profile first.

📝 *Required Information:*
• Full Name
• Phone Number
• Gender
• Age
• Residence
• Education Level

Click the button below to start:
"""
            
            builder = KeyboardBuilder()
            builder.add_button_row(
                f"📝 " + ("إكمال الملف الشخصي" if lang == Language.ARABIC else "Complete Profile"),
                f"{PROFILE_PREFIX}start"
            )
            builder.add_button_row(
                f"🌍 " + ("تغيير اللغة" if lang == Language.ARABIC else "Language"),
                "nav_language"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())
            return
        
        # Profile complete - show main menu
        from infrastructure.telegram.handlers.start_handler import get_welcome_message, get_main_menu_keyboard
        message = get_welcome_message(lang, is_admin_user)
        keyboard = get_main_menu_keyboard(lang, is_admin_user)
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # Start command with profile check
    application.add_handler(CommandHandler("start", start_with_profile_check))
    
    # Main navigation callback handler - handles all button navigation
    application.add_handler(create_navigation_callback_handler(
        get_courses_use_case=container.get_courses,
        get_course_by_id_use_case=container.get_course_by_id,
        get_registrations_use_case=container.get_registrations,
        get_materials_use_case=container.get_materials,
        set_language_use_case=container.set_language,
        register_student_use_case=container.register_student,
    ))
    
    # Admin callback handler (now includes create_course and upload handlers)
    async def enhanced_admin_callback(update: Update, context):
        """Enhanced admin callback handler with course creation and upload flows."""
        query = update.callback_query
        action = query.data
        
        # Course creation confirmation
        if action == f"{COURSE_CREATE_PREFIX}confirm":
            await confirm_course_creation(update, context, container.create_course)
            return
        
        # Upload course selection toggle
        if action.startswith(f"{UPLOAD_SELECT_PREFIX}toggle_"):
            await handle_upload_course_toggle(update, context, container.get_courses)
            return
        
        # Upload course selection confirm
        if action == f"{UPLOAD_SELECT_PREFIX}confirm":
            await handle_upload_confirm_selection(update, context)
            return
        
        # Handle admin_create_course action
        if action == "admin_create_course":
            await query.answer()
            lang = get_user_language(context)
            
            # Start course creation flow
            context.user_data['creating_course'] = True
            context.user_data['course_step'] = 'name'
            context.user_data['course_data'] = {}
            
            msg = COURSE_CREATION_STEPS['name']['ar' if lang == Language.ARABIC else 'en']
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
            return
        
        # Handle admin_upload (enhanced with course selection)
        if action == "admin_upload":
            await query.answer()
            lang = get_user_language(context)
            
            # Get courses for selection
            courses = await container.get_courses.execute(available_only=False)
            context.user_data['upload_selected_courses'] = set()
            
            message = get_upload_course_selection_message(lang)
            keyboard = get_upload_course_keyboard(courses, set(), lang)
            await query.edit_message_text(message, reply_markup=keyboard, parse_mode='Markdown')
            return
        
        # Handle admin_payments (course selection for payment management)
        if action == "admin_payments":
            await query.answer()
            lang = get_user_language(context)
            courses = await container.get_courses.execute(available_only=False)
            
            if not courses:
                msg = "❌ لا توجد دورات" if lang == Language.ARABIC else "❌ No courses"
                await query.edit_message_text(msg)
                return
            
            # Show course selection for payment management
            from infrastructure.telegram.handlers.ui_components import KeyboardBuilder
            builder = KeyboardBuilder()
            for course in courses:
                builder.add_button_row(f"📚 {course.name}", f"{PAYMENT_PREFIX}list_{course.id}")
            builder.add_button_row("🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"), "admin_panel")
            
            msg = "💰 *إدارة المدفوعات*\n\nاختر دورة:" if lang == Language.ARABIC else "💰 *Payment Management*\n\nSelect course:"
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=builder.build())
            return
        
        # Fall through to original admin handler
        from infrastructure.telegram.handlers.start_handler import admin_callback_handler
        await admin_callback_handler(
            update,
            context,
            student_repo=container.student_repo,
            course_repo=container.course_repo,
            registration_repo=container.registration_repo,
        )
    
    # Registration admin callback handler
    async def registration_admin_callback(update: Update, context):
        await handle_registration_admin_callback(update, context, container)
    
    # Payment admin callback handler
    async def payment_admin_callback(update: Update, context):
        await handle_payment_admin_callback(update, context, container)
    
    # Notification admin callback handler
    async def notification_admin_callback(update: Update, context):
        await handle_notification_admin_callback(update, context, container)
    
    # Student registration callback handler
    async def student_registration_callback(update: Update, context):
        await handle_registration_callback(update, context, container)
    
    # Student profile callback handler
    async def student_profile_callback(update: Update, context):
        await handle_profile_callback(update, context, container)
    
    # Admin student viewer callback handler
    async def admin_student_viewer_callback(update: Update, context):
        await handle_student_viewer_callback(update, context, container)
    
    # Course manager callback handler
    async def course_manager_callback(update: Update, context):
        await handle_course_manager_callback(update, context, container)
    
    application.add_handler(CallbackQueryHandler(enhanced_admin_callback, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(enhanced_admin_callback, pattern=f"^{COURSE_CREATE_PREFIX}"))
    application.add_handler(CallbackQueryHandler(enhanced_admin_callback, pattern=f"^{UPLOAD_SELECT_PREFIX}"))
    application.add_handler(CallbackQueryHandler(registration_admin_callback, pattern=f"^{REG_ADMIN_PREFIX}"))
    application.add_handler(CallbackQueryHandler(payment_admin_callback, pattern=f"^{PAYMENT_PREFIX}"))
    application.add_handler(CallbackQueryHandler(notification_admin_callback, pattern=f"^{NOTIF_PREFIX}"))
    application.add_handler(CallbackQueryHandler(student_registration_callback, pattern=f"^{REG_PREFIX}"))
    application.add_handler(CallbackQueryHandler(student_profile_callback, pattern=f"^{PROFILE_PREFIX}"))
    application.add_handler(CallbackQueryHandler(admin_student_viewer_callback, pattern=f"^{STUDENT_VIEWER_PREFIX}"))
    application.add_handler(CallbackQueryHandler(course_manager_callback, pattern=f"^{COURSE_MGR_PREFIX}"))
    
    # Text message handler for registration, course creation, and admin actions
    async def handle_text_input(update: Update, context):
        """Handle text input for registration, course creation and admin flows."""
        lang = get_user_language(context)
        user_id = update.effective_user.id
        
        # Student profile flow (with validation)
        if await handle_profile_text_input(update, context):
            return
        
        # Student registration flow (with phone validation)
        if await handle_registration_text_input(update, context):
            return
        
        # Admin student search
        if await handle_search_input(update, context, container):
            return
        
        # Payment amount input
        if await handle_payment_amount_input(update, context):
            return
        
        # Notification content input
        if await handle_notification_content_input(update, context):
            return
        
        # Course edit text input
        if await handle_course_edit_input(update, context, container):
            return
        
        # Course creation flow (priority)
        if context.user_data.get('creating_course'):
            handled = await handle_course_creation_text(update, context, container.create_course)
            if handled:
                return
        
        # Registration flow
        if context.user_data.get('awaiting_name'):
            name = update.message.text.strip()
            
            if len(name) < 2:
                error = "❌ الاسم قصير جداً" if lang == Language.ARABIC else "❌ Name too short"
                await update.message.reply_text(error)
                return
            
            course_id = context.user_data.get('enrolling_course_id')
            context.user_data['awaiting_name'] = False
            
            if course_id and container.register_student:
                result = await container.register_student.execute(
                    telegram_id=user_id,
                    name=name,
                    course_id=course_id,
                )
                
                # Clean up
                context.user_data.pop('enrolling_course_id', None)
                
                if result.success:
                    if lang == Language.ARABIC:
                        message = """
✅ *تم التسجيل بنجاح!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

تهانينا! تم تسجيلك في الدورة بنجاح.
سيتم التواصل معك قريباً.

اضغط /start للعودة للقائمة الرئيسية.
"""
                    else:
                        message = """
✅ *Registration Successful!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Congratulations! You have been registered successfully.
We will contact you soon.

Press /start to return to main menu.
"""
                else:
                    error_messages = {
                        "Already registered for this course": (
                            "❌ أنت مسجل بالفعل في هذه الدورة",
                            "❌ You are already registered for this course"
                        ),
                        "Course is full": (
                            "❌ الدورة ممتلئة",
                            "❌ Course is full"
                        ),
                        "Course is not available for registration": (
                            "❌ الدورة غير متاحة للتسجيل",
                            "❌ Course is not available for registration"
                        ),
                    }
                    
                    err_ar, err_en = error_messages.get(result.error, (
                        "❌ حدث خطأ أثناء التسجيل",
                        "❌ Error during registration"
                    ))
                    message = err_ar if lang == Language.ARABIC else err_en
                    message += "\n\nاضغط /start للعودة" if lang == Language.ARABIC else "\n\nPress /start to return"
                
                await update.message.reply_text(message, parse_mode='Markdown')
        
        # Admin: Broadcast flow
        elif context.user_data.get('awaiting_broadcast'):
            if not config.telegram.is_admin(user_id):
                return
            
            context.user_data['awaiting_broadcast'] = False
            message_text = update.message.text.strip()
            
            sending_msg = "📤 جاري الإرسال..." if lang == Language.ARABIC else "📤 Sending..."
            await update.message.reply_text(sending_msg)
            
            # Set up send callback
            async def send_message(chat_id: int, text: str):
                await application.bot.send_message(chat_id=chat_id, text=text)
            
            container.broadcast_message.set_send_callback(send_message)
            result = await container.broadcast_message.execute(message_text)
            
            if lang == Language.ARABIC:
                response = f"✅ تم الإرسال بنجاح!\n\nتم الإرسال إلى: {result.successful}/{result.total_users} مستخدم"
            else:
                response = f"✅ Sent successfully!\n\nSent to: {result.successful}/{result.total_users} users"
            
            response += "\n\nاضغط /start للعودة" if lang == Language.ARABIC else "\n\nPress /start to return"
            await update.message.reply_text(response)
        
        # Admin: Post content flow
        elif context.user_data.get('awaiting_post_content'):
            if not config.telegram.is_admin(user_id):
                return
            
            context.user_data['awaiting_post_content'] = False
            context.user_data['post_content'] = update.message.text.strip()
            
            # Ask for platform
            if lang == Language.ARABIC:
                message = """
📣 *اختر المنصة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر المنصة التي تريد النشر عليها:
"""
            else:
                message = """
📣 *Select Platform*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Choose the platform to publish on:
"""
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📘 Facebook", callback_data="postplat_facebook")],
                [InlineKeyboardButton("📸 Instagram", callback_data="postplat_instagram")],
                [InlineKeyboardButton("📱 " + ("كلاهما" if lang == Language.ARABIC else "Both"), callback_data="postplat_both")],
                [InlineKeyboardButton("❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"), callback_data="postplat_cancel")],
            ])
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
    
    # File handler for admin upload
    async def handle_file_input(update: Update, context):
        """Handle file upload for admin."""
        lang = get_user_language(context)
        user_id = update.effective_user.id
        
        # Course file upload (with course selection)
        if context.user_data.get('awaiting_course_file'):
            handled = await handle_course_file_upload(
                update, context,
                container.upload_to_courses,
                container.upload_file,
            )
            if handled:
                return
        
        # Course-specific file upload
        if context.user_data.get('file_upload'):
            if not config.telegram.is_admin(user_id):
                return
            
            upload_info = context.user_data.get('file_upload')
            course_id = upload_info.get('course_id')
            folder_id = upload_info.get('folder_id')
            
            context.user_data.pop('file_upload', None)
            
            if not update.message.document:
                error = "❌ يرجى إرسال ملف" if lang == Language.ARABIC else "❌ Please send a file"
                await update.message.reply_text(error)
                return
            
            uploading = "📤 جاري الرفع..." if lang == Language.ARABIC else "📤 Uploading..."
            await update.message.reply_text(uploading)
            
            try:
                doc = update.message.document
                file = await context.bot.get_file(doc.file_id)
                file_bytes = await file.download_as_bytearray()
                
                link = await container.drive_adapter.upload_file_bytes(
                    file_bytes=bytes(file_bytes),
                    file_name=doc.file_name or "uploaded_file",
                    mime_type=doc.mime_type or "application/octet-stream",
                    folder_id=folder_id,
                )
                
                if lang == Language.ARABIC:
                    message = f"✅ تم رفع الملف بنجاح!\n\n🔗 الرابط:\n{link}"
                else:
                    message = f"✅ File uploaded successfully!\n\n🔗 Link:\n{link}"
            except Exception as e:
                if lang == Language.ARABIC:
                    message = f"❌ فشل الرفع: {e}"
                else:
                    message = f"❌ Upload failed: {e}"
            
            from infrastructure.telegram.handlers.ui_components import KeyboardBuilder
            builder = KeyboardBuilder()
            builder.add_button_row(
                f"📁 " + ("الملفات" if lang == Language.ARABIC else "Files"),
                f"{COURSE_MGR_PREFIX}files_{course_id}"
            )
            
            await update.message.reply_text(message, reply_markup=builder.build(), disable_web_page_preview=True)
            return
        
        # General file upload
        if context.user_data.get('awaiting_file'):
            if not config.telegram.is_admin(user_id):
                return
            
            context.user_data['awaiting_file'] = False
            
            if not update.message.document:
                error = "❌ يرجى إرسال ملف" if lang == Language.ARABIC else "❌ Please send a file"
                await update.message.reply_text(error)
                return
            
            uploading = "📤 جاري الرفع..." if lang == Language.ARABIC else "📤 Uploading..."
            await update.message.reply_text(uploading)
            
            # Download and upload
            doc = update.message.document
            file = await context.bot.get_file(doc.file_id)
            file_bytes = await file.download_as_bytearray()
            
            result = await container.upload_file.execute(
                file_bytes=bytes(file_bytes),
                file_name=doc.file_name or "uploaded_file",
                mime_type=doc.mime_type or "application/octet-stream",
            )
            
            if result.success:
                if lang == Language.ARABIC:
                    message = f"✅ تم الرفع بنجاح!\n\n🔗 الرابط:\n{result.shareable_link}"
                else:
                    message = f"✅ Uploaded successfully!\n\n🔗 Link:\n{result.shareable_link}"
            else:
                if lang == Language.ARABIC:
                    message = f"❌ فشل الرفع: {result.error}"
                else:
                    message = f"❌ Upload failed: {result.error}"
            
            message += "\n\nاضغط /start للعودة" if lang == Language.ARABIC else "\n\nPress /start to return"
            await update.message.reply_text(message, disable_web_page_preview=True)
    
    # Post platform selection callback
    async def handle_post_platform(update: Update, context):
        """Handle post platform selection."""
        query = update.callback_query
        await query.answer()
        
        lang = get_user_language(context)
        user_id = update.effective_user.id
        
        if not config.telegram.is_admin(user_id):
            return
        
        action = query.data.replace("postplat_", "")
        
        if action == "cancel":
            context.user_data.pop('post_content', None)
            msg = "❌ تم الإلغاء" if lang == Language.ARABIC else "❌ Cancelled"
            await query.edit_message_text(msg + "\n\nاضغط /start للعودة" if lang == Language.ARABIC else msg + "\n\nPress /start to return")
            return
        
        content = context.user_data.get('post_content', '')
        context.user_data.pop('post_content', None)
        
        try:
            platform = Platform(action)
        except ValueError:
            platform = Platform.FACEBOOK
        
        # Check Instagram image requirement
        if platform in (Platform.INSTAGRAM, Platform.BOTH):
            if lang == Language.ARABIC:
                msg = "⚠️ Instagram يتطلب صورة. النشر على Facebook فقط..."
            else:
                msg = "⚠️ Instagram requires an image. Publishing to Facebook only..."
            await query.edit_message_text(msg)
            platform = Platform.FACEBOOK
        
        publishing = "📤 جاري النشر..." if lang == Language.ARABIC else "📤 Publishing..."
        await query.edit_message_text(publishing)
        
        post = ScheduledPost.create(
            content=content,
            scheduled_datetime=now_syria(),
            platform=platform,
        )
        
        result = await container.publish_post.execute(post)
        
        if result.success:
            if lang == Language.ARABIC:
                message = f"✅ تم النشر بنجاح على {platform.value}!"
            else:
                message = f"✅ Published successfully on {platform.value}!"
        else:
            if lang == Language.ARABIC:
                message = f"❌ فشل النشر: {result.error}"
            else:
                message = f"❌ Publishing failed: {result.error}"
        
        message += "\n\nاضغط /start للعودة" if lang == Language.ARABIC else "\n\nPress /start to return"
        await query.edit_message_text(message)
    
    application.add_handler(CallbackQueryHandler(handle_post_platform, pattern="^postplat_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file_input))
    
    logger.info("All handlers registered")


def setup_scheduler(application: Application, container: Container) -> None:
    """
    Set up the post scheduler with shared dependencies.
    """
    async def on_scheduler_error(error_message: str) -> None:
        try:
            admin_ids = config.telegram.admin_user_ids
            if admin_ids:
                await application.bot.send_message(
                    chat_id=admin_ids[0],
                    text=f"⚠️ Scheduler Error:\n\n{error_message}"
                )
        except Exception as e:
            logger.error(f"Failed to notify admin of scheduler error: {e}")
    
    async def on_post_success(post, result) -> None:
        try:
            admin_ids = config.telegram.admin_user_ids
            if admin_ids:
                platform = post.platform.value
                await application.bot.send_message(
                    chat_id=admin_ids[0],
                    text=f"📣 Post published successfully on {platform}!"
                )
        except Exception as e:
            logger.error(f"Failed to notify admin of post success: {e}")
    
    container.check_and_publish._on_success = on_post_success
    container.check_and_publish._on_error = on_scheduler_error
    container.scheduler.set_publish_callback(container.check_and_publish.execute)
    container.scheduler._on_error = on_scheduler_error
    container.scheduler.start()
    
    logger.info("Scheduler started")


async def main() -> None:
    """Main entry point."""
    global _container
    
    logger.info("=" * 50)
    logger.info("Training Center Management Platform")
    logger.info("=" * 50)
    logger.info(f"Timezone: {config.scheduler.timezone}")
    logger.info(f"Scheduler interval: {config.scheduler.check_interval_minutes} minutes")
    logger.info("=" * 50)
    
    if not config.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        sys.exit(1)
    
    if not config.mongodb.uri:
        logger.error("MONGODB_URI is not set")
        sys.exit(1)
    
    _container = await create_container()
    application = Application.builder().token(config.telegram.bot_token).build()
    
    setup_handlers(application, _container)
    setup_scheduler(application, _container)
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(shutdown())
    
    async def shutdown():
        global _container
        if _container:
            await shutdown_container(_container)
        await application.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Telegram bot...")
    
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot is running! Press Ctrl+C to stop.")
        
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("Application cancelled")
    except Exception as e:
        logger.error(f"Error running application: {e}")
        raise
    finally:
        logger.info("Cleaning up...")
        if _container:
            await shutdown_container(_container)
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
