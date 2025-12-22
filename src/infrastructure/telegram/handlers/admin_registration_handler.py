"""
Admin registration approval handler.
Handles approval/rejection of pending registrations.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from domain.entities import Language, RegistrationStatus
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, divider,
    get_back_and_home_keyboard,
)
from config import config


# Callback prefixes
REG_ADMIN_PREFIX = "regadm_"


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


def format_registration_card(reg_data: dict, lang: Language) -> str:
    """Format a registration card for display."""
    student = reg_data["student"]
    course = reg_data["course"]
    registration = reg_data["registration"]
    
    if lang == Language.ARABIC:
        return f"""
📋 *طلب تسجيل جديد*
{divider()}

👤 *الطالب:* {student.full_name}
📱 *الهاتف:* {student.phone_number}
📚 *الدورة:* {course.name}
💰 *السعر:* ${course.price}
📅 *تاريخ الطلب:* {registration.registered_at.strftime('%Y-%m-%d %H:%M')}

{divider()}
"""
    else:
        return f"""
📋 *New Registration Request*
{divider()}

👤 *Student:* {student.full_name}
📱 *Phone:* {student.phone_number}
📚 *Course:* {course.name}
💰 *Price:* ${course.price}
📅 *Request Date:* {registration.registered_at.strftime('%Y-%m-%d %H:%M')}

{divider()}
"""


def get_registration_actions_keyboard(registration_id: str, lang: Language) -> InlineKeyboardMarkup:
    """Get action buttons for a registration."""
    builder = KeyboardBuilder()
    
    builder.add_button(
        f"✅ " + ("قبول" if lang == Language.ARABIC else "Approve"),
        f"{REG_ADMIN_PREFIX}approve_{registration_id}"
    )
    builder.add_button(
        f"❌ " + ("رفض" if lang == Language.ARABIC else "Reject"),
        f"{REG_ADMIN_PREFIX}reject_{registration_id}"
    )
    builder.add_row()
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{REG_ADMIN_PREFIX}list"
    )
    
    return builder.build()


async def show_pending_registrations(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_pending_use_case,
) -> None:
    """Show list of pending registrations."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    # Get pending registrations
    pending = await get_pending_use_case.execute()
    
    if not pending:
        if lang == Language.ARABIC:
            message = f"""
{Emoji.SUCCESS} *لا توجد طلبات معلقة*
{divider()}

جميع طلبات التسجيل تمت معالجتها ✨
"""
        else:
            message = f"""
{Emoji.SUCCESS} *No Pending Requests*
{divider()}

All registration requests have been processed ✨
"""
        keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
        
        if query:
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return
    
    # Store pending list in context
    context.user_data['pending_registrations'] = pending
    
    # Show list
    if lang == Language.ARABIC:
        message = f"""
📝 *طلبات التسجيل المعلقة*
{divider()}

يوجد {len(pending)} طلب في انتظار المراجعة.
اختر طلباً لعرض التفاصيل:
"""
    else:
        message = f"""
📝 *Pending Registrations*
{divider()}

There are {len(pending)} requests waiting for review.
Select a request to view details:
"""
    
    builder = KeyboardBuilder()
    for i, reg_data in enumerate(pending):
        student = reg_data["student"]
        course = reg_data["course"]
        label = f"👤 {student.full_name[:15]} - {course.name[:15]}"
        builder.add_button_row(label, f"{REG_ADMIN_PREFIX}view_{i}")
    
    builder.add_button_row(
        f"🔙 " + ("لوحة الإدارة" if lang == Language.ARABIC else "Admin Panel"),
        f"{CallbackPrefix.ADMIN}panel"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def view_registration_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    index: int,
) -> None:
    """View details of a specific registration."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    pending = context.user_data.get('pending_registrations', [])
    if index >= len(pending):
        await query.edit_message_text("❌ خطأ: الطلب غير موجود")
        return
    
    reg_data = pending[index]
    registration = reg_data["registration"]
    
    message = format_registration_card(reg_data, lang)
    keyboard = get_registration_actions_keyboard(registration.id, lang)
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_approve_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    registration_id: str,
    approve_use_case,
    bot,
) -> None:
    """Handle registration approval."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    admin_id = update.effective_user.id
    
    result = await approve_use_case.execute(
        registration_id=registration_id,
        admin_telegram_id=admin_id,
    )
    
    if result.success:
        # Get student to notify
        pending = context.user_data.get('pending_registrations', [])
        student_telegram_id = None
        course_name = ""
        
        for reg_data in pending:
            if reg_data["registration"].id == registration_id:
                student_telegram_id = reg_data["student"].telegram_id
                course_name = reg_data["course"].name
                break
        
        if lang == Language.ARABIC:
            message = f"""
{Emoji.SUCCESS} *تم قبول الطلب بنجاح!*
{divider()}

سيتم إشعار الطالب.
"""
        else:
            message = f"""
{Emoji.SUCCESS} *Registration Approved!*
{divider()}

Student will be notified.
"""
        
        # Notify student
        if student_telegram_id:
            try:
                student_msg = f"""
✅ *تم قبول طلب تسجيلك!*
{divider()}

📚 *الدورة:* {course_name}

سيتم التواصل معك قريباً لإتمام عملية الدفع.
تواصل معنا لأي استفسار! 🎓
"""
                await bot.send_message(student_telegram_id, student_msg, parse_mode='Markdown')
            except Exception as e:
                message += f"\n⚠️ فشل إرسال الإشعار للطالب"
    else:
        message = format_error(result.error, lang == Language.ARABIC)
    
    keyboard = get_back_and_home_keyboard(lang, f"{REG_ADMIN_PREFIX}list")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_reject_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    registration_id: str,
    reject_use_case,
    bot,
) -> None:
    """Handle registration rejection."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    admin_id = update.effective_user.id
    
    result = await reject_use_case.execute(
        registration_id=registration_id,
        admin_telegram_id=admin_id,
        reason="Rejected by admin",
    )
    
    if result.success:
        # Get student to notify
        pending = context.user_data.get('pending_registrations', [])
        student_telegram_id = None
        course_name = ""
        
        for reg_data in pending:
            if reg_data["registration"].id == registration_id:
                student_telegram_id = reg_data["student"].telegram_id
                course_name = reg_data["course"].name
                break
        
        if lang == Language.ARABIC:
            message = f"""
{Emoji.WARNING} *تم رفض الطلب*
{divider()}

سيتم إشعار الطالب.
"""
        else:
            message = f"""
{Emoji.WARNING} *Registration Rejected*
{divider()}

Student will be notified.
"""
        
        # Notify student
        if student_telegram_id:
            try:
                student_msg = f"""
❌ *عذراً، لم يتم قبول طلب تسجيلك*
{divider()}

📚 *الدورة:* {course_name}

يمكنك التواصل معنا للاستفسار أو التقديم لدورات أخرى.
"""
                await bot.send_message(student_telegram_id, student_msg, parse_mode='Markdown')
            except:
                message += f"\n⚠️ فشل إرسال الإشعار للطالب"
    else:
        message = format_error(result.error, lang == Language.ARABIC)
    
    keyboard = get_back_and_home_keyboard(lang, f"{REG_ADMIN_PREFIX}list")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_registration_admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for registration admin callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(REG_ADMIN_PREFIX):
        return False
    
    data = query.data[len(REG_ADMIN_PREFIX):]
    
    if data == "list":
        await show_pending_registrations(
            update, context,
            container.get_pending_registrations,
        )
        return True
    
    elif data.startswith("view_"):
        index = int(data.replace("view_", ""))
        await view_registration_details(update, context, index)
        return True
    
    elif data.startswith("approve_"):
        reg_id = data.replace("approve_", "")
        await handle_approve_registration(
            update, context, reg_id,
            container.approve_registration,
            context.bot,
        )
        return True
    
    elif data.startswith("reject_"):
        reg_id = data.replace("reject_", "")
        await handle_reject_registration(
            update, context, reg_id,
            container.reject_registration,
            context.bot,
        )
        return True
    
    return False
