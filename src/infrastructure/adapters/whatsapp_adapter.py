"""
WhatsApp Cloud API adapter for OTP verification and notifications.
Uses Meta's WhatsApp Business Platform.
"""
import logging
import random
import string
import httpx
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OTPRecord:
    """Stores OTP information for verification."""
    code: str
    phone: str
    created_at: datetime
    attempts: int = 0
    verified: bool = False
    
    def is_expired(self, ttl_minutes: int = 5) -> bool:
        """Check if OTP has expired."""
        return datetime.now() > self.created_at + timedelta(minutes=ttl_minutes)
    
    def is_valid(self, code: str) -> bool:
        """Check if provided code matches."""
        return self.code == code and not self.is_expired()


class WhatsAppAdapter:
    """
    Adapter for WhatsApp Cloud API.
    Handles OTP sending, verification, and notifications.
    """
    
    BASE_URL = "https://graph.facebook.com/v18.0"
    OTP_TTL_MINUTES = 5
    MAX_ATTEMPTS = 3
    MAX_RESENDS = 3
    
    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        otp_template_name: str = "otp_verification",
    ):
        """
        Initialize WhatsApp adapter.
        
        Args:
            phone_number_id: WhatsApp Business Phone Number ID
            access_token: Meta API Access Token
            otp_template_name: Name of the OTP message template
        """
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._otp_template_name = otp_template_name
        
        # In-memory OTP storage (consider Redis for production)
        self._otp_store: dict[int, OTPRecord] = {}  # telegram_id -> OTPRecord
        self._resend_count: dict[int, int] = {}  # telegram_id -> resend count
    
    def _generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP code."""
        return ''.join(random.choices(string.digits, k=length))
    
    def _format_phone_for_whatsapp(self, phone: str) -> str:
        """
        Format phone number for WhatsApp API.
        Expects Syrian format and converts to international.
        """
        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Syrian number handling
        if phone.startswith('0'):
            # 09xxxxxxxx -> 9639xxxxxxxx
            phone = '963' + phone[1:]
        elif phone.startswith('963'):
            # Already international
            pass
        elif phone.startswith('+963'):
            phone = phone[1:]  # Remove +
        
        return phone
    
    async def send_otp(
        self,
        telegram_id: int,
        phone: str,
    ) -> Tuple[bool, str]:
        """
        Send OTP to phone number via WhatsApp.
        
        Args:
            telegram_id: User's Telegram ID (for tracking)
            phone: Phone number to send OTP to
            
        Returns:
            Tuple of (success, message)
        """
        # Check resend limit
        resend_count = self._resend_count.get(telegram_id, 0)
        if resend_count >= self.MAX_RESENDS:
            return False, "تم تجاوز الحد الأقصى لإعادة الإرسال. حاول لاحقاً."
        
        # Generate OTP
        otp_code = self._generate_otp()
        formatted_phone = self._format_phone_for_whatsapp(phone)
        
        # Send via WhatsApp
        success = await self._send_whatsapp_template(
            to=formatted_phone,
            template_name=self._otp_template_name,
            parameters=[otp_code],
        )
        
        if success:
            # Store OTP
            self._otp_store[telegram_id] = OTPRecord(
                code=otp_code,
                phone=phone,
                created_at=datetime.now(),
            )
            self._resend_count[telegram_id] = resend_count + 1
            
            # Mask phone for display
            masked_phone = phone[:4] + "****" + phone[-3:]
            return True, f"تم إرسال رمز التحقق إلى {masked_phone}"
        else:
            return False, "فشل إرسال رمز التحقق. تأكد من صحة الرقم."
    
    def verify_otp(
        self,
        telegram_id: int,
        code: str,
    ) -> Tuple[bool, str]:
        """
        Verify OTP code.
        
        Args:
            telegram_id: User's Telegram ID
            code: OTP code to verify
            
        Returns:
            Tuple of (success, message)
        """
        record = self._otp_store.get(telegram_id)
        
        if not record:
            return False, "لم يتم إرسال رمز تحقق. أعد إدخال رقم الهاتف."
        
        if record.is_expired(self.OTP_TTL_MINUTES):
            return False, "انتهت صلاحية الرمز. أعد إرسال رمز جديد."
        
        record.attempts += 1
        
        if record.attempts > self.MAX_ATTEMPTS:
            return False, "تم تجاوز عدد المحاولات. أعد إرسال رمز جديد."
        
        if record.is_valid(code):
            record.verified = True
            return True, "✅ تم التحقق بنجاح!"
        else:
            remaining = self.MAX_ATTEMPTS - record.attempts
            return False, f"❌ رمز خاطئ. المحاولات المتبقية: {remaining}"
    
    def is_phone_verified(self, telegram_id: int) -> bool:
        """Check if user's phone is verified."""
        record = self._otp_store.get(telegram_id)
        return record is not None and record.verified
    
    def get_verified_phone(self, telegram_id: int) -> Optional[str]:
        """Get verified phone number for user."""
        record = self._otp_store.get(telegram_id)
        if record and record.verified:
            return record.phone
        return None
    
    def clear_otp(self, telegram_id: int) -> None:
        """Clear OTP record for user."""
        self._otp_store.pop(telegram_id, None)
        self._resend_count.pop(telegram_id, None)
    
    async def _send_whatsapp_template(
        self,
        to: str,
        template_name: str,
        parameters: list[str],
        language: str = "ar",
    ) -> bool:
        """
        Send a WhatsApp template message.
        
        Args:
            to: Recipient phone number (international format)
            template_name: Name of the message template
            parameters: Template parameters
            language: Template language code
            
        Returns:
            True if successful
        """
        url = f"{self.BASE_URL}/{self._phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        # Build template components
        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": param}
                    for param in parameters
                ]
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"WhatsApp OTP sent to {to}")
                    return True
                else:
                    logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    async def send_notification(
        self,
        to: str,
        message: str,
    ) -> bool:
        """
        Send a text notification via WhatsApp.
        Note: This requires a pre-approved template for notifications.
        
        Args:
            to: Recipient phone number
            message: Message content
            
        Returns:
            True if successful
        """
        url = f"{self.BASE_URL}/{self._phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        
        formatted_phone = self._format_phone_for_whatsapp(to)
        
        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "text",
            "text": {"body": message}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"WhatsApp notification sent to {formatted_phone}")
                    return True
                else:
                    logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification: {e}")
            return False
    
    async def send_payment_reminder(
        self,
        phone: str,
        student_name: str,
        course_name: str,
        amount_due: float,
        template_name: str = "payment_reminder",
    ) -> bool:
        """
        Send payment reminder notification.
        
        Args:
            phone: Student's phone number
            student_name: Student's name
            course_name: Course name
            amount_due: Amount due
            template_name: Template name for payment reminders
            
        Returns:
            True if successful
        """
        return await self._send_whatsapp_template(
            to=self._format_phone_for_whatsapp(phone),
            template_name=template_name,
            parameters=[student_name, course_name, str(amount_due)],
        )
