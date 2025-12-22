"""
Notification-related use cases for the Training Center platform.
Handles auto-reminders and targeted notifications.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta

from domain.entities import (
    Course, Student, Registration,
    RegistrationStatus, PaymentStatus, NotificationType,
)
from domain.repositories import (
    ICourseRepository, IStudentRepository, IRegistrationRepository,
    IPaymentRecordRepository,
)
from domain.value_objects import now_syria


# ============================================================================
# Result Dataclasses
# ============================================================================

@dataclass
class NotificationResult:
    """Result of sending notifications."""
    success: bool
    sent_count: int = 0
    failed_count: int = 0
    error: Optional[str] = None


@dataclass
class StudentProfileResult:
    """Student profile data."""
    student: Optional[Student]
    courses: List[dict]  # List of {course, registration, payments}
    error: Optional[str] = None


# ============================================================================
# Notification Use Cases
# ============================================================================

def get_notification_emoji(notification_type: NotificationType) -> str:
    """Get emoji for notification type."""
    mapping = {
        NotificationType.INFO: "ℹ️",
        NotificationType.REMINDER: "🔔",
        NotificationType.WARNING: "⚠️",
        NotificationType.URGENT: "🚨",
        NotificationType.SUCCESS: "✅",
    }
    return mapping.get(notification_type, "📢")


def get_notification_label(notification_type: NotificationType, is_arabic: bool = True) -> str:
    """Get label for notification type."""
    if is_arabic:
        mapping = {
            NotificationType.INFO: "معلومات",
            NotificationType.REMINDER: "تذكير",
            NotificationType.WARNING: "تنبيه",
            NotificationType.URGENT: "عاجل",
            NotificationType.SUCCESS: "نجاح",
        }
    else:
        mapping = {
            NotificationType.INFO: "Info",
            NotificationType.REMINDER: "Reminder",
            NotificationType.WARNING: "Warning",
            NotificationType.URGENT: "Urgent",
            NotificationType.SUCCESS: "Success",
        }
    return mapping.get(notification_type, "Notification")


def format_notification_message(
    notification_type: NotificationType,
    content: str,
    is_arabic: bool = True,
) -> str:
    """Format a notification message with emoji and label."""
    emoji = get_notification_emoji(notification_type)
    label = get_notification_label(notification_type, is_arabic)
    
    return f"""{emoji} *{label}*
━━━━━━━━━━━━━━━━━━━━━━━━

{content}

━━━━━━━━━━━━━━━━━━━━━━━━
🎓 {"مركز التدريب" if is_arabic else "Training Center"}
"""


class GetCoursesToRemindUseCase:
    """Get courses starting in the next 24 hours that need reminders."""
    
    def __init__(
        self,
        course_repository: ICourseRepository,
        registration_repository: IRegistrationRepository,
        student_repository: IStudentRepository,
        payment_repository: IPaymentRecordRepository,
    ):
        self._course_repo = course_repository
        self._registration_repo = registration_repository
        self._student_repo = student_repository
        self._payment_repo = payment_repository
    
    async def execute(self, hours_before: int = 24) -> List[dict]:
        """
        Get courses starting soon with their students categorized.
        
        Returns list of:
        {
            "course": Course,
            "approved_paid": [Student],      # Send reminder
            "approved_unpaid": [Student],    # Send payment warning
        }
        """
        now = now_syria()
        target_time = now + timedelta(hours=hours_before)
        
        # Get all courses
        all_courses = await self._course_repo.get_available()
        
        result = []
        for course in all_courses:
            # Check if course starts within the window (24h ± 1h)
            time_diff = (course.start_date - now).total_seconds() / 3600
            if not (hours_before - 1 <= time_diff <= hours_before + 1):
                continue
            
            registrations = await self._registration_repo.get_by_course(course.id)
            
            approved_paid = []
            approved_unpaid = []
            
            for reg in registrations:
                if reg.status != RegistrationStatus.APPROVED:
                    continue
                
                student = await self._student_repo.get_by_id(reg.student_id)
                if not student:
                    continue
                
                if reg.payment_status == PaymentStatus.PAID:
                    approved_paid.append(student)
                else:
                    # Calculate remaining amount
                    total_paid = await self._payment_repo.get_total_paid(reg.id)
                    approved_unpaid.append({
                        "student": student,
                        "total_paid": total_paid,
                        "remaining": course.price - total_paid,
                    })
            
            if approved_paid or approved_unpaid:
                result.append({
                    "course": course,
                    "approved_paid": approved_paid,
                    "approved_unpaid": approved_unpaid,
                })
        
        return result


class GetTargetedNotificationRecipientsUseCase:
    """Get recipients for targeted notifications."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
        student_repository: IStudentRepository,
    ):
        self._registration_repo = registration_repository
        self._student_repo = student_repository
    
    async def execute(
        self,
        course_id: Optional[str] = None,
        student_ids: Optional[List[str]] = None,
        all_students: bool = False,
        approved_only: bool = True,
    ) -> List[Student]:
        """Get list of students to notify."""
        if all_students:
            return await self._student_repo.get_all()
        
        if student_ids:
            students = []
            for sid in student_ids:
                student = await self._student_repo.get_by_id(sid)
                if student:
                    students.append(student)
            return students
        
        if course_id:
            registrations = await self._registration_repo.get_by_course(course_id)
            students = []
            for reg in registrations:
                if approved_only and reg.status != RegistrationStatus.APPROVED:
                    continue
                student = await self._student_repo.get_by_id(reg.student_id)
                if student:
                    students.append(student)
            return students
        
        return []


# ============================================================================
# Student Profile Use Case
# ============================================================================

class GetStudentProfileUseCase:
    """Get comprehensive student profile."""
    
    def __init__(
        self,
        student_repository: IStudentRepository,
        registration_repository: IRegistrationRepository,
        course_repository: ICourseRepository,
        payment_repository: IPaymentRecordRepository,
    ):
        self._student_repo = student_repository
        self._registration_repo = registration_repository
        self._course_repo = course_repository
        self._payment_repo = payment_repository
    
    async def execute(self, telegram_id: int) -> StudentProfileResult:
        """Get student profile with all courses and payment info."""
        student = await self._student_repo.get_by_telegram_id(telegram_id)
        if not student:
            return StudentProfileResult(
                student=None,
                courses=[],
                error="Student not found"
            )
        
        registrations = await self._registration_repo.get_by_student(student.id)
        
        courses = []
        for reg in registrations:
            course = await self._course_repo.get_by_id(reg.course_id)
            if not course:
                continue
            
            payments = await self._payment_repo.get_by_registration(reg.id)
            total_paid = sum(p.amount for p in payments)
            
            courses.append({
                "course": course,
                "registration": reg,
                "payments": payments,
                "total_paid": total_paid,
                "remaining": max(0, course.price - total_paid),
            })
        
        return StudentProfileResult(
            student=student,
            courses=courses,
        )
