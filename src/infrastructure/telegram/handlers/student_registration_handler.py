"""
Student registration flow handler.
Multi-step registration with name and phone validation.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from domain.entities import Language
from domain.value_objects import validate_syrian_phone, get_phone_input_example
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, divider,
    get_back_and_home_keyboard, get_cancel_keyboard,
)


# Registration flow states
class RegistrationState:
    SELECT_COURSE = "select_course"
    ENTER_NAME = "enter_name"
    ENTER_PHONE = "enter_phone"
    CONFIRM = "confirm"


# Callback prefix
REG_PREFIX = "stdreg_"


def get_available_courses_keyboard(courses: list, lang: Language) -> InlineKeyboardMarkup:
    """Build keyboard with available courses."""
    builder = KeyboardBuilder()
    
    for course in courses:
        price_label = f"${course.price}"
        builder.add_button_row(
            f"📚 {course.name} - {price_label}",
            f"{REG_PREFIX}course_{course.id}"
        )
    
    builder.add_button_row(
        f"🔙 " + ("القائمة الرئيسية" if lang == Language.ARABIC else "Main Menu"),
        f"{CallbackPrefix.NAV}main"
    )
    
    return builder.build()


async def start_registration_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_courses_use_case,
) -> None:
    """Start the registration flow - show available courses."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    # Get available courses
    courses = await get_courses_use_case.execute()
    
    if not courses:
        if lang == Language.ARABIC:
            message = f"""
{Emoji.WARNING} *لا توجد دورات متاحة حالياً*
{divider()}

يرجى المحاولة لاحقاً عندما تتوفر دورات جديدة.
"""
        else:
            message = f"""
{Emoji.WARNING} *No Courses Available*
{divider()}

Please try again when new courses are available.
"""
        keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.NAV}main")
        
        if query:
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return
    
    # Store courses in context
    context.user_data['available_courses'] = {c.id: c for c in courses}
    
    if lang == Language.ARABIC:
        message = f"""
📚 *التسجيل في دورة*
{divider()}

اختر الدورة التي تريد التسجيل فيها:
"""
    else:
        message = f"""
📚 *Course Registration*
{divider()}

Select the course you want to register for:
"""
    
    keyboard = get_available_courses_keyboard(courses, lang)
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_course_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    course_id: str,
) -> None:
    """Handle course selection - prompt for name."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    courses = context.user_data.get('available_courses', {})
    course = courses.get(course_id)
    
    if not course:
        await query.edit_message_text("❌ خطأ في اختيار الدورة")
        return
    
    # Set registration state
    context.user_data['registration_flow'] = {
        'state': RegistrationState.ENTER_NAME,
        'course_id': course_id,
        'course_name': course.name,
        'course_price': course.price,
    }
    
    if lang == Language.ARABIC:
        message = f"""
📝 *التسجيل في: {course.name}*
{divider()}

💵 *السعر:* ${course.price}

{divider()}

*الخطوة 1 من 3*

👤 أدخل اسمك الكامل (الاسم الثلاثي):

مثال: `أحمد محمد العلي`
"""
    else:
        message = f"""
📝 *Registering for: {course.name}*
{divider()}

💵 *Price:* ${course.price}

{divider()}

*Step 1 of 3*

👤 Enter your full name:

Example: `Ahmed Mohammed Ali`
"""
    
    keyboard = get_cancel_keyboard(lang, f"{REG_PREFIX}cancel")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_name_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle name input from user."""
    flow = context.user_data.get('registration_flow')
    if not flow or flow.get('state') != RegistrationState.ENTER_NAME:
        return False
    
    lang = get_user_language(context)
    name = update.message.text.strip()
    
    # Validate name (at least 2 words, each at least 2 characters)
    name_parts = name.split()
    if len(name_parts) < 2 or any(len(part) < 2 for part in name_parts):
        if lang == Language.ARABIC:
            await update.message.reply_text(
                "❌ يرجى إدخال الاسم الكامل (اسمين على الأقل)\n\n"
                "مثال: `أحمد محمد`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Please enter your full name (at least 2 names)\n\n"
                "Example: `Ahmed Mohammed`",
                parse_mode='Markdown'
            )
        return True
    
    # Store name and move to phone step
    flow['full_name'] = name
    flow['state'] = RegistrationState.ENTER_PHONE
    context.user_data['registration_flow'] = flow
    
    if lang == Language.ARABIC:
        message = f"""
📝 *التسجيل في: {flow['course_name']}*
{divider()}

✅ *الاسم:* {name}

{divider()}

*الخطوة 2 من 3*

{get_phone_input_example()}
"""
    else:
        message = f"""
📝 *Registering for: {flow['course_name']}*
{divider()}

✅ *Name:* {name}

{divider()}

*Step 2 of 3*

📱 *Enter your phone number:*

Accepted formats:
• `0912345678` (10 digits starting with 09)
• `+963912345678` (with country code)

Example: `0991234567`
"""
    
    keyboard = get_cancel_keyboard(lang, f"{REG_PREFIX}cancel")
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
    return True


async def handle_phone_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle phone input from user."""
    flow = context.user_data.get('registration_flow')
    if not flow or flow.get('state') != RegistrationState.ENTER_PHONE:
        return False
    
    lang = get_user_language(context)
    phone = update.message.text.strip()
    
    # Validate phone
    is_valid, normalized_phone, error = validate_syrian_phone(phone)
    
    if not is_valid:
        if lang == Language.ARABIC:
            await update.message.reply_text(
                f"❌ {error}\n\n"
                f"الصيغ المقبولة:\n"
                f"• `0912345678` (10 أرقام تبدأ بـ 09)\n"
                f"• `+963912345678` (مع رمز الدولة)\n\n"
                f"مثال: `0991234567`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ {error}\n\n"
                f"Valid formats:\n"
                f"• `0912345678` (10 digits starting with 09)\n"
                f"• `+963912345678` (with country code)\n\n"
                f"Example: `0991234567`",
                parse_mode='Markdown'
            )
        return True
    
    # Store phone and move to confirmation
    flow['phone_number'] = normalized_phone
    flow['state'] = RegistrationState.CONFIRM
    context.user_data['registration_flow'] = flow
    
    # Show confirmation
    if lang == Language.ARABIC:
        message = f"""
📝 *تأكيد التسجيل*
{divider()}

📚 *الدورة:* {flow['course_name']}
💵 *السعر:* ${flow['course_price']}

{divider()}

👤 *الاسم:* {flow['full_name']}
📱 *الهاتف:* {normalized_phone}

{divider()}

*الخطوة 3 من 3*

هل تريد تأكيد التسجيل؟
"""
    else:
        message = f"""
📝 *Confirm Registration*
{divider()}

📚 *Course:* {flow['course_name']}
💵 *Price:* ${flow['course_price']}

{divider()}

👤 *Name:* {flow['full_name']}
📱 *Phone:* {normalized_phone}

{divider()}

*Step 3 of 3*

Do you want to confirm registration?
"""
    
    builder = KeyboardBuilder()
    builder.add_button(
        f"✅ " + ("تأكيد" if lang == Language.ARABIC else "Confirm"),
        f"{REG_PREFIX}confirm"
    )
    builder.add_button(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{REG_PREFIX}cancel"
    )
    builder.add_row()
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())
    return True


async def handle_registration_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    request_registration_use_case,
) -> None:
    """Handle registration confirmation."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    flow = context.user_data.get('registration_flow')
    if not flow or flow.get('state') != RegistrationState.CONFIRM:
        await query.edit_message_text("❌ خطأ في عملية التسجيل")
        return
    
    # Clear flow state
    context.user_data.pop('registration_flow', None)
    
    # Execute registration
    result = await request_registration_use_case.execute(
        telegram_id=user_id,
        full_name=flow['full_name'],
        phone_number=flow['phone_number'],
        course_id=flow['course_id'],
    )
    
    if result.success:
        if lang == Language.ARABIC:
            message = f"""
{Emoji.SUCCESS} *تم إرسال طلب التسجيل بنجاح!*
{divider()}

📚 *الدورة:* {flow['course_name']}
👤 *الاسم:* {flow['full_name']}
📱 *الهاتف:* {flow['phone_number']}

{divider()}

⏳ طلبك قيد المراجعة من قبل الإدارة.
سيتم إشعارك فور الموافقة على طلبك.

شكراً لاختيارك مركز التدريب! 🎓
"""
        else:
            message = f"""
{Emoji.SUCCESS} *Registration Request Submitted!*
{divider()}

📚 *Course:* {flow['course_name']}
👤 *Name:* {flow['full_name']}
📱 *Phone:* {flow['phone_number']}

{divider()}

⏳ Your request is under review.
You will be notified once approved.

Thank you for choosing our Training Center! 🎓
"""
    else:
        message = format_error(result.error, lang == Language.ARABIC)
    
    keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.NAV}main")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_registration_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle registration cancellation."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    # Clear flow state
    context.user_data.pop('registration_flow', None)
    
    if lang == Language.ARABIC:
        message = f"""
{Emoji.WARNING} *تم إلغاء التسجيل*
{divider()}

يمكنك البدء من جديد في أي وقت.
"""
    else:
        message = f"""
{Emoji.WARNING} *Registration Cancelled*
{divider()}

You can start again at any time.
"""
    
    keyboard = get_back_and_home_keyboard(lang, f"{CallbackPrefix.NAV}main")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_registration_text_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Main text input handler for registration flow."""
    flow = context.user_data.get('registration_flow')
    if not flow:
        return False
    
    state = flow.get('state')
    
    if state == RegistrationState.ENTER_NAME:
        return await handle_name_input(update, context)
    elif state == RegistrationState.ENTER_PHONE:
        return await handle_phone_input(update, context)
    
    return False


async def handle_registration_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for registration callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(REG_PREFIX):
        return False
    
    data = query.data[len(REG_PREFIX):]
    
    if data == "start":
        await start_registration_flow(update, context, container.get_courses)
        return True
    
    elif data.startswith("course_"):
        course_id = data.replace("course_", "")
        await handle_course_selection(update, context, course_id)
        return True
    
    elif data == "confirm":
        await handle_registration_confirm(update, context, container.request_registration)
        return True
    
    elif data == "cancel":
        await handle_registration_cancel(update, context)
        return True
    
    return False
