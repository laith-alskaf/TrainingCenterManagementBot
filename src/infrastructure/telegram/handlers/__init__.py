"""Telegram handlers package."""
from infrastructure.telegram.handlers.base import (
    admin_required,
    get_user_language,
    get_user_language_async,
    log_handler,
    send_error_to_admin,
)
from infrastructure.telegram.handlers.start_handler import (
    get_start_handler,
    create_navigation_callback_handler,
    create_admin_callback_handler,
)
from infrastructure.telegram.handlers.language_handler import (
    get_language_handler,
    get_language_callback_handler,
)
from infrastructure.telegram.handlers.courses_handler import (
    get_courses_handler,
    get_course_detail_callback_handler,
)
from infrastructure.telegram.handlers.register_handler import (
    get_register_conversation_handler,
)
from infrastructure.telegram.handlers.materials_handler import (
    get_materials_handler,
    get_materials_callback_handler,
)
from infrastructure.telegram.handlers.admin_handlers import (
    get_post_conversation_handler,
    get_broadcast_conversation_handler,
    get_upload_conversation_handler,
)

__all__ = [
    # Base
    "admin_required",
    "get_user_language",
    "get_user_language_async",
    "log_handler",
    "send_error_to_admin",
    # Handlers
    "get_start_handler",
    "create_navigation_callback_handler",
    "create_admin_callback_handler",
    "get_language_handler",
    "get_language_callback_handler",
    "get_courses_handler",
    "get_course_detail_callback_handler",
    "get_register_conversation_handler",
    "get_materials_handler",
    "get_materials_callback_handler",
    "get_post_conversation_handler",
    "get_broadcast_conversation_handler",
    "get_upload_conversation_handler",
]
