"""
Unified UI Components for Telegram Bot.

This module provides reusable, scalable UI components for building
consistent and professional Telegram bot interfaces.

Design Principles:
- All functions are pure and stateless
- Easy to extend with new components
- Consistent styling across the bot
- Supports Arabic and English
"""
from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from domain.entities import Language


# ============================================================================
# Constants
# ============================================================================

class Emoji:
    """Standardized emojis for consistent UI."""
    HOME = "🏠"
    BACK = "🔙"
    CANCEL = "❌"
    CONFIRM = "✅"
    COURSES = "📚"
    REGISTER = "📝"
    MATERIALS = "📁"
    LANGUAGE = "🌍"
    HELP = "❓"
    ADMIN = "⚙️"
    CREATE = "➕"
    UPLOAD = "📤"
    STATS = "📊"
    BROADCAST = "📢"
    POST = "📣"
    GUIDE = "📖"
    WARNING = "⚠️"
    ERROR = "❌"
    SUCCESS = "✅"
    LOADING = "⏳"
    STAR = "⭐"
    CALENDAR = "📅"
    MONEY = "💰"
    PERSON = "👤"
    PEOPLE = "👥"
    INSTRUCTOR = "👨‍🏫"
    CLOCK = "⏱"
    SEAT = "🪑"
    CHECK = "✓"
    UNCHECK = "⬜"
    CHECKED = "✅"
    LINK = "🔗"
    FILE = "📄"
    FOLDER = "📁"
    

class CallbackPrefix:
    """Callback data prefixes for routing."""
    NAV = "nav_"
    ADMIN = "admin_"
    COURSE_CREATE = "cc_"
    UPLOAD_SELECT = "ups_"
    LANG = "lang_"
    CONFIRM = "confirm_"


# ============================================================================
# Text Helpers
# ============================================================================

def t(arabic: str, english: str, lang: Language) -> str:
    """Get localized text based on language."""
    return arabic if lang == Language.ARABIC else english


def divider() -> str:
    """Get a visual divider line."""
    return "━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ============================================================================
# Keyboard Builders
# ============================================================================

class KeyboardBuilder:
    """
    Builder pattern for creating inline keyboards.
    
    Usage:
        keyboard = (KeyboardBuilder()
            .add_button("Click me", "callback_data")
            .add_row()
            .add_button("Another", "callback2")
            .add_back_row(lang)
            .build())
    """
    
    def __init__(self):
        self._rows: List[List[InlineKeyboardButton]] = []
        self._current_row: List[InlineKeyboardButton] = []
    
    def add_button(
        self,
        text: str,
        callback_data: str,
        url: Optional[str] = None
    ) -> "KeyboardBuilder":
        """Add a button to the current row."""
        if url:
            self._current_row.append(InlineKeyboardButton(text, url=url))
        else:
            self._current_row.append(InlineKeyboardButton(text, callback_data=callback_data))
        return self
    
    def add_row(self) -> "KeyboardBuilder":
        """Finish current row and start a new one."""
        if self._current_row:
            self._rows.append(self._current_row)
            self._current_row = []
        return self
    
    def add_button_row(
        self,
        text: str,
        callback_data: str,
        url: Optional[str] = None
    ) -> "KeyboardBuilder":
        """Add a button as its own row (convenience method)."""
        self.add_row()
        self.add_button(text, callback_data, url)
        return self.add_row()
    
    def add_back_button(self, lang: Language, callback: str) -> "KeyboardBuilder":
        """Add a back button to current row."""
        text = f"{Emoji.BACK} " + t("رجوع", "Back", lang)
        self.add_button(text, callback)
        return self
    
    def add_home_button(self, lang: Language) -> "KeyboardBuilder":
        """Add a home/main menu button to current row."""
        text = f"{Emoji.HOME} " + t("الرئيسية", "Main", lang)
        self.add_button(text, f"{CallbackPrefix.NAV}main")
        return self
    
    def add_cancel_button(self, lang: Language, callback: str) -> "KeyboardBuilder":
        """Add a cancel button to current row."""
        text = f"{Emoji.CANCEL} " + t("إلغاء", "Cancel", lang)
        self.add_button(text, callback)
        return self
    
    def add_confirm_button(self, lang: Language, callback: str) -> "KeyboardBuilder":
        """Add a confirm button to current row."""
        text = f"{Emoji.CONFIRM} " + t("تأكيد", "Confirm", lang)
        self.add_button(text, callback)
        return self
    
    def add_back_row(self, lang: Language, back_callback: Optional[str] = None) -> "KeyboardBuilder":
        """Add a row with back and home buttons."""
        self.add_row()
        if back_callback:
            self.add_back_button(lang, back_callback)
        self.add_home_button(lang)
        return self.add_row()
    
    def add_navigation_row(
        self,
        lang: Language,
        back_callback: Optional[str] = None,
        show_home: bool = True
    ) -> "KeyboardBuilder":
        """Add a navigation row with optional back and home buttons."""
        self.add_row()
        if back_callback:
            self.add_back_button(lang, back_callback)
        if show_home:
            self.add_home_button(lang)
        return self.add_row()
    
    def build(self) -> InlineKeyboardMarkup:
        """Build and return the keyboard."""
        # Add any remaining buttons in current row
        if self._current_row:
            self._rows.append(self._current_row)
        return InlineKeyboardMarkup(self._rows)


def quick_keyboard(
    buttons: List[Tuple[str, str]],
    lang: Language,
    back_callback: Optional[str] = None,
    columns: int = 1
) -> InlineKeyboardMarkup:
    """
    Quickly create a keyboard with a list of buttons.
    
    Args:
        buttons: List of (text, callback_data) tuples
        lang: Language for navigation buttons
        back_callback: Optional callback for back button
        columns: Number of columns per row
        
    Returns:
        InlineKeyboardMarkup
    """
    builder = KeyboardBuilder()
    
    for i, (text, callback) in enumerate(buttons):
        builder.add_button(text, callback)
        if (i + 1) % columns == 0:
            builder.add_row()
    
    builder.add_navigation_row(lang, back_callback)
    return builder.build()


# ============================================================================
# Message Formatters
# ============================================================================

def format_header(title: str, emoji: str = "") -> str:
    """Format a message header."""
    if emoji:
        return f"{emoji} *{title}*\n\n{divider()}"
    return f"*{title}*\n\n{divider()}"


def format_success(
    title: str,
    details: Optional[str] = None,
    lang: Language = Language.ARABIC
) -> str:
    """Format a success message."""
    header = t("تمت العملية بنجاح!", "Operation Successful!", lang)
    message = f"{Emoji.SUCCESS} *{header}*\n\n{divider()}\n\n"
    
    if title:
        message += f"{title}\n"
    
    if details:
        message += f"\n{details}\n"
    
    message += f"\n{divider()}"
    return message


def format_error(
    error: str,
    help_text: Optional[str] = None,
    lang: Language = Language.ARABIC
) -> str:
    """Format an error message."""
    header = t("حدث خطأ", "Error Occurred", lang)
    message = f"{Emoji.ERROR} *{header}*\n\n{divider()}\n\n"
    message += f"{error}\n"
    
    if help_text:
        message += f"\n💡 {help_text}\n"
    
    message += f"\n{divider()}"
    return message


def format_warning(
    warning: str,
    lang: Language = Language.ARABIC
) -> str:
    """Format a warning message."""
    return f"{Emoji.WARNING} {warning}"


def format_loading(lang: Language = Language.ARABIC) -> str:
    """Format a loading message."""
    text = t("جاري التحميل...", "Loading...", lang)
    return f"{Emoji.LOADING} {text}"


def format_step(
    step_num: int,
    total_steps: int,
    title: str,
    description: str,
    lang: Language
) -> str:
    """Format a step in a multi-step process."""
    step_text = t("الخطوة", "Step", lang)
    of_text = t("من", "of", lang)
    
    return f"""
{Emoji.REGISTER} *{title}*

{divider()}
📌 *{step_text} {step_num} {of_text} {total_steps}*
{divider()}

{description}
"""


def format_confirmation(
    title: str,
    items: List[Tuple[str, str]],
    lang: Language
) -> str:
    """
    Format a confirmation message with key-value pairs.
    
    Args:
        title: Confirmation title
        items: List of (label, value) tuples
        lang: Language
        
    Returns:
        Formatted confirmation message
    """
    confirm_text = t("تأكيد", "Confirm", lang)
    message = f"{Emoji.CONFIRM} *{confirm_text} {title}*\n\n{divider()}\n\n"
    
    for label, value in items:
        message += f"• *{label}:* {value}\n"
    
    message += f"\n{divider()}"
    return message


# ============================================================================
# Common Keyboards
# ============================================================================

def get_home_keyboard(lang: Language) -> InlineKeyboardMarkup:
    """Get just a home button."""
    return (KeyboardBuilder()
        .add_home_button(lang)
        .build())


def get_back_and_home_keyboard(
    lang: Language,
    back_callback: str
) -> InlineKeyboardMarkup:
    """Get back and home buttons in one row."""
    return (KeyboardBuilder()
        .add_back_button(lang, back_callback)
        .add_home_button(lang)
        .build())


def get_cancel_keyboard(lang: Language, cancel_callback: str) -> InlineKeyboardMarkup:
    """Get just a cancel button."""
    return (KeyboardBuilder()
        .add_cancel_button(lang, cancel_callback)
        .build())


def get_confirm_cancel_keyboard(
    lang: Language,
    confirm_callback: str,
    cancel_callback: str
) -> InlineKeyboardMarkup:
    """Get confirm and cancel buttons."""
    return (KeyboardBuilder()
        .add_confirm_button(lang, confirm_callback)
        .add_row()
        .add_cancel_button(lang, cancel_callback)
        .build())


# ============================================================================
# List Formatters
# ============================================================================

def format_list_item(
    index: int,
    title: str,
    subtitle: Optional[str] = None,
    emoji: str = "📌"
) -> str:
    """Format a single list item."""
    if subtitle:
        return f"{emoji} *{title}*\n   {subtitle}"
    return f"{emoji} *{title}*"


def format_empty_list(
    message: str,
    lang: Language
) -> str:
    """Format an empty list message."""
    empty_emoji = "📭"
    return f"{empty_emoji} *{message}*\n\n{divider()}"


# ============================================================================
# Course-specific Formatters
# ============================================================================

def format_course_card(
    name: str,
    description: str,
    instructor: str,
    start_date: str,
    end_date: str,
    price: float,
    max_students: int,
    status: str,
    lang: Language,
    target_audience: Optional[str] = None,
    duration_hours: Optional[int] = None,
) -> str:
    """Format a course as a beautiful card."""
    
    labels = {
        'description': t("الوصف", "Description", lang),
        'instructor': t("المدرب", "Instructor", lang),
        'date': t("التاريخ", "Dates", lang),
        'price': t("السعر", "Price", lang),
        'max_students': t("الحد الأقصى", "Max Students", lang),
        'status': t("الحالة", "Status", lang),
        'target': t("الفئة المستهدفة", "Target Audience", lang),
        'duration': t("المدة", "Duration", lang),
        'students': t("طالب", "students", lang),
        'hours': t("ساعة", "hours", lang),
    }
    
    card = f"""
{Emoji.COURSES} *{name}*

{divider()}

{Emoji.REGISTER} *{labels['description']}:*
{description}

{Emoji.INSTRUCTOR} *{labels['instructor']}:* {instructor}
{Emoji.CALENDAR} *{labels['date']}:* {start_date} - {end_date}
{Emoji.MONEY} *{labels['price']}:* ${price}
{Emoji.SEAT} *{labels['max_students']}:* {max_students} {labels['students']}
{Emoji.STAR} *{labels['status']}:* {status}
"""
    
    if target_audience:
        card += f"{Emoji.PEOPLE} *{labels['target']}:* {target_audience}\n"
    
    if duration_hours:
        card += f"{Emoji.CLOCK} *{labels['duration']}:* {duration_hours} {labels['hours']}\n"
    
    card += f"\n{divider()}"
    return card


# ============================================================================
# Admin-specific Components
# ============================================================================

def format_stats_card(
    stats: dict,
    lang: Language
) -> str:
    """Format statistics as a card."""
    labels = {
        'title': t("إحصائيات المنصة", "Platform Statistics", lang),
        'students': t("عدد الطلاب", "Students", lang),
        'courses': t("عدد الدورات", "Courses", lang),
        'registrations': t("عدد التسجيلات", "Registrations", lang),
    }
    
    return f"""
{Emoji.STATS} *{labels['title']}*

{divider()}

{Emoji.PEOPLE} *{labels['students']}:* {stats.get('students', 0)}
{Emoji.COURSES} *{labels['courses']}:* {stats.get('courses', 0)}
{Emoji.REGISTER} *{labels['registrations']}:* {stats.get('registrations', 0)}

{divider()}
"""
