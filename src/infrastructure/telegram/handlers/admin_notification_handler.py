"""
Admin targeted notification handler.
Send notifications to specific students or course groups.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from domain.entities import Language, NotificationType
from application.use_cases import format_notification_message, get_notification_emoji
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, divider,
    get_back_and_home_keyboard, get_cancel_keyboard,
)
from config import config


# Callback prefix
NOTIF_PREFIX = "adnotif_"


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


def get_notification_type_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get notification type selection keyboard."""
    builder = KeyboardBuilder()
    
    types = [
        (NotificationType.INFO, "ℹ️", "معلومات" if lang == Language.ARABIC else "Info"),
        (NotificationType.REMINDER, "🔔", "تذكير" if lang == Language.ARABIC else "Reminder"),
        (NotificationType.WARNING, "⚠️", "تنبيه" if lang == Language.ARABIC else "Warning"),
        (NotificationType.URGENT, "🚨", "عاجل" if lang == Language.ARABIC else "Urgent"),
        (NotificationType.SUCCESS, "✅", "نجاح" if lang == Language.ARABIC else "Success"),
    ]
    
    for ntype, emoji, label in types:
        builder.add_button_row(f"{emoji} {label}", f"{NOTIF_PREFIX}type_{ntype.value}")
    
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{CallbackPrefix.ADMIN}panel"
    )
    
    return builder.build()


async def start_notification_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Start the notification sending flow."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    if lang == Language.ARABIC:
        message = f"""
📢 *إرسال إشعار موجه*
{divider()}

اختر نوع الإشعار:
"""
    else:
        message = f"""
📢 *Send Targeted Notification*
{divider()}

Select notification type:
"""
    
    keyboard = get_notification_type_keyboard(lang)
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_notification_type_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    notification_type: str,
    get_courses_use_case,
) -> None:
    """Handle notification type selection."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    # Store type and move to recipient selection
    context.user_data['notification_flow'] = {
        'type': NotificationType(notification_type),
        'step': 'select_recipients',
    }
    
    # Get courses for recipient selection
    courses = await get_courses_use_case.execute()
    context.user_data['available_courses_for_notif'] = {c.id: c for c in courses}
    
    type_emoji = get_notification_emoji(NotificationType(notification_type))
    
    if lang == Language.ARABIC:
        message = f"""
📢 *إرسال إشعار {type_emoji}*
{divider()}

اختر المستلمين:
"""
    else:
        message = f"""
📢 *Send {type_emoji} Notification*
{divider()}

Select recipients:
"""
    
    builder = KeyboardBuilder()
    
    # All students option
    builder.add_button_row(
        f"👥 " + ("جميع الطلاب" if lang == Language.ARABIC else "All Students"),
        f"{NOTIF_PREFIX}recipients_all"
    )
    
    # Per course options
    for course in courses:
        builder.add_button_row(
            f"📚 {course.name[:25]}",
            f"{NOTIF_PREFIX}recipients_course_{course.id}"
        )
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{NOTIF_PREFIX}start"
    )
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def handle_recipients_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipient_type: str,
) -> None:
    """Handle recipients selection."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    flow = context.user_data.get('notification_flow', {})
    
    if recipient_type == "all":
        flow['recipients'] = 'all'
        flow['recipients_label'] = "جميع الطلاب" if lang == Language.ARABIC else "All Students"
    elif recipient_type.startswith("course_"):
        course_id = recipient_type.replace("course_", "")
        courses = context.user_data.get('available_courses_for_notif', {})
        course = courses.get(course_id)
        if course:
            flow['recipients'] = course_id
            flow['recipients_label'] = course.name
        else:
            await query.edit_message_text("❌ خطأ")
            return
    
    flow['step'] = 'enter_content'
    context.user_data['notification_flow'] = flow
    
    type_emoji = get_notification_emoji(flow['type'])
    
    if lang == Language.ARABIC:
        message = f"""
📢 *إرسال إشعار*
{divider()}

{type_emoji} *النوع:* {flow['type'].value}
👥 *المستلمين:* {flow['recipients_label']}

{divider()}

✏️ اكتب محتوى الإشعار:
"""
    else:
        message = f"""
📢 *Send Notification*
{divider()}

{type_emoji} *Type:* {flow['type'].value}
👥 *Recipients:* {flow['recipients_label']}

{divider()}

✏️ Write the notification content:
"""
    
    keyboard = get_cancel_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_notification_content_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle notification content text input."""
    flow = context.user_data.get('notification_flow')
    if not flow or flow.get('step') != 'enter_content':
        return False
    
    lang = get_user_language(context)
    content = update.message.text.strip()
    
    if len(content) < 5:
        if lang == Language.ARABIC:
            await update.message.reply_text("❌ المحتوى قصير جداً")
        else:
            await update.message.reply_text("❌ Content is too short")
        return True
    
    flow['content'] = content
    flow['step'] = 'confirm'
    context.user_data['notification_flow'] = flow
    
    type_emoji = get_notification_emoji(flow['type'])
    
    # Show preview
    preview = format_notification_message(
        flow['type'],
        content,
        lang == Language.ARABIC,
    )
    
    if lang == Language.ARABIC:
        message = f"""
📢 *معاينة الإشعار*
{divider()}

👥 *المستلمين:* {flow['recipients_label']}

{divider()}

{preview}

{divider()}

هل تريد إرسال هذا الإشعار؟
"""
    else:
        message = f"""
📢 *Notification Preview*
{divider()}

👥 *Recipients:* {flow['recipients_label']}

{divider()}

{preview}

{divider()}

Do you want to send this notification?
"""
    
    builder = KeyboardBuilder()
    builder.add_button(
        f"✅ " + ("إرسال" if lang == Language.ARABIC else "Send"),
        f"{NOTIF_PREFIX}send"
    )
    builder.add_button(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{NOTIF_PREFIX}cancel"
    )
    builder.add_row()
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())
    return True


async def handle_send_notification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_recipients_use_case,
    bot,
) -> None:
    """Handle sending the notification."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    flow = context.user_data.get('notification_flow')
    
    if not flow or flow.get('step') != 'confirm':
        await query.edit_message_text("❌ خطأ")
        return
    
    # Clear flow
    context.user_data.pop('notification_flow', None)
    
    # Get recipients
    if flow['recipients'] == 'all':
        students = await get_recipients_use_case.execute(all_students=True)
    else:
        students = await get_recipients_use_case.execute(
            course_id=flow['recipients'],
            approved_only=True,
        )
    
    if not students:
        if lang == Language.ARABIC:
            message = "❌ لا يوجد طلاب لإرسال الإشعار لهم"
        else:
            message = "❌ No students to send notification to"
        keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
        await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # Format notification message
    notification_msg = format_notification_message(
        flow['type'],
        flow['content'],
        True,  # Arabic
    )
    
    # Send to all recipients
    sent_count = 0
    failed_count = 0
    
    for student in students:
        try:
            await bot.send_message(student.telegram_id, notification_msg, parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            failed_count += 1
    
    if lang == Language.ARABIC:
        message = f"""
{Emoji.SUCCESS} *تم إرسال الإشعار!*
{divider()}

✅ *أُرسل إلى:* {sent_count} طالب
"""
        if failed_count > 0:
            message += f"❌ *فشل:* {failed_count} طالب\n"
    else:
        message = f"""
{Emoji.SUCCESS} *Notification Sent!*
{divider()}

✅ *Sent to:* {sent_count} students
"""
        if failed_count > 0:
            message += f"❌ *Failed:* {failed_count} students\n"
    
    keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_notification_admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for notification admin callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(NOTIF_PREFIX):
        return False
    
    data = query.data[len(NOTIF_PREFIX):]
    
    if data == "start":
        await start_notification_flow(update, context)
        return True
    
    elif data.startswith("type_"):
        ntype = data.replace("type_", "")
        await handle_notification_type_selection(
            update, context, ntype, container.get_courses
        )
        return True
    
    elif data.startswith("recipients_"):
        recipient_type = data.replace("recipients_", "")
        await handle_recipients_selection(update, context, recipient_type)
        return True
    
    elif data == "send":
        await handle_send_notification(
            update, context,
            container.get_notification_recipients,
            context.bot,
        )
        return True
    
    elif data == "cancel":
        context.user_data.pop('notification_flow', None)
        lang = get_user_language(context)
        await query.answer("تم الإلغاء" if lang == Language.ARABIC else "Cancelled")
        from infrastructure.telegram.handlers.start_handler import show_admin_panel
        await show_admin_panel(update, context)
        return True
    
    return False
