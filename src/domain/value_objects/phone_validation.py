"""
Phone number validation utilities for Syrian phone numbers.
"""
import re
from typing import Tuple, Optional


def validate_syrian_phone(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate Syrian phone number.
    
    Valid formats:
        - 0912345678 (10 digits starting with 0)
        - 912345678 (9 digits without leading 0)
        - +963912345678 (with country code)
        - 00963912345678 (with international prefix)
        - 963912345678 (country code without +)
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, normalized_number, error_message)
        - normalized_number: Always in format 09XXXXXXXX
    """
    # Remove spaces, dashes, and parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())
    
    # Empty check
    if not cleaned:
        return False, None, "رقم الهاتف مطلوب"
    
    # Check for valid characters
    if not re.match(r'^[\d\+]+$', cleaned):
        return False, None, "الرقم يجب أن يحتوي على أرقام فقط"
    
    # Remove country code variations
    if cleaned.startswith('+963'):
        cleaned = '0' + cleaned[4:]
    elif cleaned.startswith('00963'):
        cleaned = '0' + cleaned[5:]
    elif cleaned.startswith('963'):
        cleaned = '0' + cleaned[3:]
    
    # Add leading zero if missing
    if len(cleaned) == 9 and cleaned[0] != '0':
        cleaned = '0' + cleaned
    
    # Validate final format (10 digits starting with 09)
    if not re.match(r'^09\d{8}$', cleaned):
        return False, None, "الرقم يجب أن يكون 10 أرقام ويبدأ بـ 09"
    
    return True, cleaned, None


def get_phone_input_example() -> str:
    """Get example text for phone input."""
    return """📱 *أدخل رقم الهاتف:*

الصيغ المقبولة:
• `0912345678` (10 أرقام تبدأ بـ 09)
• `+963912345678` (مع رمز الدولة)

مثال: `0991234567`
"""


def format_phone_display(phone: str) -> str:
    """Format phone for display."""
    if len(phone) == 10:
        return f"{phone[:4]} {phone[4:7]} {phone[7:]}"
    return phone
