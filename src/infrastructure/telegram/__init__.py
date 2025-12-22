"""Telegram bot infrastructure package."""
from  infrastructure.telegram.localization_service import (
    LocalizationService,
    get_localization,
    t,
)

__all__ = [
    "LocalizationService",
    "get_localization",
    "t",
]
