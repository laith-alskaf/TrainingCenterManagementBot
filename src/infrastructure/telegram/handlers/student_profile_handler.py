"""
Student profile handler.
Multi-step profile completion with validation and examples.
"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional, Tuple

from domain.entities import Language, Gender, EducationLevel, Student
from domain.value_objects import validate_syrian_phone, now_syria
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, divider,
    format_success, format_error,
    get_cancel_keyboard, get_home_keyboard,
)


# Callback prefix
PROFILE_PREFIX = "profile_"


# Profile steps
class ProfileStep:
    FULL_NAME = "full_name"
    PHONE = "phone"
    OTP_VERIFY = "otp_verify"  # WhatsApp OTP verification
    GENDER = "gender"
    AGE = "age"
    RESIDENCE = "residence"
    EDUCATION = "education"
    SPECIALIZATION = "specialization"
    CONFIRM = "confirm"


# Step order
STEP_ORDER = [
    ProfileStep.FULL_NAME,
    ProfileStep.PHONE,
    ProfileStep.OTP_VERIFY,
    ProfileStep.GENDER,
    ProfileStep.AGE,
    ProfileStep.RESIDENCE,
    ProfileStep.EDUCATION,
    ProfileStep.SPECIALIZATION,
    ProfileStep.CONFIRM,
]


def get_step_number(step: str) -> int:
    """Get the step number (1-indexed)."""
    try:
        return STEP_ORDER.index(step) + 1
    except ValueError:
        return 0


def get_total_steps() -> int:
    """Get total number of steps (excluding confirm)."""
    return len(STEP_ORDER) - 1  # Exclude confirm step


def get_progress_bar(step: str, lang: Language) -> str:
    """Get a visual progress bar for the current step."""
    current = get_step_number(step)
    total = get_total_steps()
    
    filled = "▓" * current
    empty = "░" * (total - current)
    
    if lang == Language.ARABIC:
        return f"الخطوة {current} من {total}\n{filled}{empty}"
    else:
        return f"Step {current} of {total}\n{filled}{empty}"


def get_education_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get education level selection keyboard."""
    builder = KeyboardBuilder()
    
    levels = [
        (EducationLevel.MIDDLE_SCHOOL, "📚", "إعدادي" if lang == Language.ARABIC else "Middle School"),
        (EducationLevel.HIGH_SCHOOL, "🎓", "ثانوي" if lang == Language.ARABIC else "High School"),
        (EducationLevel.DIPLOMA, "🏫", "معهد" if lang == Language.ARABIC else "Diploma"),
        (EducationLevel.BACHELOR, "🎓", "بكالوريوس" if lang == Language.ARABIC else "Bachelor"),
        (EducationLevel.MASTER, "📜", "ماجستير" if lang == Language.ARABIC else "Master"),
        (EducationLevel.PHD, "🔬", "دكتوراه" if lang == Language.ARABIC else "PhD"),
        (EducationLevel.OTHER, "📝", "أخرى" if lang == Language.ARABIC else "Other"),
    ]
    
    # Two buttons per row
    for i in range(0, len(levels), 2):
        for level, emoji, label in levels[i:i+2]:
            builder.add_button(f"{emoji} {label}", f"{PROFILE_PREFIX}edu_{level.value}")
        builder.add_row()
    
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{PROFILE_PREFIX}cancel"
    )
    
    return builder.build()


def get_gender_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get gender selection keyboard."""
    builder = KeyboardBuilder()
    
    builder.add_button(
        "👨 " + ("ذكر" if lang == Language.ARABIC else "Male"),
        f"{PROFILE_PREFIX}gender_male"
    )
    builder.add_button(
        "👩 " + ("أنثى" if lang == Language.ARABIC else "Female"),
        f"{PROFILE_PREFIX}gender_female"
    )
    builder.add_row()
    
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{PROFILE_PREFIX}cancel"
    )
    
    return builder.build()


def get_otp_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get OTP verification keyboard with resend and change phone options."""
    builder = KeyboardBuilder()
    
    builder.add_button(
        "🔄 " + ("إعادة إرسال" if lang == Language.ARABIC else "Resend"),
        f"{PROFILE_PREFIX}otp_resend"
    )
    builder.add_button(
        "📱 " + ("تغيير الرقم" if lang == Language.ARABIC else "Change Phone"),
        f"{PROFILE_PREFIX}otp_change_phone"
    )
    builder.add_row()
    
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{PROFILE_PREFIX}cancel"
    )
    
    return builder.build()


def needs_specialization(education_level: EducationLevel) -> bool:
    """Check if specialization is needed for this education level."""
    return education_level in (
        EducationLevel.DIPLOMA,
        EducationLevel.BACHELOR,
        EducationLevel.MASTER,
        EducationLevel.PHD,
    )


# Validation functions

def validate_full_name(name: str, lang: Language) -> Tuple[bool, str, Optional[str]]:
    """Validate full name (at least 3 words)."""
    parts = name.strip().split()
    
    if len(parts) < 3:
        if lang == Language.ARABIC:
            return False, "", "❌ يرجى إدخال الاسم الثلاثي (3 كلمات على الأقل)"
        else:
            return False, "", "❌ Please enter your full name (at least 3 words)"
    
    if any(len(p) < 2 for p in parts):
        if lang == Language.ARABIC:
            return False, "", "❌ كل كلمة يجب أن تكون حرفين على الأقل"
        else:
            return False, "", "❌ Each word must be at least 2 characters"
    
    return True, name.strip(), None


def validate_age(age_str: str, lang: Language) -> Tuple[bool, int, Optional[str]]:
    """Validate age (10-80)."""
    try:
        age = int(age_str.strip())
        if age < 10 or age > 80:
            if lang == Language.ARABIC:
                return False, 0, "❌ العمر يجب أن يكون بين 10 و 80 سنة"
            else:
                return False, 0, "❌ Age must be between 10 and 80"
        return True, age, None
    except ValueError:
        if lang == Language.ARABIC:
            return False, 0, "❌ أدخل رقماً صحيحاً (مثال: 25)"
        else:
            return False, 0, "❌ Enter a valid number (example: 25)"


def validate_residence(residence: str, lang: Language) -> Tuple[bool, str, Optional[str]]:
    """Validate residence (at least 3 characters)."""
    residence = residence.strip()
    if len(residence) < 3:
        if lang == Language.ARABIC:
            return False, "", "❌ مكان الإقامة قصير جداً (3 أحرف على الأقل)"
        else:
            return False, "", "❌ Residence is too short (at least 3 characters)"
    return True, residence, None


def validate_specialization(spec: str, lang: Language) -> Tuple[bool, str, Optional[str]]:
    """Validate specialization (at least 2 characters)."""
    spec = spec.strip()
    if len(spec) < 2:
        if lang == Language.ARABIC:
            return False, "", "❌ الاختصاص قصير جداً"
        else:
            return False, "", "❌ Specialization is too short"
    return True, spec, None


# Message formatters

def get_step_message(step: str, lang: Language, profile_data: dict = None) -> str:
    """Get the message for a profile step."""
    progress = get_progress_bar(step, lang)
    
    if step == ProfileStep.FULL_NAME:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

👤 *أدخل اسمك الثلاثي:*

📌 *مثال:* `أحمد محمد العلي`

⚠️ يجب أن يكون 3 كلمات على الأقل
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

👤 *Enter your full name:*

📌 *Example:* `Ahmed Mohammed Ali`

⚠️ Must be at least 3 words
"""
    
    elif step == ProfileStep.PHONE:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

📱 *أدخل رقم هاتفك:*

📌 *الصيغ المقبولة:*
• `0912345678` ← 10 أرقام تبدأ بـ 09
• `+963912345678` ← مع رمز الدولة

📌 *مثال:* `0991234567`
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

📱 *Enter your phone number:*

📌 *Valid formats:*
• `0912345678` ← 10 digits starting with 09
• `+963912345678` ← with country code

📌 *Example:* `0991234567`
"""
    
    elif step == ProfileStep.OTP_VERIFY:
        masked_phone = profile_data.get('phone_number', '')[:4] + "****" + profile_data.get('phone_number', '')[-3:] if profile_data else "***"
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

📱 *تم إرسال رمز التحقق عبر واتساب*

الرقم: `{masked_phone}`

✏️ *أدخل رمز التحقق المكون من 6 أرقام:*

⚠️ الرمز صالح لمدة 5 دقائق
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

📱 *Verification code sent via WhatsApp*

Phone: `{masked_phone}`

✏️ *Enter the 6-digit verification code:*

⚠️ Code expires in 5 minutes
"""
    
    elif step == ProfileStep.GENDER:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

👤 *اختر جنسك:*
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

👤 *Select your gender:*
"""
    
    elif step == ProfileStep.AGE:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

🎂 *أدخل عمرك:*

📌 *مثال:* `25`

⚠️ يجب أن يكون بين 10 و 80 سنة
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

🎂 *Enter your age:*

📌 *Example:* `25`

⚠️ Must be between 10 and 80 years
"""
    
    elif step == ProfileStep.RESIDENCE:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

🏠 *أدخل مكان إقامتك:*

📌 *مثال:* `دمشق - المزة`

يمكنك كتابة المدينة والحي
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

🏠 *Enter your residence:*

📌 *Example:* `Damascus - Mazzeh`

You can write the city and neighborhood
"""
    
    elif step == ProfileStep.EDUCATION:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

🎓 *اختر مستواك الدراسي:*
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

🎓 *Select your education level:*
"""
    
    elif step == ProfileStep.SPECIALIZATION:
        if lang == Language.ARABIC:
            return f"""
📝 *إكمال الملف الشخصي*
{divider()}

{progress}

📚 *أدخل اختصاصك:*

📌 *أمثلة:*
• `هندسة معلوماتية`
• `طب بشري`
• `إدارة أعمال`
• `تصميم غرافيكي`
"""
        else:
            return f"""
📝 *Complete Your Profile*
{divider()}

{progress}

📚 *Enter your specialization:*

📌 *Examples:*
• `Computer Engineering`
• `Medicine`
• `Business Administration`
• `Graphic Design`
"""
    
    elif step == ProfileStep.CONFIRM:
        data = profile_data or {}
        
        gender_ar = "ذكر" if data.get("gender") == Gender.MALE else "أنثى"
        gender_en = "Male" if data.get("gender") == Gender.MALE else "Female"
        
        edu_labels = {
            EducationLevel.MIDDLE_SCHOOL: ("إعدادي", "Middle School"),
            EducationLevel.HIGH_SCHOOL: ("ثانوي", "High School"),
            EducationLevel.DIPLOMA: ("معهد", "Diploma"),
            EducationLevel.BACHELOR: ("بكالوريوس", "Bachelor"),
            EducationLevel.MASTER: ("ماجستير", "Master"),
            EducationLevel.PHD: ("دكتوراه", "PhD"),
            EducationLevel.OTHER: ("أخرى", "Other"),
        }
        edu = data.get("education_level", EducationLevel.OTHER)
        edu_ar, edu_en = edu_labels.get(edu, ("أخرى", "Other"))
        
        spec = data.get("specialization", "")
        spec_line = ""
        if spec:
            spec_line = f"📚 *الاختصاص:* {spec}\n" if lang == Language.ARABIC else f"📚 *Specialization:* {spec}\n"
        
        if lang == Language.ARABIC:
            return f"""
✅ *تأكيد الملف الشخصي*
{divider()}

👤 *الاسم:* {data.get('full_name', '')}
📱 *الهاتف:* {data.get('phone_number', '')}
👤 *الجنس:* {gender_ar}
🎂 *العمر:* {data.get('age', 0)} سنة
🏠 *الإقامة:* {data.get('residence', '')}
🎓 *التحصيل:* {edu_ar}
{spec_line}
{divider()}

هل المعلومات صحيحة؟
"""
        else:
            return f"""
✅ *Confirm Profile*
{divider()}

👤 *Name:* {data.get('full_name', '')}
📱 *Phone:* {data.get('phone_number', '')}
👤 *Gender:* {gender_en}
🎂 *Age:* {data.get('age', 0)} years
🏠 *Residence:* {data.get('residence', '')}
🎓 *Education:* {edu_en}
{spec_line}
{divider()}

Is this information correct?
"""
    
    return ""


def get_confirm_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get confirmation keyboard."""
    builder = KeyboardBuilder()
    
    builder.add_button(
        f"✅ " + ("تأكيد" if lang == Language.ARABIC else "Confirm"),
        f"{PROFILE_PREFIX}confirm_yes"
    )
    builder.add_button(
        f"✏️ " + ("تعديل" if lang == Language.ARABIC else "Edit"),
        f"{PROFILE_PREFIX}edit"
    )
    builder.add_row()
    
    return builder.build()


# Handler functions

async def start_profile_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Start the profile completion flow."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    # Initialize profile data
    context.user_data['profile_flow'] = {
        'step': ProfileStep.FULL_NAME,
        'data': {},
    }
    
    message = get_step_message(ProfileStep.FULL_NAME, lang)
    keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)


async def handle_profile_text_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Handle text input for profile completion."""
    flow = context.user_data.get('profile_flow')
    if not flow:
        return False
    
    step = flow.get('step')
    if step not in [ProfileStep.FULL_NAME, ProfileStep.PHONE, ProfileStep.OTP_VERIFY, ProfileStep.AGE,
                    ProfileStep.RESIDENCE, ProfileStep.SPECIALIZATION]:
        return False
    
    lang = get_user_language(context)
    text = update.message.text.strip()
    
    # Validate based on step
    if step == ProfileStep.FULL_NAME:
        is_valid, value, error = validate_full_name(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        flow['data']['full_name'] = value
        # Move to phone
        flow['step'] = ProfileStep.PHONE
        message = get_step_message(ProfileStep.PHONE, lang)
        keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    elif step == ProfileStep.PHONE:
        is_valid, normalized, error = validate_syrian_phone(text)
        if not is_valid:
            if lang == Language.ARABIC:
                await update.message.reply_text(
                    f"❌ {error}\n\n"
                    f"📌 الصيغ المقبولة:\n"
                    f"• `0912345678`\n"
                    f"• `+963912345678`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ {error}\n\n"
                    f"📌 Valid formats:\n"
                    f"• `0912345678`\n"
                    f"• `+963912345678`",
                    parse_mode='Markdown'
                )
            return True
        
        flow['data']['phone_number'] = normalized
        flow['data']['phone_pending_verification'] = normalized
        
        # Send OTP via WhatsApp (container passed via context)
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            user_id = update.effective_user.id
            success, otp_message = await whatsapp_adapter.send_otp(user_id, normalized)
            
            if success:
                # Move to OTP verification
                flow['step'] = ProfileStep.OTP_VERIFY
                context.user_data['profile_flow'] = flow
                message = get_step_message(ProfileStep.OTP_VERIFY, lang, flow['data'])
                keyboard = get_otp_keyboard(lang)
                await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
            else:
                # OTP send failed
                await update.message.reply_text(
                    f"❌ {otp_message}\n\n" + 
                    ("حاول مرة أخرى أو تأكد من صحة الرقم." if lang == Language.ARABIC else "Please try again or verify the phone number."),
                    parse_mode='Markdown'
                )
        else:
            # WhatsApp adapter not configured, skip OTP verification
            flow['step'] = ProfileStep.GENDER
            context.user_data['profile_flow'] = flow
            flow['data']['phone_verified'] = False  # Mark as unverified
            message = get_step_message(ProfileStep.GENDER, lang)
            keyboard = get_gender_keyboard(lang)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    elif step == ProfileStep.OTP_VERIFY:
        # Validate OTP code
        if not text.isdigit() or len(text) != 6:
            if lang == Language.ARABIC:
                await update.message.reply_text("❌ الرمز يجب أن يكون 6 أرقام")
            else:
                await update.message.reply_text("❌ Code must be 6 digits")
            return True
        
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            user_id = update.effective_user.id
            success, verify_message = whatsapp_adapter.verify_otp(user_id, text)
            
            if success:
                # OTP verified, move to gender
                flow['data']['phone_verified'] = True
                flow['step'] = ProfileStep.GENDER
                context.user_data['profile_flow'] = flow
                
                # Clear OTP data
                whatsapp_adapter.clear_otp(user_id)
                
                if lang == Language.ARABIC:
                    await update.message.reply_text("✅ تم التحقق من رقم الهاتف بنجاح!")
                else:
                    await update.message.reply_text("✅ Phone number verified successfully!")
                
                message = get_step_message(ProfileStep.GENDER, lang)
                keyboard = get_gender_keyboard(lang)
                await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
            else:
                # OTP verification failed
                await update.message.reply_text(verify_message)
        else:
            # No adapter, skip
            flow['step'] = ProfileStep.GENDER
            context.user_data['profile_flow'] = flow
            message = get_step_message(ProfileStep.GENDER, lang)
            keyboard = get_gender_keyboard(lang)
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    elif step == ProfileStep.AGE:
        is_valid, value, error = validate_age(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        flow['data']['age'] = value
        # Move to residence
        flow['step'] = ProfileStep.RESIDENCE
        message = get_step_message(ProfileStep.RESIDENCE, lang)
        keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    elif step == ProfileStep.RESIDENCE:
        is_valid, value, error = validate_residence(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        flow['data']['residence'] = value
        # Move to education
        flow['step'] = ProfileStep.EDUCATION
        message = get_step_message(ProfileStep.EDUCATION, lang)
        keyboard = get_education_keyboard(lang)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    elif step == ProfileStep.SPECIALIZATION:
        is_valid, value, error = validate_specialization(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        flow['data']['specialization'] = value
        # Move to confirm
        flow['step'] = ProfileStep.CONFIRM
        message = get_step_message(ProfileStep.CONFIRM, lang, flow['data'])
        keyboard = get_confirm_keyboard(lang)
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    context.user_data['profile_flow'] = flow
    return True


async def handle_profile_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle profile-related callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(PROFILE_PREFIX):
        return False
    
    data = query.data[len(PROFILE_PREFIX):]
    lang = get_user_language(context)
    flow = context.user_data.get('profile_flow', {})
    
    # Start profile
    if data == "start":
        await start_profile_flow(update, context)
        return True
    
    # Cancel
    elif data == "cancel":
        await query.answer()
        context.user_data.pop('profile_flow', None)
        # Clear any OTP data
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            whatsapp_adapter.clear_otp(update.effective_user.id)
        if lang == Language.ARABIC:
            message = "❌ تم إلغاء إكمال الملف الشخصي"
        else:
            message = "❌ Profile completion cancelled"
        keyboard = get_home_keyboard(lang)
        await query.edit_message_text(message, reply_markup=keyboard)
        return True
    
    # OTP resend
    elif data == "otp_resend":
        await query.answer()
        phone = flow.get('data', {}).get('phone_pending_verification', '')
        if not phone:
            if lang == Language.ARABIC:
                await query.edit_message_text("❌ حدث خطأ. أعد إدخال رقم الهاتف.")
            else:
                await query.edit_message_text("❌ Error. Please re-enter phone number.")
            return True
        
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            user_id = update.effective_user.id
            success, otp_message = await whatsapp_adapter.send_otp(user_id, phone)
            
            if success:
                message = get_step_message(ProfileStep.OTP_VERIFY, lang, flow['data'])
                keyboard = get_otp_keyboard(lang)
                if lang == Language.ARABIC:
                    await query.answer("✅ تم إعادة إرسال الرمز", show_alert=True)
                else:
                    await query.answer("✅ Code resent", show_alert=True)
                await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
            else:
                await query.answer(otp_message, show_alert=True)
        return True
    
    # OTP change phone
    elif data == "otp_change_phone":
        await query.answer()
        # Clear OTP and go back to phone step
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            whatsapp_adapter.clear_otp(update.effective_user.id)
        
        flow['step'] = ProfileStep.PHONE
        flow['data'].pop('phone_pending_verification', None)
        context.user_data['profile_flow'] = flow
        
        message = get_step_message(ProfileStep.PHONE, lang)
        keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    # Gender selection
    elif data.startswith("gender_"):
        await query.answer()
        gender = Gender.MALE if data == "gender_male" else Gender.FEMALE
        flow['data']['gender'] = gender
        # Move to age
        flow['step'] = ProfileStep.AGE
        context.user_data['profile_flow'] = flow
        message = get_step_message(ProfileStep.AGE, lang)
        keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    # Education selection
    elif data.startswith("edu_"):
        await query.answer()
        edu_value = data.replace("edu_", "")
        education = EducationLevel(edu_value)
        flow['data']['education_level'] = education
        
        # Check if specialization is needed
        if needs_specialization(education):
            flow['step'] = ProfileStep.SPECIALIZATION
            context.user_data['profile_flow'] = flow
            message = get_step_message(ProfileStep.SPECIALIZATION, lang)
            keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        else:
            flow['data']['specialization'] = None
            flow['step'] = ProfileStep.CONFIRM
            context.user_data['profile_flow'] = flow
            message = get_step_message(ProfileStep.CONFIRM, lang, flow['data'])
            keyboard = get_confirm_keyboard(lang)
            await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    # Edit (go back to start)
    elif data == "edit":
        await query.answer()
        flow['step'] = ProfileStep.FULL_NAME
        context.user_data['profile_flow'] = flow
        message = get_step_message(ProfileStep.FULL_NAME, lang)
        keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}cancel")
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    # Confirm profile
    elif data == "confirm_yes":
        await query.answer()
        
        user_id = update.effective_user.id
        profile_data = flow.get('data', {})
        
        # Get or create student
        student = await container.student_repo.get_by_telegram_id(user_id)
        now = now_syria()
        
        if student:
            # Update existing
            student.full_name = profile_data.get('full_name', '')
            student.phone_number = profile_data.get('phone_number', '')
            student.gender = profile_data.get('gender', Gender.MALE)
            student.age = profile_data.get('age', 0)
            student.residence = profile_data.get('residence', '')
            student.education_level = profile_data.get('education_level', EducationLevel.OTHER)
            student.specialization = profile_data.get('specialization')
            student.profile_completed = True
            student.updated_at = now
        else:
            # Create new
            student = Student.create(
                telegram_id=user_id,
                full_name=profile_data.get('full_name', ''),
                phone_number=profile_data.get('phone_number', ''),
                gender=profile_data.get('gender', Gender.MALE),
                age=profile_data.get('age', 0),
                residence=profile_data.get('residence', ''),
                education_level=profile_data.get('education_level', EducationLevel.OTHER),
                now=now,
                specialization=profile_data.get('specialization'),
                language=lang,
            )
        
        await container.student_repo.save(student)
        
        # Clear flow
        context.user_data.pop('profile_flow', None)
        
        if lang == Language.ARABIC:
            message = f"""
{Emoji.SUCCESS} *تم إكمال ملفك الشخصي بنجاح!*
{divider()}

يمكنك الآن تصفح الدورات والتسجيل.

اضغط /start للعودة للقائمة الرئيسية.
"""
        else:
            message = f"""
{Emoji.SUCCESS} *Profile Completed Successfully!*
{divider()}

You can now browse courses and register.

Press /start to return to main menu.
"""
        
        keyboard = get_home_keyboard(lang)
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    return False


async def check_profile_complete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Check if student profile is complete. Returns True if complete."""
    user_id = update.effective_user.id
    student = await container.student_repo.get_by_telegram_id(user_id)
    
    if not student or not student.profile_completed:
        return False
    return True


async def show_profile_required_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show message that profile is required."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    if lang == Language.ARABIC:
        message = f"""
⚠️ *يرجى إكمال ملفك الشخصي أولاً!*
{divider()}

لاستخدام خدمات المركز، يجب عليك إكمال ملفك الشخصي.

انقر الزر أدناه للبدء:
"""
    else:
        message = f"""
⚠️ *Please Complete Your Profile First!*
{divider()}

To use training center services, you must complete your profile.

Click the button below to start:
"""
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"📝 " + ("إكمال الملف الشخصي" if lang == Language.ARABIC else "Complete Profile"),
        f"{PROFILE_PREFIX}start"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_student_profile(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> None:
    """Show student's profile information with edit option."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    student = await container.student_repo.get_by_telegram_id(user_id)
    
    if not student:
        if lang == Language.ARABIC:
            message = "❌ لم يتم العثور على ملفك الشخصي."
        else:
            message = "❌ Profile not found."
        if query:
            await query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return
    
    # Format profile info
    gender_ar = "ذكر" if student.gender == Gender.MALE else "أنثى"
    gender_en = "Male" if student.gender == Gender.MALE else "Female"
    
    edu_labels = {
        EducationLevel.MIDDLE_SCHOOL: ("إعدادي", "Middle School"),
        EducationLevel.HIGH_SCHOOL: ("ثانوي", "High School"),
        EducationLevel.DIPLOMA: ("معهد", "Diploma"),
        EducationLevel.BACHELOR: ("بكالوريوس", "Bachelor"),
        EducationLevel.MASTER: ("ماجستير", "Master"),
        EducationLevel.PHD: ("دكتوراه", "PhD"),
        EducationLevel.OTHER: ("أخرى", "Other"),
    }
    edu_ar, edu_en = edu_labels.get(student.education_level, ("أخرى", "Other"))
    
    phone_verified = getattr(student, 'phone_verified', False)
    verified_badge = " ✅" if phone_verified else " ⚠️"
    
    if lang == Language.ARABIC:
        spec_line = f"📚 *الاختصاص:* {student.specialization}\n" if student.specialization else ""
        message = f"""
👤 *ملفك الشخصي*
{divider()}

👤 *الاسم:* {student.full_name}
📱 *الهاتف:* {student.phone_number}{verified_badge}
👤 *الجنس:* {gender_ar}
🎂 *العمر:* {student.age} سنة
🏠 *الإقامة:* {student.residence}
🎓 *التحصيل:* {edu_ar}
{spec_line}
{divider()}

{"✅ تم التحقق من رقم الهاتف" if phone_verified else "⚠️ رقم الهاتف غير موثق"}
"""
    else:
        spec_line = f"📚 *Specialization:* {student.specialization}\n" if student.specialization else ""
        message = f"""
👤 *Your Profile*
{divider()}

👤 *Name:* {student.full_name}
📱 *Phone:* {student.phone_number}{verified_badge}
👤 *Gender:* {gender_en}
🎂 *Age:* {student.age} years
🏠 *Residence:* {student.residence}
🎓 *Education:* {edu_en}
{spec_line}
{divider()}

{"✅ Phone number verified" if phone_verified else "⚠️ Phone number not verified"}
"""
    
    builder = KeyboardBuilder()
    
    # Edit buttons
    builder.add_button(
        "✏️ " + ("تعديل الاسم" if lang == Language.ARABIC else "Edit Name"),
        f"{PROFILE_PREFIX}edit_name"
    )
    builder.add_button(
        "📱 " + ("تعديل الهاتف" if lang == Language.ARABIC else "Edit Phone"),
        f"{PROFILE_PREFIX}edit_phone"
    )
    builder.add_row()
    
    builder.add_button(
        "🏠 " + ("تعديل الإقامة" if lang == Language.ARABIC else "Edit Residence"),
        f"{PROFILE_PREFIX}edit_residence"
    )
    builder.add_button(
        "🎓 " + ("تعديل التحصيل" if lang == Language.ARABIC else "Edit Education"),
        f"{PROFILE_PREFIX}edit_education"
    )
    builder.add_row()
    
    builder.add_button_row(
        "🏠 " + ("القائمة الرئيسية" if lang == Language.ARABIC else "Main Menu"),
        "home"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def handle_profile_edit_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle profile edit callbacks."""
    query = update.callback_query
    if not query or not query.data.startswith(f"{PROFILE_PREFIX}edit_"):
        return False
    
    await query.answer()
    data = query.data.replace(f"{PROFILE_PREFIX}edit_", "")
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    # Set edit mode
    context.user_data['profile_edit'] = {'field': data}
    
    if data == "name":
        if lang == Language.ARABIC:
            message = """
✏️ *تعديل الاسم*

أدخل اسمك الثلاثي الجديد:

📌 *مثال:* `أحمد محمد العلي`
"""
        else:
            message = """
✏️ *Edit Name*

Enter your new full name:

📌 *Example:* `Ahmed Mohammed Ali`
"""
    elif data == "phone":
        if lang == Language.ARABIC:
            message = """
✏️ *تعديل رقم الهاتف*

أدخل رقم الهاتف الجديد:

📌 *مثال:* `0991234567`

⚠️ سيتطلب تحقق جديد عبر واتساب
"""
        else:
            message = """
✏️ *Edit Phone Number*

Enter your new phone number:

📌 *Example:* `0991234567`

⚠️ Will require new WhatsApp verification
"""
    elif data == "residence":
        if lang == Language.ARABIC:
            message = """
✏️ *تعديل مكان الإقامة*

أدخل مكان إقامتك الجديد:

📌 *مثال:* `دمشق - المزة`
"""
        else:
            message = """
✏️ *Edit Residence*

Enter your new residence:

📌 *Example:* `Damascus - Mazzeh`
"""
    elif data == "education":
        # Show education keyboard
        message = "🎓 " + ("اختر مستواك الدراسي الجديد:" if lang == Language.ARABIC else "Select your new education level:")
        keyboard = get_education_keyboard(lang)
        context.user_data['profile_edit'] = {'field': 'education_select'}
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    else:
        return False
    
    keyboard = get_cancel_keyboard(lang, f"{PROFILE_PREFIX}view")
    await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
    return True


async def handle_profile_edit_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle text input for profile editing."""
    edit_data = context.user_data.get('profile_edit')
    if not edit_data:
        return False
    
    field = edit_data.get('field')
    if not field:
        return False
    
    lang = get_user_language(context)
    text = update.message.text.strip()
    user_id = update.effective_user.id
    student = await container.student_repo.get_by_telegram_id(user_id)
    
    if not student:
        return False
    
    if field == "name":
        is_valid, value, error = validate_full_name(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        student.full_name = value
        student.updated_at = now_syria()
        await container.student_repo.save(student)
        context.user_data.pop('profile_edit', None)
        
        if lang == Language.ARABIC:
            await update.message.reply_text("✅ تم تحديث الاسم بنجاح!")
        else:
            await update.message.reply_text("✅ Name updated successfully!")
        
        # Show updated profile
        await show_student_profile(update, context, container)
        return True
    
    elif field == "phone":
        is_valid, normalized, error = validate_syrian_phone(text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error}")
            return True
        
        # Send OTP for verification
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            success, otp_message = await whatsapp_adapter.send_otp(user_id, normalized)
            if success:
                context.user_data['profile_edit'] = {
                    'field': 'phone_otp',
                    'new_phone': normalized
                }
                
                masked_phone = normalized[:4] + "****" + normalized[-3:]
                if lang == Language.ARABIC:
                    await update.message.reply_text(
                        f"📱 تم إرسال رمز التحقق إلى {masked_phone}\n\n"
                        "أدخل الرمز المكون من 6 أرقام:"
                    )
                else:
                    await update.message.reply_text(
                        f"📱 Verification code sent to {masked_phone}\n\n"
                        "Enter the 6-digit code:"
                    )
            else:
                await update.message.reply_text(f"❌ {otp_message}")
        else:
            # No WhatsApp, update directly
            student.phone_number = normalized
            student.updated_at = now_syria()
            await container.student_repo.save(student)
            context.user_data.pop('profile_edit', None)
            
            if lang == Language.ARABIC:
                await update.message.reply_text("✅ تم تحديث رقم الهاتف!")
            else:
                await update.message.reply_text("✅ Phone number updated!")
            
            await show_student_profile(update, context, container)
        return True
    
    elif field == "phone_otp":
        new_phone = edit_data.get('new_phone', '')
        if not text.isdigit() or len(text) != 6:
            if lang == Language.ARABIC:
                await update.message.reply_text("❌ الرمز يجب أن يكون 6 أرقام")
            else:
                await update.message.reply_text("❌ Code must be 6 digits")
            return True
        
        whatsapp_adapter = context.bot_data.get('whatsapp_adapter')
        if whatsapp_adapter:
            success, verify_message = whatsapp_adapter.verify_otp(user_id, text)
            if success:
                student.phone_number = new_phone
                student.updated_at = now_syria()
                await container.student_repo.save(student)
                whatsapp_adapter.clear_otp(user_id)
                context.user_data.pop('profile_edit', None)
                
                if lang == Language.ARABIC:
                    await update.message.reply_text("✅ تم تحديث رقم الهاتف والتحقق منه!")
                else:
                    await update.message.reply_text("✅ Phone number updated and verified!")
                
                await show_student_profile(update, context, container)
            else:
                await update.message.reply_text(verify_message)
        return True
    
    elif field == "residence":
        is_valid, value, error = validate_residence(text, lang)
        if not is_valid:
            await update.message.reply_text(error)
            return True
        student.residence = value
        student.updated_at = now_syria()
        await container.student_repo.save(student)
        context.user_data.pop('profile_edit', None)
        
        if lang == Language.ARABIC:
            await update.message.reply_text("✅ تم تحديث مكان الإقامة!")
        else:
            await update.message.reply_text("✅ Residence updated!")
        
        await show_student_profile(update, context, container)
        return True
    
    return False


async def handle_profile_view_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle profile view callback."""
    query = update.callback_query
    if not query or query.data != f"{PROFILE_PREFIX}view":
        return False
    
    context.user_data.pop('profile_edit', None)
    await show_student_profile(update, context, container)
    return True
