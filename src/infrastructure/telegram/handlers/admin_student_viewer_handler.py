"""
Admin student viewer handler.
View, search, and manage student information.
"""
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import List, Optional

from domain.entities import Language, Gender, EducationLevel, Student, RegistrationStatus, PaymentStatus
from infrastructure.telegram.handlers.base import get_user_language
from infrastructure.telegram.handlers.ui_components import (
    KeyboardBuilder, Emoji, CallbackPrefix, divider,
    format_success, format_error,
    get_back_and_home_keyboard,
)
from config import config


# Callback prefix
STUDENT_VIEWER_PREFIX = "stdview_"


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return config.telegram.is_admin(user_id)


def get_gender_label(gender: Gender, lang: Language) -> str:
    """Get gender label."""
    if lang == Language.ARABIC:
        return "ذكر" if gender == Gender.MALE else "أنثى"
    return "Male" if gender == Gender.MALE else "Female"


def get_education_label(edu: EducationLevel, lang: Language) -> str:
    """Get education level label."""
    labels = {
        EducationLevel.MIDDLE_SCHOOL: ("إعدادي", "Middle School"),
        EducationLevel.HIGH_SCHOOL: ("ثانوي", "High School"),
        EducationLevel.DIPLOMA: ("معهد", "Diploma"),
        EducationLevel.BACHELOR: ("بكالوريوس", "Bachelor"),
        EducationLevel.MASTER: ("ماجستير", "Master"),
        EducationLevel.PHD: ("دكتوراه", "PhD"),
        EducationLevel.OTHER: ("أخرى", "Other"),
    }
    ar, en = labels.get(edu, ("أخرى", "Other"))
    return ar if lang == Language.ARABIC else en


def get_payment_status_label(status: PaymentStatus, lang: Language) -> str:
    """Get payment status label."""
    if lang == Language.ARABIC:
        labels = {
            PaymentStatus.UNPAID: "🔴 لم يدفع",
            PaymentStatus.PARTIAL: "🟡 دفع جزئي",
            PaymentStatus.PAID: "🟢 دفع كامل",
        }
    else:
        labels = {
            PaymentStatus.UNPAID: "🔴 Unpaid",
            PaymentStatus.PARTIAL: "🟡 Partial",
            PaymentStatus.PAID: "🟢 Paid",
        }
    return labels.get(status, "Unknown")


def get_registration_status_label(status: RegistrationStatus, lang: Language) -> str:
    """Get registration status label."""
    if lang == Language.ARABIC:
        labels = {
            RegistrationStatus.PENDING: "⏳ معلق",
            RegistrationStatus.APPROVED: "✅ مقبول",
            RegistrationStatus.REJECTED: "❌ مرفوض",
            RegistrationStatus.CANCELLED: "🚫 ملغي",
        }
    else:
        labels = {
            RegistrationStatus.PENDING: "⏳ Pending",
            RegistrationStatus.APPROVED: "✅ Approved",
            RegistrationStatus.REJECTED: "❌ Rejected",
            RegistrationStatus.CANCELLED: "🚫 Cancelled",
        }
    return labels.get(status, "Unknown")


def format_student_card(
    student: Student,
    lang: Language,
    registrations: List = None,
    show_full: bool = False,
) -> str:
    """Format student information card."""
    gender_label = get_gender_label(student.gender, lang)
    edu_label = get_education_label(student.education_level, lang)
    
    spec_line = ""
    if student.specialization:
        if lang == Language.ARABIC:
            spec_line = f"📚 *الاختصاص:* {student.specialization}\n"
        else:
            spec_line = f"📚 *Specialization:* {student.specialization}\n"
    
    if lang == Language.ARABIC:
        card = f"""
👤 *معلومات الطالب*
{divider()}

👤 *الاسم:* {student.full_name}
📱 *الهاتف:* {student.phone_number}
👤 *الجنس:* {gender_label}
🎂 *العمر:* {student.age} سنة
🏠 *الإقامة:* {student.residence}
🎓 *التحصيل:* {edu_label}
{spec_line}"""
    else:
        card = f"""
👤 *Student Information*
{divider()}

👤 *Name:* {student.full_name}
📱 *Phone:* {student.phone_number}
👤 *Gender:* {gender_label}
🎂 *Age:* {student.age} years
🏠 *Residence:* {student.residence}
🎓 *Education:* {edu_label}
{spec_line}"""
    
    # Add registrations if available
    if registrations and show_full:
        if lang == Language.ARABIC:
            card += f"\n{divider()}\n📚 *الدورات المسجلة:*\n"
            for reg in registrations:
                course_name = reg.get('course_name', 'غير معروف')
                status = get_registration_status_label(reg.get('status', RegistrationStatus.PENDING), lang)
                payment = get_payment_status_label(reg.get('payment_status', PaymentStatus.UNPAID), lang)
                card += f"\n• *{course_name}*\n  الحالة: {status}\n  الدفع: {payment}\n"
        else:
            card += f"\n{divider()}\n📚 *Registered Courses:*\n"
            for reg in registrations:
                course_name = reg.get('course_name', 'Unknown')
                status = get_registration_status_label(reg.get('status', RegistrationStatus.PENDING), lang)
                payment = get_payment_status_label(reg.get('payment_status', PaymentStatus.UNPAID), lang)
                card += f"\n• *{course_name}*\n  Status: {status}\n  Payment: {payment}\n"
    
    return card


async def show_student_management_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show student management menu."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    if lang == Language.ARABIC:
        message = f"""
👥 *إدارة الطلاب*
{divider()}

اختر إجراءً:
"""
    else:
        message = f"""
👥 *Student Management*
{divider()}

Select an action:
"""
    
    builder = KeyboardBuilder()
    
    builder.add_button_row(
        f"📋 " + ("جميع الطلاب" if lang == Language.ARABIC else "All Students"),
        f"{STUDENT_VIEWER_PREFIX}all"
    )
    
    builder.add_button_row(
        f"🔍 " + ("بحث بالاسم" if lang == Language.ARABIC else "Search by Name"),
        f"{STUDENT_VIEWER_PREFIX}search_name"
    )
    
    builder.add_button_row(
        f"📱 " + ("بحث بالهاتف" if lang == Language.ARABIC else "Search by Phone"),
        f"{STUDENT_VIEWER_PREFIX}search_phone"
    )
    
    builder.add_button_row(
        f"📚 " + ("طلاب دورة معينة" if lang == Language.ARABIC else "Course Students"),
        f"{STUDENT_VIEWER_PREFIX}by_course"
    )
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{CallbackPrefix.ADMIN}panel"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_all_students(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    page: int = 0,
) -> None:
    """Show all students with pagination."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    students = await container.student_repo.get_with_complete_profile()
    
    if not students:
        if lang == Language.ARABIC:
            message = "❌ لا يوجد طلاب مسجلين"
        else:
            message = "❌ No registered students"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}menu")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # Pagination
    page_size = 10
    total_pages = (len(students) + page_size - 1) // page_size
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(students))
    page_students = students[start_idx:end_idx]
    
    # Store students in context
    context.user_data['viewer_students'] = students
    
    if lang == Language.ARABIC:
        message = f"""
📋 *جميع الطلاب* ({len(students)} طالب)
{divider()}

صفحة {page + 1} من {total_pages}

اختر طالباً لعرض معلوماته:
"""
    else:
        message = f"""
📋 *All Students* ({len(students)} students)
{divider()}

Page {page + 1} of {total_pages}

Select a student to view details:
"""
    
    builder = KeyboardBuilder()
    
    for student in page_students:
        label = f"👤 {student.full_name[:25]}"
        builder.add_button_row(label, f"{STUDENT_VIEWER_PREFIX}view_{student.id}")
    
    # Navigation
    nav_buttons = []
    if page > 0:
        nav_buttons.append((f"◀️ " + ("السابق" if lang == Language.ARABIC else "Prev"), f"{STUDENT_VIEWER_PREFIX}page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append((f"▶️ " + ("التالي" if lang == Language.ARABIC else "Next"), f"{STUDENT_VIEWER_PREFIX}page_{page + 1}"))
    
    for label, callback in nav_buttons:
        builder.add_button(label, callback)
    if nav_buttons:
        builder.add_row()
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{STUDENT_VIEWER_PREFIX}menu"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())
    else:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_student_details(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    student_id: str,
) -> None:
    """Show detailed student information with registrations."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    student = await container.student_repo.get_by_id(student_id)
    
    if not student:
        if lang == Language.ARABIC:
            message = "❌ لم يتم العثور على الطالب"
        else:
            message = "❌ Student not found"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}menu")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # Get registrations
    registrations_data = []
    registrations = await container.registration_repo.get_by_student(student_id)
    
    for reg in registrations:
        course = await container.course_repo.get_by_id(reg.course_id)
        registrations_data.append({
            'course_name': course.name if course else 'Unknown',
            'status': reg.status,
            'payment_status': reg.payment_status,
        })
    
    message = format_student_card(student, lang, registrations_data, show_full=True)
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{STUDENT_VIEWER_PREFIX}all"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def prompt_search_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Prompt admin to enter name for search."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    context.user_data['student_search'] = {'type': 'name'}
    
    if lang == Language.ARABIC:
        message = f"""
🔍 *البحث عن طالب بالاسم*
{divider()}

أدخل اسم الطالب أو جزء منه:

📌 *مثال:* `أحمد` أو `محمد العلي`
"""
    else:
        message = f"""
🔍 *Search Student by Name*
{divider()}

Enter the student name or part of it:

📌 *Example:* `Ahmed` or `Mohammed Ali`
"""
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{STUDENT_VIEWER_PREFIX}menu"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def prompt_search_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Prompt admin to enter phone for search."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    context.user_data['student_search'] = {'type': 'phone'}
    
    if lang == Language.ARABIC:
        message = f"""
🔍 *البحث عن طالب بالهاتف*
{divider()}

أدخل رقم الهاتف أو جزء منه:

📌 *مثال:* `0991234567` أو `991`
"""
    else:
        message = f"""
🔍 *Search Student by Phone*
{divider()}

Enter the phone number or part of it:

📌 *Example:* `0991234567` or `991`
"""
    
    builder = KeyboardBuilder()
    builder.add_button_row(
        f"❌ " + ("إلغاء" if lang == Language.ARABIC else "Cancel"),
        f"{STUDENT_VIEWER_PREFIX}menu"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def handle_search_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Handle search text input."""
    search = context.user_data.get('student_search')
    if not search:
        return False
    
    lang = get_user_language(context)
    search_type = search.get('type')
    text = update.message.text.strip()
    
    # Clear search state
    context.user_data.pop('student_search', None)
    
    if search_type == 'name':
        students = await container.student_repo.search_by_name(text)
    elif search_type == 'phone':
        students = await container.student_repo.search_by_phone(text)
    else:
        return False
    
    if not students:
        if lang == Language.ARABIC:
            message = f"❌ لم يتم العثور على نتائج لـ: `{text}`"
        else:
            message = f"❌ No results found for: `{text}`"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}menu")
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        return True
    
    # Store results
    context.user_data['viewer_students'] = students
    
    if lang == Language.ARABIC:
        message = f"""
🔍 *نتائج البحث* ({len(students)} طالب)
{divider()}

اختر طالباً لعرض معلوماته:
"""
    else:
        message = f"""
🔍 *Search Results* ({len(students)} students)
{divider()}

Select a student to view details:
"""
    
    builder = KeyboardBuilder()
    for student in students[:10]:  # Limit to 10
        label = f"👤 {student.full_name[:25]}"
        builder.add_button_row(label, f"{STUDENT_VIEWER_PREFIX}view_{student.id}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{STUDENT_VIEWER_PREFIX}menu"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=builder.build())
    return True


async def show_course_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> None:
    """Show course selection for viewing students."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    courses = await container.get_courses.execute(available_only=False)
    
    if not courses:
        if lang == Language.ARABIC:
            message = "❌ لا توجد دورات"
        else:
            message = "❌ No courses"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}menu")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    if lang == Language.ARABIC:
        message = f"""
📚 *اختر دورة لعرض طلابها:*
{divider()}
"""
    else:
        message = f"""
📚 *Select course to view students:*
{divider()}
"""
    
    builder = KeyboardBuilder()
    for course in courses:
        builder.add_button_row(f"📚 {course.name[:30]}", f"{STUDENT_VIEWER_PREFIX}course_{course.id}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{STUDENT_VIEWER_PREFIX}menu"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def show_course_students(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
    course_id: str,
) -> None:
    """Show students of a specific course."""
    query = update.callback_query
    if query:
        await query.answer()
    
    lang = get_user_language(context)
    
    # Get course
    course = await container.course_repo.get_by_id(course_id)
    if not course:
        if lang == Language.ARABIC:
            message = "❌ الدورة غير موجودة"
        else:
            message = "❌ Course not found"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}menu")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # Get registrations
    registrations = await container.registration_repo.get_by_course(course_id)
    
    if not registrations:
        if lang == Language.ARABIC:
            message = f"❌ لا يوجد طلاب مسجلين في: {course.name}"
        else:
            message = f"❌ No students registered in: {course.name}"
        keyboard = get_back_and_home_keyboard(lang, f"{STUDENT_VIEWER_PREFIX}by_course")
        if query:
            await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # Get students
    students = []
    for reg in registrations:
        student = await container.student_repo.get_by_id(reg.student_id)
        if student:
            students.append(student)
    
    context.user_data['viewer_students'] = students
    
    if lang == Language.ARABIC:
        message = f"""
📚 *طلاب: {course.name}*
{divider()}

عدد الطلاب: {len(students)}

اختر طالباً لعرض معلوماته:
"""
    else:
        message = f"""
📚 *Students: {course.name}*
{divider()}

Number of students: {len(students)}

Select a student to view details:
"""
    
    builder = KeyboardBuilder()
    for student in students[:15]:
        builder.add_button_row(f"👤 {student.full_name[:25]}", f"{STUDENT_VIEWER_PREFIX}view_{student.id}")
    
    builder.add_button_row(
        f"🔙 " + ("رجوع" if lang == Language.ARABIC else "Back"),
        f"{STUDENT_VIEWER_PREFIX}by_course"
    )
    
    if query:
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=builder.build())


async def handle_student_viewer_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    container,
) -> bool:
    """Main callback handler for student viewer."""
    query = update.callback_query
    if not query or not query.data.startswith(STUDENT_VIEWER_PREFIX):
        return False
    
    data = query.data[len(STUDENT_VIEWER_PREFIX):]
    
    if data == "menu":
        await show_student_management_menu(update, context)
        return True
    
    elif data == "all":
        await show_all_students(update, context, container, page=0)
        return True
    
    elif data.startswith("page_"):
        page = int(data.replace("page_", ""))
        await show_all_students(update, context, container, page=page)
        return True
    
    elif data.startswith("view_"):
        student_id = data.replace("view_", "")
        await show_student_details(update, context, container, student_id)
        return True
    
    elif data == "search_name":
        await prompt_search_name(update, context)
        return True
    
    elif data == "search_phone":
        await prompt_search_phone(update, context)
        return True
    
    elif data == "by_course":
        await show_course_selection(update, context, container)
        return True
    
    elif data.startswith("course_"):
        course_id = data.replace("course_", "")
        await show_course_students(update, context, container, course_id)
        return True
    
    return False
