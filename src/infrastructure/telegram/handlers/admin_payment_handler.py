"""
Admin payment management handler.
Handles adding payments and viewing payment history.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from domain.entities import Language, PaymentMethod, PaymentStatus
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, divider,
    get_back_and_home_keyboard, get_cancel_keyboard,
)
from config import config


# Callback prefixes
PAYMENT_PREFIX = "pay_"


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


def format_payment_status_emoji(status: PaymentStatus) -> str:
    """Get emoji for payment status."""
    mapping = {
        PaymentStatus.UNPAID: "🔴",
        PaymentStatus.PARTIAL: "🟡",
        PaymentStatus.PAID: "🟢",
    }
    return mapping.get(status, "⚪")


def format_payment_status_label(status: PaymentStatus, lang: Language) -> str:
    """Get label for payment status."""
    if lang == Language.ARABIC:
        mapping = {
            PaymentStatus.UNPAID: "لم يدفع",
            PaymentStatus.PARTIAL: "دفع جزئي",
            PaymentStatus.PAID: "دفع كامل",
        }
    else:
        mapping = {
            PaymentStatus.UNPAID: "Unpaid",
            PaymentStatus.PARTIAL: "Partial",
            PaymentStatus.PAID: "Paid",
        }
    return mapping.get(status, "Unknown")


def format_student_payment_card(student_data: dict, lang: Language) -> str:
    """Format a student payment card."""
    student = student_data["student"]
    registration = student_data["registration"]
    course = student_data["course"]
    total_paid = student_data["total_paid"]
    remaining = student_data["remaining"]
    
    status_emoji = format_payment_status_emoji(registration.payment_status)
    status_label = format_payment_status_label(registration.payment_status, lang)
    
    if lang == Language.ARABIC:
        return f"""
💰 *إدارة دفعات الطالب*
{divider()}

👤 *الاسم:* {student.full_name}
📱 *الهاتف:* {student.phone_number}
📚 *الدورة:* {course.name}

{divider()}

💵 *المبلغ الإجمالي:* ${course.price}
✅ *المدفوع:* ${total_paid}
⏳ *المتبقي:* ${remaining}
{status_emoji} *الحالة:* {status_label}

{divider()}
"""
    else:
        return f"""
💰 *Student Payment Management*
{divider()}

👤 *Name:* {student.full_name}
📱 *Phone:* {student.phone_number}
📚 *Course:* {course.name}

{divider()}

💵 *Total Amount:* ${course.price}
✅ *Paid:* ${total_paid}
⏳ *Remaining:* ${remaining}
{status_emoji} *Status:* {status_label}

{divider()}
"""


def get_payment_method_keyboard(registration_id: str, lang: Language) -> InlineKeyboardMarkup:
    """Get payment method selection keyboard."""
    builder = KeyboardBuilder()
    
    methods = [
        (PaymentMethod.CASH, "💵", "نقد" if lang == Language.ARABIC else "Cash"),
        (PaymentMethod.TRANSFER, "🏦", "تحويل" if lang == Language.ARABIC else "Transfer"),
        (PaymentMethod.CARD, "💳", "بطاقة" if lang == Language.ARABIC else "Card"),
    ]
    
    for method, emoji, label in methods:
        builder.add_button_row(
            f"{emoji} {label}",
            f"{PAYMENT_PREFIX}method_{registration_id}_{method.value}"
        )
    
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{PAYMENT_PREFIX}cancel"
    )
    
    return builder.build()


async def show_course_students_for_payment(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    course_id: str,
    get_course_students_use_case,
) -> None:
    """Show students of a course for payment management."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    students = await get_course_students_use_case.execute(course_id)
    
    if not students:
        if lang == Language.ARABIC:
            message = "❌ لا يوجد طلاب مسجلين في هذه الدورة"
        else:
            message = "❌ No students registered in this course"
        
        keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
        
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    course_name = students[0]["course"].name if students else ""
    
    # Store in context
    context.user_data['course_students'] = students
    context.user_data['current_course_id'] = course_id
    
    if lang == Language.ARABIC:
        message = f"""
👥 *طلاب الدورة: {course_name}*
{divider()}

اختر طالباً لإدارة مدفوعاته:
"""
    else:
        message = f"""
👥 *Course Students: {course_name}*
{divider()}

Select a student to manage payments:
"""
    
    builder = KeyboardBuilder()
    for i, student_data in enumerate(students):
        student = student_data["student"]
        status_emoji = format_payment_status_emoji(student_data["registration"].payment_status)
        label = f"{status_emoji} {student.full_name[:20]} - ${student_data['total_paid']}/{student_data['course'].price}"
        builder.add_button_row(label, f"{PAYMENT_PREFIX}student_{i}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{CallbackPrefix.ADMIN}panel"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_student_payment_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    student_index: int,
) -> None:
    """Show payment details for a specific student."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    students = context.user_data.get('course_students', [])
    if student_index >= len(students):
        await query.edit_message_text("❌ خطأ")
        return
    
    student_data = students[student_index]
    context.user_data['current_student_index'] = student_index
    
    message = format_student_payment_card(student_data, lang)
    
    builder = KeyboardBuilder()
    
    # Add payment button
    builder.add_button_row(
        f"➕ " + ("إضافة دفعة" if lang == Language.ARABIC else "Add Payment"),
        f"{PAYMENT_PREFIX}add_{student_data['registration'].id}"
    )
    
    # View history button
    builder.add_button_row(
        f"📋 " + ("سجل الدفعات" if lang == Language.ARABIC else "Payment History"),
        f"{PAYMENT_PREFIX}history_{student_data['registration'].id}"
    )
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{PAYMENT_PREFIX}list_{context.user_data.get('current_course_id', '')}"
    )
    
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def prompt_payment_amount(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    registration_id: str,
) -> None:
    """Prompt admin to enter payment amount."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    context.user_data['adding_payment'] = True
    context.user_data['payment_registration_id'] = registration_id
    context.user_data['payment_step'] = 'amount'
    
    if lang == Language.ARABIC:
        message = f"""
💵 *إضافة دفعة جديدة*
{divider()}

أدخل المبلغ المدفوع (بالدولار):

مثال: `50` أو `100.5`
"""
    else:
        message = f"""
💵 *Add New Payment*
{divider()}

Enter the payment amount (in USD):

Example: `50` or `100.5`
"""
    
    keyboard = get_cancel_keyboard(lang, f"{PAYMENT_PREFIX}cancel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_payment_amount_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle payment amount text input."""
    if not context.user_data.get('adding_payment'):
        return False
    
    if context.user_data.get('payment_step') != 'amount':
        return False
    
    lang = get_user_language(context)
    text = update.message.text.strip()
    
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError("Invalid amount")
        
        context.user_data['payment_amount'] = amount
        context.user_data['payment_step'] = 'method'
        
        registration_id = context.user_data.get('payment_registration_id')
        
        if lang == Language.ARABIC:
            message = f"""
💵 *المبلغ:* ${amount}

اختر طريقة الدفع:
"""
        else:
            message = f"""
💵 *Amount:* ${amount}

Select payment method:
"""
        
        keyboard = get_payment_method_keyboard(registration_id, lang)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
        
    except ValueError:
        if lang == Language.ARABIC:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً (مثال: 50)")
        else:
            await update.message.reply_text("❌ Enter a valid number (example: 50)")
        return True


async def handle_payment_method_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    registration_id: str,
    method: str,
    add_payment_use_case,
) -> None:
    """Handle payment method selection and add payment."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    admin_id = update.effective_user.id
    
    amount = context.user_data.get('payment_amount', 0)
    payment_method = PaymentMethod(method)
    
    # Clear state
    context.user_data.pop('adding_payment', None)
    context.user_data.pop('payment_step', None)
    context.user_data.pop('payment_amount', None)
    context.user_data.pop('payment_registration_id', None)
    
    result = await add_payment_use_case.execute(
        registration_id=registration_id,
        amount=amount,
        method=payment_method,
        admin_telegram_id=admin_id,
    )
    
    if result.success:
        if lang == Language.ARABIC:
            message = f"""
{Emoji.SUCCESS} *تم إضافة الدفعة بنجاح!*
{divider()}

💵 *المبلغ:* ${amount}
📊 *إجمالي المدفوع:* ${result.total_paid}
"""
        else:
            message = f"""
{Emoji.SUCCESS} *Payment Added Successfully!*
{divider()}

💵 *Amount:* ${amount}
📊 *Total Paid:* ${result.total_paid}
"""
    else:
        message = format_error(result.error, lang == Language.ARABIC)
    
    keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def show_payment_history(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    registration_id: str,
    get_payment_history_use_case,
) -> None:
    """Show payment history for a registration."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    payments = await get_payment_history_use_case.execute(registration_id)
    
    if not payments:
        if lang == Language.ARABIC:
            message = "📋 لا توجد دفعات مسجلة"
        else:
            message = "📋 No payments recorded"
    else:
        total = sum(p.amount for p in payments)
        
        if lang == Language.ARABIC:
            message = f"""
📋 *سجل الدفعات*
{divider()}

"""
            for p in payments:
                method_label = {
                    PaymentMethod.CASH: "نقد",
                    PaymentMethod.TRANSFER: "تحويل",
                    PaymentMethod.CARD: "بطاقة",
                }.get(p.method, "أخرى")
                message += f"• ${p.amount} | {method_label} | {p.paid_at.strftime('%Y-%m-%d')}\n"
            
            message += f"\n{divider()}\n💰 *الإجمالي:* ${total}"
        else:
            message = f"""
📋 *Payment History*
{divider()}

"""
            for p in payments:
                message += f"• ${p.amount} | {p.method.value} | {p.paid_at.strftime('%Y-%m-%d')}\n"
            
            message += f"\n{divider()}\n💰 *Total:* ${total}"
    
    keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.ADMIN}panel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_payment_admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for payment admin callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(PAYMENT_PREFIX):
        return False
    
    data = query.data[len(PAYMENT_PREFIX):]
    
    if data.startswith("list_"):
        course_id = data.replace("list_", "")
        await show_course_students_for_payment(
            update, context, course_id,
            container.get_course_students,
        )
        return True
    
    elif data.startswith("student_"):
        index = int(data.replace("student_", ""))
        await show_student_payment_details(update, context, index)
        return True
    
    elif data.startswith("add_"):
        reg_id = data.replace("add_", "")
        await prompt_payment_amount(update, context, reg_id)
        return True
    
    elif data.startswith("method_"):
        parts = data.replace("method_", "").rsplit("_", 1)
        reg_id = parts[0]
        method = parts[1]
        await handle_payment_method_selection(
            update, context, reg_id, method,
            container.add_payment,
        )
        return True
    
    elif data.startswith("history_"):
        reg_id = data.replace("history_", "")
        await show_payment_history(
            update, context, reg_id,
            container.get_payment_history,
        )
        return True
    
    elif data == "cancel":
        context.user_data.pop('adding_payment', None)
        context.user_data.pop('payment_step', None)
        lang = get_user_language(context)
        await query.answer("تم الإلغاء" if lang == Language.ARABIC else "Cancelled")
        # Return to admin panel
        from infrastructure.telegram.handlers.start_handler import show_admin_panel
        await show_admin_panel(update, context)
        return True
    
    return False
