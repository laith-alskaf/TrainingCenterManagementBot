"""
Admin flow handlers for course creation and file upload with course selection.
Uses ui_components for consistent styling.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from domain.entities import Language
from domain.value_objects import parse_datetime_syria
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix,
    format_header, format_success, format_error, format_loading,
    divider, get_cancel_keyboard as ui_get_cancel_keyboard,
    get_confirm_cancel_keyboard,
)
from config import config


# Callback prefixes
ADMIN_PREFIX = CallbackPrefix.ADMIN
COURSE_CREATE_PREFIX = CallbackPrefix.COURSE_CREATE
UPLOAD_SELECT_PREFIX = CallbackPrefix.UPLOAD_SELECT


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


# ============================================================================
# Course Creation Flow Messages
# ============================================================================

COURSE_CREATION_STEPS = {
    'name': {
        'ar': """
➕ *إنشاء دورة جديدة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 *الخطوة 1 من 8: اسم الدورة*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل اسم الدورة:
(مثال: دورة البرمجة بـ Python)
""",
        'en': """
➕ *Create New Course*

━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 *Step 1 of 8: Course Name*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send the course name:
(Example: Python Programming Course)
"""
    },
    'description': {
        'ar': """
📌 *الخطوة 2 من 8: وصف الدورة*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل وصف مختصر للدورة:
(يظهر للطلاب عند عرض تفاصيل الدورة)
""",
        'en': """
📌 *Step 2 of 8: Course Description*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send a brief description:
(Shown to students when viewing course details)
"""
    },
    'instructor': {
        'ar': """
📌 *الخطوة 3 من 8: اسم المدرب*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل اسم المدرب:
""",
        'en': """
📌 *Step 3 of 8: Instructor Name*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send the instructor's name:
"""
    },
    'target_audience': {
        'ar': """
📌 *الخطوة 4 من 8: الفئة المستهدفة*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل وصف الفئة المستهدفة:
(مثال: المبتدئين في البرمجة)
""",
        'en': """
📌 *Step 4 of 8: Target Audience*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Describe the target audience:
(Example: Beginners in programming)
"""
    },
    'start_date': {
        'ar': """
📌 *الخطوة 5 من 8: تاريخ البداية*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل تاريخ بداية الدورة بالصيغة:
`YYYY-MM-DD`

(مثال: `2024-02-01`)
""",
        'en': """
📌 *Step 5 of 8: Start Date*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send the start date in format:
`YYYY-MM-DD`

(Example: `2024-02-01`)
"""
    },
    'duration': {
        'ar': """
📌 *الخطوة 6 من 8: مدة الدورة*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل مدة الدورة (بالأيام وعدد الساعات):
بالصيغة: `أيام,ساعات`

(مثال: `30,40` = 30 يوم، 40 ساعة إجمالي)
""",
        'en': """
📌 *Step 6 of 8: Duration*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send course duration (days, hours):
Format: `days,hours`

(Example: `30,40` = 30 days, 40 total hours)
"""
    },
    'max_students': {
        'ar': """
📌 *الخطوة 7 من 8: عدد المقاعد*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل الحد الأقصى لعدد الطلاب:
(رقم فقط، مثال: `25`)
""",
        'en': """
📌 *Step 7 of 8: Max Students*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send maximum number of students:
(Number only, example: `25`)
"""
    },
    'price': {
        'ar': """
📌 *الخطوة 8 من 8: السعر*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل سعر الدورة (بالدولار):
(رقم فقط، مثال: `150`)

أرسل `0` إذا كانت مجانية.
""",
        'en': """
📌 *Step 8 of 8: Price*
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send course price (in USD):
(Number only, example: `150`)

Send `0` if free.
"""
    },
}


def get_cancel_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get cancel button keyboard."""
    return ui_get_cancel_keyboard(lang, f"{ADMIN_PREFIX}panel")


def get_course_creation_summary(data: dict, lang: Language) -> str:
    """Get course creation summary for confirmation."""
    if lang == Language.ARABIC:
        return f"""
✅ *تأكيد إنشاء الدورة*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *الاسم:* {data.get('name', '-')}
📝 *الوصف:* {data.get('description', '-')[:50]}...
👨‍🏫 *المدرب:* {data.get('instructor', '-')}
🎯 *الفئة المستهدفة:* {data.get('target_audience', '-')}
📅 *تاريخ البداية:* {data.get('start_date', '-')}
⏱ *المدة:* {data.get('duration_days', '-')} يوم ({data.get('duration_hours', '-')} ساعة)
🪑 *الحد الأقصى:* {data.get('max_students', '-')} طالب
💰 *السعر:* ${data.get('price', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━

هل تريد إنشاء هذه الدورة؟
"""
    else:
        return f"""
✅ *Confirm Course Creation*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *Name:* {data.get('name', '-')}
📝 *Description:* {data.get('description', '-')[:50]}...
👨‍🏫 *Instructor:* {data.get('instructor', '-')}
🎯 *Target Audience:* {data.get('target_audience', '-')}
📅 *Start Date:* {data.get('start_date', '-')}
⏱ *Duration:* {data.get('duration_days', '-')} days ({data.get('duration_hours', '-')} hours)
🪑 *Max Students:* {data.get('max_students', '-')}
💰 *Price:* ${data.get('price', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do you want to create this course?
"""


def get_confirm_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get confirmation keyboard."""
    return get_confirm_cancel_keyboard(
        lang,
        f"{COURSE_CREATE_PREFIX}confirm",
        f"{ADMIN_PREFIX}panel"
    )


# ============================================================================
# Upload to Courses Flow
# ============================================================================

def get_upload_course_selection_message(lang: Language) -> str:
    """Get message for course selection during upload."""
    if lang == Language.ARABIC:
        return """
📤 *رفع ملف للدورات*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

اختر الدورة أو الدورات التي تريد رفع الملف إليها.
يمكنك اختيار أكثر من دورة.

✅ = محدد | ⬜ = غير محدد

بعد الانتهاء من الاختيار، اضغط "تأكيد الاختيار".
"""
    else:
        return """
📤 *Upload File to Courses*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select the course(s) to upload the file to.
You can select multiple courses.

✅ = Selected | ⬜ = Not selected

After selecting, press "Confirm Selection".
"""


def get_upload_course_keyboard(courses: list, selected_ids: set, lang: Language) -> InlineKeyboardMarkup:
    """Build course selection keyboard for upload."""
    keyboard = []
    
    for course in courses:
        is_selected = course.id in selected_ids
        prefix = "✅ " if is_selected else "⬜ "
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{course.name}",
                callback_data=f"{UPLOAD_SELECT_PREFIX}toggle_{course.id}"
            )
        ])
    
    # General files option
    general_selected = "__general__" in selected_ids
    general_prefix = "✅ " if general_selected else "⬜ "
    general_text = "ملفات عامة" if lang == Language.ARABIC else "General Files"
    keyboard.append([
        InlineKeyboardButton(
            f"{general_prefix}📁 {general_text}",
            callback_data=f"{UPLOAD_SELECT_PREFIX}toggle___general__"
        )
    ])
    
    # Confirm and cancel buttons
    keyboard.append([
        InlineKeyboardButton(
            "✅ " + ("تأكيد الاختيار" if lang == Language.ARABIC else "Confirm Selection"),
            callback_data=f"{UPLOAD_SELECT_PREFIX}confirm"
        ),
    ])
    keyboard.append([
        InlineKeyboardButton(
            "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
            callback_data=f"{ADMIN_PREFIX}panel"
        ),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_upload_file_prompt(lang: Language) -> str:
    """Get upload file prompt."""
    if lang == Language.ARABIC:
        return """
📤 *أرسل الملف الآن*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

أرسل الملف الذي تريد رفعه:
(PDF, Word, Excel, صور, فيديو...)

📌 الحد الأقصى: 50 MB
"""
    else:
        return """
📤 *Send the File Now*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

Send the file you want to upload:
(PDF, Word, Excel, images, video...)

📌 Max size: 50 MB
"""


# ============================================================================
# Course Creation Text Handler
# ============================================================================

async def handle_course_creation_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    create_course_use_case,
) -> bool:
    """
    Handle text input during course creation flow.
    Returns True if handled, False otherwise.
    """
    if not context.user_data.get('creating_course'):
        return False
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return False
    
    step = context.user_data.get('course_step', 'name')
    text = update.message.text.strip()
    
    # Validate and store based on current step
    if step == 'name':
        if len(text) < 2:
            error = "❌ الاسم قصير جداً" if lang == Language.ARABIC else "❌ Name too short"
            await update.message.reply_text(error)
            return True
        
        context.user_data['course_data'] = {'name': text}
        context.user_data['course_step'] = 'description'
        
        msg = COURSE_CREATION_STEPS['description']['ar' if lang == Language.ARABIC else 'en']
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
    
    elif step == 'description':
        if len(text) < 10:
            error = "❌ الوصف قصير جداً" if lang == Language.ARABIC else "❌ Description too short"
            await update.message.reply_text(error)
            return True
        
        context.user_data['course_data']['description'] = text
        context.user_data['course_step'] = 'instructor'
        
        msg = COURSE_CREATION_STEPS['instructor']['ar' if lang == Language.ARABIC else 'en']
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
    
    elif step == 'instructor':
        if len(text) < 2:
            error = "❌ الاسم قصير جداً" if lang == Language.ARABIC else "❌ Name too short"
            await update.message.reply_text(error)
            return True
        
        context.user_data['course_data']['instructor'] = text
        context.user_data['course_step'] = 'target_audience'
        
        msg = COURSE_CREATION_STEPS['target_audience']['ar' if lang == Language.ARABIC else 'en']
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
    
    elif step == 'target_audience':
        context.user_data['course_data']['target_audience'] = text
        context.user_data['course_step'] = 'start_date'
        
        msg = COURSE_CREATION_STEPS['start_date']['ar' if lang == Language.ARABIC else 'en']
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
    
    elif step == 'start_date':
        # Validate date format
        try:
            parse_datetime_syria(text, "09:00")
            context.user_data['course_data']['start_date'] = text
            context.user_data['course_step'] = 'duration'
            
            msg = COURSE_CREATION_STEPS['duration']['ar' if lang == Language.ARABIC else 'en']
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
        except:
            error = "❌ صيغة التاريخ غير صحيحة. استخدم: YYYY-MM-DD" if lang == Language.ARABIC else "❌ Invalid date format. Use: YYYY-MM-DD"
            await update.message.reply_text(error)
            return True
    
    elif step == 'duration':
        # Parse days,hours format
        try:
            parts = text.replace(' ', '').split(',')
            days = int(parts[0])
            hours = int(parts[1]) if len(parts) > 1 else days * 2
            
            if days < 1 or hours < 1:
                raise ValueError("Invalid values")
            
            context.user_data['course_data']['duration_days'] = days
            context.user_data['course_data']['duration_hours'] = hours
            context.user_data['course_step'] = 'max_students'
            
            msg = COURSE_CREATION_STEPS['max_students']['ar' if lang == Language.ARABIC else 'en']
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
        except:
            error = "❌ صيغة غير صحيحة. استخدم: أيام,ساعات" if lang == Language.ARABIC else "❌ Invalid format. Use: days,hours"
            await update.message.reply_text(error)
            return True
    
    elif step == 'max_students':
        try:
            max_students = int(text)
            if max_students < 1:
                raise ValueError("Invalid")
            
            context.user_data['course_data']['max_students'] = max_students
            context.user_data['course_step'] = 'price'
            
            msg = COURSE_CREATION_STEPS['price']['ar' if lang == Language.ARABIC else 'en']
            await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_cancel_keyboard(lang))
        except:
            error = "❌ أدخل رقم صحيح" if lang == Language.ARABIC else "❌ Enter a valid number"
            await update.message.reply_text(error)
            return True
    
    elif step == 'price':
        try:
            price = float(text)
            if price < 0:
                raise ValueError("Invalid")
            
            context.user_data['course_data']['price'] = price
            context.user_data['course_step'] = 'confirm'
            
            # Show summary for confirmation
            summary = get_course_creation_summary(context.user_data['course_data'], lang)
            await update.message.reply_text(
                summary,
                parse_mode='Markdown',
                reply_markup=get_confirm_keyboard(lang)
            )
        except:
            error = "❌ أدخل رقم صحيح" if lang == Language.ARABIC else "❌ Enter a valid number"
            await update.message.reply_text(error)
            return True
    
    return True


async def confirm_course_creation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    create_course_use_case,
) -> None:
    """Handle course creation confirmation."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    data = context.user_data.get('course_data', {})
    
    # Clean up user data
    context.user_data.pop('creating_course', None)
    context.user_data.pop('course_step', None)
    context.user_data.pop('course_data', None)
    
    creating_msg = "⏳ جاري إنشاء الدورة..." if lang == Language.ARABIC else "⏳ Creating course..."
    await query.edit_message_text(creating_msg)
    
    try:
        from datetime import timedelta
        
        start_date = parse_datetime_syria(data['start_date'], "09:00")
        end_date = start_date + timedelta(days=data.get('duration_days', 30))
        
        result = await create_course_use_case.execute(
            name=data['name'],
            description=data['description'],
            instructor=data['instructor'],
            start_date=start_date,
            end_date=end_date,
            price=data['price'],
            max_students=data['max_students'],
            target_audience=data.get('target_audience'),
            duration_hours=data.get('duration_hours'),
        )
        
        if result.success:
            if lang == Language.ARABIC:
                message = f"""
✅ *تم إنشاء الدورة بنجاح!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *{result.course.name}*

تم إنشاء مجلد Google Drive للمواد التعليمية.

اضغط /start للعودة.
"""
            else:
                message = f"""
✅ *Course Created Successfully!*

━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 *{result.course.name}*

A Google Drive folder was created for materials.

Press /start to return.
"""
        else:
            if lang == Language.ARABIC:
                message = f"❌ فشل إنشاء الدورة: {result.error}"
            else:
                message = f"❌ Failed to create course: {result.error}"
        
        await query.edit_message_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error = f"❌ خطأ: {e}" if lang == Language.ARABIC else f"❌ Error: {e}"
        await query.edit_message_text(error)


# ============================================================================
# Upload Course Selection Handlers
# ============================================================================

async def handle_upload_course_toggle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    get_courses_use_case,
) -> None:
    """Handle toggling course selection for upload."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    course_id = query.data.replace(f"{UPLOAD_SELECT_PREFIX}toggle_", "")
    
    # Get or initialize selected courses set
    selected = context.user_data.get('upload_selected_courses', set())
    
    # Toggle
    if course_id in selected:
        selected.discard(course_id)
    else:
        selected.add(course_id)
    
    context.user_data['upload_selected_courses'] = selected
    
    # Refresh keyboard
    courses = await get_courses_use_case.execute(available_only=False)
    keyboard = get_upload_course_keyboard(courses, selected, lang)
    message = get_upload_course_selection_message(lang)
    
    selected_count = len(selected)
    count_text = f"\n\n✅ {selected_count} " + ("محدد" if lang == Language.ARABIC else "selected")
    
    await query.edit_message_text(message + count_text, reply_markup=keyboard, parse_mode='Markdown')


async def handle_upload_confirm_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle confirmation of course selection for upload."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    selected = context.user_data.get('upload_selected_courses', set())
    
    if not selected:
        error = "❌ اختر دورة واحدة على الأقل" if lang == Language.ARABIC else "❌ Select at least one course"
        await query.answer(error, show_alert=True)
        return
    
    # Store selection and ask for file
    context.user_data['awaiting_course_file'] = True
    
    message = get_upload_file_prompt(lang)
    cancel_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
            callback_data=f"{ADMIN_PREFIX}panel"
        )
    ]])
    
    await query.edit_message_text(message, reply_markup=cancel_keyboard, parse_mode='Markdown')


async def handle_course_file_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    upload_to_courses_use_case,
    upload_file_use_case,
) -> bool:
    """
    Handle file upload after course selection.
    Returns True if handled.
    """
    if not context.user_data.get('awaiting_course_file'):
        return False
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return False
    
    lang = get_user_language(context)
    
    if not update.message.document:
        error = "❌ يرجى إرسال ملف" if lang == Language.ARABIC else "❌ Please send a file"
        await update.message.reply_text(error)
        return True
    
    context.user_data['awaiting_course_file'] = False
    selected = context.user_data.get('upload_selected_courses', set())
    context.user_data.pop('upload_selected_courses', None)
    
    uploading = "📤 جاري الرفع..." if lang == Language.ARABIC else "📤 Uploading..."
    await update.message.reply_text(uploading)
    
    # Download file
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Check if general files or specific courses
    if "__general__" in selected and len(selected) == 1:
        # Upload to general folder
        result = await upload_file_use_case.execute(
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
            message = f"❌ {result.error}"
    else:
        # Upload to course folders
        course_ids = [cid for cid in selected if cid != "__general__"]
        
        result = await upload_to_courses_use_case.execute(
            file_bytes=bytes(file_bytes),
            file_name=doc.file_name or "uploaded_file",
            mime_type=doc.mime_type or "application/octet-stream",
            course_ids=course_ids,
        )
        
        if result.success:
            if lang == Language.ARABIC:
                message = f"✅ تم الرفع إلى {len(result.links)} دورة بنجاح!"
            else:
                message = f"✅ Uploaded to {len(result.links)} course(s) successfully!"
            
            if result.error:
                message += f"\n\n⚠️ {result.error}"
        else:
            message = f"❌ {result.error}"
    
    message += "\n\n" + ("اضغط /start للعودة" if lang == Language.ARABIC else "Press /start to return")
    await update.message.reply_text(message, disable_web_page_preview=True)
    
    return True
