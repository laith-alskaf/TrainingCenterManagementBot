"""
Admin course management handler.
View, edit, and manage courses and their files.
"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional, List
from datetime import datetime

from domain.entities import Language, Course, CourseStatus
from domain.value_objects import now_syria
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix, divider,
    format_success, format_error,
    get_back_and_home_keyboard,
)
from config import config


# Callback prefix
COURSE_MGR_PREFIX = "cmgr_"


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


def get_status_emoji(status: CourseStatus) -> str:
    """Get emoji for course status."""
    return {
        CourseStatus.DRAFT: "📝",
        CourseStatus.PUBLISHED: "✅",
        CourseStatus.ONGOING: "🔵",
        CourseStatus.COMPLETED: "✔️",
        CourseStatus.CANCELLED: "❌",
    }.get(status, "📋")


def get_status_label(status: CourseStatus, lang: Language) -> str:
    """Get label for course status."""
    if lang == Language.ARABIC:
        return {
            CourseStatus.DRAFT: "مسودة",
            CourseStatus.PUBLISHED: "منشور",
            CourseStatus.ONGOING: "جاري",
            CourseStatus.COMPLETED: "مكتمل",
            CourseStatus.CANCELLED: "ملغي",
        }.get(status, "غير معروف")
    else:
        return {
            CourseStatus.DRAFT: "Draft",
            CourseStatus.PUBLISHED: "Published",
            CourseStatus.ONGOING: "Ongoing",
            CourseStatus.COMPLETED: "Completed",
            CourseStatus.CANCELLED: "Cancelled",
        }.get(status, "Unknown")


def format_course_card(course: Course, lang: Language, detailed: bool = False) -> str:
    """Format course information card."""
    status_emoji = get_status_emoji(course.status)
    status_label = get_status_label(course.status, lang)
    
    start_date = course.start_date.strftime("%Y-%m-%d") if course.start_date else "N/A"
    end_date = course.end_date.strftime("%Y-%m-%d") if course.end_date else "N/A"
    
    if lang == Language.ARABIC:
        card = f"""
📚 *{course.name}*
{divider()}

{status_emoji} *الحالة:* {status_label}
👨‍🏫 *المدرب:* {course.instructor}
💰 *السعر:* ${course.price}
👥 *السعة:* {course.max_students} طالب
📅 *البداية:* {start_date}
📅 *النهاية:* {end_date}"""
        
        if detailed:
            card += f"""

📝 *الوصف:*
{course.description[:200]}{'...' if len(course.description) > 200 else ''}"""
            
            if course.target_audience:
                card += f"\n\n🎯 *الفئة المستهدفة:* {course.target_audience}"
            
            if course.duration_hours:
                card += f"\n⏱️ *المدة:* {course.duration_hours} ساعة"
            
            if course.materials_folder_id:
                card += f"\n\n📁 *مجلد المواد:* [رابط](https://drive.google.com/drive/folders/{course.materials_folder_id})"
    else:
        card = f"""
📚 *{course.name}*
{divider()}

{status_emoji} *Status:* {status_label}
👨‍🏫 *Instructor:* {course.instructor}
💰 *Price:* ${course.price}
👥 *Capacity:* {course.max_students} students
📅 *Start:* {start_date}
📅 *End:* {end_date}"""
        
        if detailed:
            card += f"""

📝 *Description:*
{course.description[:200]}{'...' if len(course.description) > 200 else ''}"""
            
            if course.target_audience:
                card += f"\n\n🎯 *Target Audience:* {course.target_audience}"
            
            if course.duration_hours:
                card += f"\n⏱️ *Duration:* {course.duration_hours} hours"
            
            if course.materials_folder_id:
                card += f"\n\n📁 *Materials Folder:* [Link](https://drive.google.com/drive/folders/{course.materials_folder_id})"
    
    return card


# ═══════════════════════════════════════════════════════════════════
# COURSE LIST & VIEW
# ═══════════════════════════════════════════════════════════════════

async def show_course_management_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> None:
    """Show course management menu with all courses."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    courses = await container.get_courses.execute(available_only=False)
    
    if lang == Language.ARABIC:
        message = f"""
📚 *إدارة الدورات*
{divider()}

عدد الدورات: {len(courses)}

اختر دورة لإدارتها:
"""
    else:
        message = f"""
📚 *Course Management*
{divider()}

Total courses: {len(courses)}

Select a course to manage:
"""
    
    builder = KeyboardBuilder()
    
    for course in courses:
        status_emoji = get_status_emoji(course.status)
        label = f"{status_emoji} {course.name[:25]}"
        builder.add_button_row(label, f"{COURSE_MGR_PREFIX}view_{course.id}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{CallbackPrefix.ADMIN}panel"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_course_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show detailed course information with management options."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    
    if not course:
        if lang == Language.ARABIC:
            message = "❌ الدورة غير موجودة"
        else:
            message = "❌ Course not found"
        keyboard = get_back_and_home_keyboard(lang, f"{COURSE_MGR_PREFIX}list")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    message = format_course_card(course, lang, detailed=True)
    
    builder = KeyboardBuilder()
    
    # Edit options
    builder.add_button_row(
        f"✏️ " + ("تعديل الدورة" if lang == Language.ARABIC else "Edit Course"),
        f"{COURSE_MGR_PREFIX}edit_{course_id}"
    )
    
    # File management
    builder.add_button_row(
        f"📁 " + ("إدارة الملفات" if lang == Language.ARABIC else "Manage Files"),
        f"{COURSE_MGR_PREFIX}files_{course_id}"
    )
    
    # Change status
    builder.add_button_row(
        f"🔄 " + ("تغيير الحالة" if lang == Language.ARABIC else "Change Status"),
        f"{COURSE_MGR_PREFIX}status_{course_id}"
    )
    
    # View students
    builder.add_button_row(
        f"👥 " + ("عرض الطلاب" if lang == Language.ARABIC else "View Students"),
        f"stdview_course_{course_id}"
    )
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{COURSE_MGR_PREFIX}list"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


# ═══════════════════════════════════════════════════════════════════
# COURSE EDIT
# ═══════════════════════════════════════════════════════════════════

async def show_edit_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show course edit options."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    if lang == Language.ARABIC:
        message = f"""
✏️ *تعديل: {course.name}*
{divider()}

اختر ما تريد تعديله:
"""
    else:
        message = f"""
✏️ *Edit: {course.name}*
{divider()}

Select what to edit:
"""
    
    builder = KeyboardBuilder()
    
    # Edit fields
    fields = [
        ("📝", "الاسم" if lang == Language.ARABIC else "Name", "name"),
        ("📄", "الوصف" if lang == Language.ARABIC else "Description", "description"),
        ("👨‍🏫", "المدرب" if lang == Language.ARABIC else "Instructor", "instructor"),
        ("💰", "السعر" if lang == Language.ARABIC else "Price", "price"),
        ("👥", "السعة" if lang == Language.ARABIC else "Capacity", "capacity"),
        ("📅", "تاريخ البداية" if lang == Language.ARABIC else "Start Date", "start_date"),
        ("📅", "تاريخ النهاية" if lang == Language.ARABIC else "End Date", "end_date"),
    ]
    
    for emoji, label, field in fields:
        builder.add_button_row(f"{emoji} {label}", f"{COURSE_MGR_PREFIX}ef_{course_id}_{field}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{COURSE_MGR_PREFIX}view_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def prompt_edit_field(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
    field: str,
) -> None:
    """Prompt for new field value."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    # Store edit state
    context.user_data['course_edit'] = {
        'course_id': course_id,
        'field': field,
    }
    
    field_info = {
        'name': ("الاسم" if lang == Language.ARABIC else "Name", course.name, "دورة البرمجة" if lang == Language.ARABIC else "Programming Course"),
        'description': ("الوصف" if lang == Language.ARABIC else "Description", course.description[:100], "تعلم أساسيات البرمجة" if lang == Language.ARABIC else "Learn programming basics"),
        'instructor': ("المدرب" if lang == Language.ARABIC else "Instructor", course.instructor, "أحمد محمد" if lang == Language.ARABIC else "Ahmed Mohammed"),
        'price': ("السعر" if lang == Language.ARABIC else "Price", str(course.price), "200"),
        'capacity': ("السعة" if lang == Language.ARABIC else "Capacity", str(course.max_students), "20"),
        'start_date': ("تاريخ البداية" if lang == Language.ARABIC else "Start Date", course.start_date.strftime("%Y-%m-%d") if course.start_date else "N/A", "2024-02-01"),
        'end_date': ("تاريخ النهاية" if lang == Language.ARABIC else "End Date", course.end_date.strftime("%Y-%m-%d") if course.end_date else "N/A", "2024-03-01"),
    }
    
    label, current, example = field_info.get(field, ("", "", ""))
    
    if lang == Language.ARABIC:
        message = f"""
✏️ *تعديل {label}*
{divider()}

📍 *القيمة الحالية:* 
`{current}`

✏️ أدخل القيمة الجديدة:

📌 *مثال:* `{example}`
"""
    else:
        message = f"""
✏️ *Edit {label}*
{divider()}

📍 *Current Value:* 
`{current}`

✏️ Enter new value:

📌 *Example:* `{example}`
"""
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{COURSE_MGR_PREFIX}edit_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def handle_edit_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle course edit text input."""
    edit_state = context.user_data.get('course_edit')
    if not edit_state:
        return False
    
    lang = get_user_language(context)
    course_id = edit_state.get('course_id')
    field = edit_state.get('field')
    text = update.message.text.strip()
    
    # Clear state
    context.user_data.pop('course_edit', None)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        await update.message.reply_text("❌ Course not found")
        return True
    
    # Update field
    try:
        if field == 'name':
            course.name = text
        elif field == 'description':
            course.description = text
        elif field == 'instructor':
            course.instructor = text
        elif field == 'price':
            course.price = float(text)
        elif field == 'capacity':
            course.max_students = int(text)
        elif field == 'start_date':
            from domain.value_objects import parse_date_syria
            course.start_date = parse_date_syria(text)
        elif field == 'end_date':
            from domain.value_objects import parse_date_syria
            course.end_date = parse_date_syria(text)
        
        course.updated_at = now_syria()
        await container.course_repo.save(course)
        
        if lang == Language.ARABIC:
            message = f"✅ تم تحديث الدورة بنجاح!"
        else:
            message = f"✅ Course updated successfully!"
        
    except ValueError as e:
        if lang == Language.ARABIC:
            message = f"❌ قيمة غير صالحة: {e}"
        else:
            message = f"❌ Invalid value: {e}"
    except Exception as e:
        if lang == Language.ARABIC:
            message = f"❌ خطأ: {e}"
        else:
            message = f"❌ Error: {e}"
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"📚 " + ("عرض الدورة" if lang == Language.ARABIC else "View Course"),
        f"{COURSE_MGR_PREFIX}view_{course_id}"
    )
    
    await update.message.reply_text(message, reply_markup=builder.build())
    return True


# ═══════════════════════════════════════════════════════════════════
# STATUS CHANGE
# ═══════════════════════════════════════════════════════════════════

async def show_status_options(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show status change options."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    current_status = get_status_label(course.status, lang)
    
    if lang == Language.ARABIC:
        message = f"""
🔄 *تغيير حالة الدورة*
{divider()}

📚 *الدورة:* {course.name}
📍 *الحالة الحالية:* {current_status}

اختر الحالة الجديدة:
"""
    else:
        message = f"""
🔄 *Change Course Status*
{divider()}

📚 *Course:* {course.name}
📍 *Current Status:* {current_status}

Select new status:
"""
    
    builder = KeyboardBuilder()
    
    statuses = [
        (CourseStatus.DRAFT, "📝", "مسودة" if lang == Language.ARABIC else "Draft"),
        (CourseStatus.PUBLISHED, "✅", "منشور" if lang == Language.ARABIC else "Published"),
        (CourseStatus.ONGOING, "🔵", "جاري" if lang == Language.ARABIC else "Ongoing"),
        (CourseStatus.COMPLETED, "✔️", "مكتمل" if lang == Language.ARABIC else "Completed"),
        (CourseStatus.CANCELLED, "❌", "ملغي" if lang == Language.ARABIC else "Cancelled"),
    ]
    
    for status, emoji, label in statuses:
        if status != course.status:
            builder.add_button_row(f"{emoji} {label}", f"{COURSE_MGR_PREFIX}st_{course_id}_{status.value}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{COURSE_MGR_PREFIX}view_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def change_course_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
    new_status: str,
) -> None:
    """Change course status."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    course.status = CourseStatus(new_status)
    course.updated_at = now_syria()
    await container.course_repo.save(course)
    
    status_label = get_status_label(course.status, lang)
    
    if lang == Language.ARABIC:
        message = f"✅ تم تغيير الحالة إلى: {status_label}"
    else:
        message = f"✅ Status changed to: {status_label}"
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"📚 " + ("عرض الدورة" if lang == Language.ARABIC else "View Course"),
        f"{COURSE_MGR_PREFIX}view_{course_id}"
    )
    
    await query.edit_message_text(message, reply_markup=builder.build())


# ═══════════════════════════════════════════════════════════════════
# FILE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

async def show_course_files(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show course files with management options."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    # Get files from Google Drive
    files = []
    if course.materials_folder_id:
        try:
            files = await container.drive_adapter.list_files(course.materials_folder_id)
        except Exception as e:
            files = []
    
    if lang == Language.ARABIC:
        message = f"""
📁 *ملفات: {course.name}*
{divider()}

عدد الملفات: {len(files)}
"""
        if files:
            message += "\n📄 *الملفات:*\n"
            for i, f in enumerate(files[:10], 1):
                message += f"\n{i}. [{f['name']}]({f.get('webViewLink', '#')})"
    else:
        message = f"""
📁 *Files: {course.name}*
{divider()}

Total files: {len(files)}
"""
        if files:
            message += "\n📄 *Files:*\n"
            for i, f in enumerate(files[:10], 1):
                message += f"\n{i}. [{f['name']}]({f.get('webViewLink', '#')})"
    
    builder = KeyboardBuilder()
    
    # Upload new file
    builder.add_button_row(
        f"📤 " + ("رفع ملف" if lang == Language.ARABIC else "Upload File"),
        f"{COURSE_MGR_PREFIX}upload_{course_id}"
    )
    
    # Delete files
    if files:
        builder.add_button_row(
            f"🗑️ " + ("حذف ملف" if lang == Language.ARABIC else "Delete File"),
            f"{COURSE_MGR_PREFIX}delfiles_{course_id}"
        )
    
    # Open Drive folder
    if course.materials_folder_id:
        # We can't add external links in buttons, but we already showed the link in message
        pass
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{COURSE_MGR_PREFIX}view_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build(), disable_web_page_preview=True)


async def prompt_upload_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Prompt user to upload a file."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        return
    
    # Store upload state
    context.user_data['file_upload'] = {
        'course_id': course_id,
        'course_name': course.name,
        'folder_id': course.materials_folder_id,
    }
    
    if lang == Language.ARABIC:
        message = f"""
📤 *رفع ملف إلى: {course.name}*
{divider()}

أرسل الملف الآن (PDF, صورة, فيديو, أو أي ملف آخر)

⚠️ أو اضغط إلغاء للرجوع
"""
    else:
        message = f"""
📤 *Upload file to: {course.name}*
{divider()}

Send the file now (PDF, image, video, or any other file)

⚠️ Or click Cancel to go back
"""
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{COURSE_MGR_PREFIX}files_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_delete_files_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show files for deletion."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    course = await container.course_repo.get_by_id(course_id)
    if not course or not course.materials_folder_id:
        return
    
    files = await container.drive_adapter.list_files(course.materials_folder_id)
    
    if not files:
        if lang == Language.ARABIC:
            message = "❌ لا توجد ملفات للحذف"
        else:
            message = "❌ No files to delete"
        keyboard = get_back_and_home_keyboard(lang, f"{COURSE_MGR_PREFIX}files_{course_id}")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    if lang == Language.ARABIC:
        message = f"""
🗑️ *حذف ملف من: {course.name}*
{divider()}

اختر الملف المراد حذفه:
"""
    else:
        message = f"""
🗑️ *Delete file from: {course.name}*
{divider()}

Select file to delete:
"""
    
    builder = KeyboardBuilder()
    
    for f in files[:10]:
        builder.add_button_row(f"🗑️ {f['name'][:30]}", f"{COURSE_MGR_PREFIX}delf_{course_id}_{f['id']}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{COURSE_MGR_PREFIX}files_{course_id}"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def delete_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
    file_id: str,
) -> None:
    """Delete a file from course."""
    query = update.callback_query
    await query.answer()
    
    lang = get_user_language(context)
    
    try:
        # Delete from Google Drive
        service = container.drive_adapter._get_service()
        service.files().delete(fileId=file_id).execute()
        
        if lang == Language.ARABIC:
            message = "✅ تم حذف الملف بنجاح!"
        else:
            message = "✅ File deleted successfully!"
    except Exception as e:
        if lang == Language.ARABIC:
            message = f"❌ خطأ في الحذف: {e}"
        else:
            message = f"❌ Delete error: {e}"
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"📁 " + ("الملفات" if lang == Language.ARABIC else "Files"),
        f"{COURSE_MGR_PREFIX}files_{course_id}"
    )
    
    await query.edit_message_text(message, reply_markup=builder.build())


# ═══════════════════════════════════════════════════════════════════
# MAIN CALLBACK HANDLER
# ═══════════════════════════════════════════════════════════════════

async def handle_course_manager_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for course management."""
    query = update.callback_query
    if not query or not query.data.startswith(COURSE_MGR_PREFIX):
        return False
    
    data = query.data[len(COURSE_MGR_PREFIX):]
    
    # List courses
    if data == "list":
        await show_course_management_menu(update, context, container)
        return True
    
    # View course
    elif data.startswith("view_"):
        course_id = data.replace("view_", "")
        await show_course_details(update, context, container, course_id)
        return True
    
    # Edit menu
    elif data.startswith("edit_"):
        course_id = data.replace("edit_", "")
        await show_edit_menu(update, context, container, course_id)
        return True
    
    # Edit field
    elif data.startswith("ef_"):
        parts = data.replace("ef_", "").split("_", 1)
        if len(parts) == 2:
            course_id, field = parts
            await prompt_edit_field(update, context, container, course_id, field)
        return True
    
    # Status menu
    elif data.startswith("status_"):
        course_id = data.replace("status_", "")
        await show_status_options(update, context, container, course_id)
        return True
    
    # Change status
    elif data.startswith("st_"):
        parts = data.replace("st_", "").split("_", 1)
        if len(parts) == 2:
            course_id, status = parts
            await change_course_status(update, context, container, course_id, status)
        return True
    
    # Files menu
    elif data.startswith("files_"):
        course_id = data.replace("files_", "")
        await show_course_files(update, context, container, course_id)
        return True
    
    # Upload prompt
    elif data.startswith("upload_"):
        course_id = data.replace("upload_", "")
        await prompt_upload_file(update, context, container, course_id)
        return True
    
    # Delete files menu
    elif data.startswith("delfiles_"):
        course_id = data.replace("delfiles_", "")
        await show_delete_files_menu(update, context, container, course_id)
        return True
    
    # Delete file
    elif data.startswith("delf_"):
        parts = data.replace("delf_", "").split("_", 1)
        if len(parts) == 2:
            course_id, file_id = parts
            await delete_file(update, context, container, course_id, file_id)
        return True
    
    return False
