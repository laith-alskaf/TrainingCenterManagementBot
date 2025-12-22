"""
Domain entities for the Training Center Management Platform.
All datetime fields are timezone-aware, normalized to Asia/Damascus.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class CourseStatus(str, Enum):
    """Status of a course."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RegistrationStatus(str, Enum):
    """Status of a student registration."""
    PENDING = "pending"         # طلب معلق
    APPROVED = "approved"       # تم القبول
    REJECTED = "rejected"       # مرفوض
    CANCELLED = "cancelled"     # ملغي


class PaymentStatus(str, Enum):
    """Payment status for a registration."""
    UNPAID = "unpaid"           # لم يدفع
    PARTIAL = "partial"         # دفع جزئي
    PAID = "paid"               # دفع كامل


class PaymentMethod(str, Enum):
    """Payment method for a payment record."""
    CASH = "cash"               # نقد
    TRANSFER = "transfer"       # تحويل
    CARD = "card"               # بطاقة
    OTHER = "other"             # أخرى


class NotificationType(str, Enum):
    """Type of notification to send."""
    INFO = "info"               # ℹ️ معلومات
    REMINDER = "reminder"       # 🔔 تذكير
    WARNING = "warning"         # ⚠️ تنبيه
    URGENT = "urgent"           # 🚨 عاجل
    SUCCESS = "success"         # ✅ نجاح


class Gender(str, Enum):
    """Gender of a student."""
    MALE = "male"               # ذكر
    FEMALE = "female"           # أنثى


class EducationLevel(str, Enum):
    """Education level of a student."""
    MIDDLE_SCHOOL = "middle_school"  # إعدادي
    HIGH_SCHOOL = "high_school"      # ثانوي
    DIPLOMA = "diploma"              # معهد
    BACHELOR = "bachelor"            # بكالوريوس
    MASTER = "master"                # ماجستير
    PHD = "phd"                      # دكتوراه
    OTHER = "other"                  # أخرى


class PostStatus(str, Enum):
    """Status of a scheduled post."""
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"


class Platform(str, Enum):
    """Social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    BOTH = "both"


class Language(str, Enum):
    """Supported languages."""
    ARABIC = "ar"
    ENGLISH = "en"


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


@dataclass
class Course:
    """
    Training course entity.
    All datetime fields are timezone-aware (Asia/Damascus).
    """
    id: str
    name: str
    description: str
    instructor: str
    start_date: datetime  # Timezone-aware
    end_date: datetime    # Timezone-aware
    price: float
    max_students: int
    status: CourseStatus = CourseStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: None)  # Set on creation
    updated_at: datetime = field(default_factory=lambda: None)  # Set on update
    materials_folder_id: Optional[str] = None  # Google Drive folder ID
    target_audience: Optional[str] = None  # Target audience description
    duration_hours: Optional[int] = None  # Total course duration in hours
    
    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        instructor: str,
        start_date: datetime,
        end_date: datetime,
        price: float,
        max_students: int,
        now: datetime,
        target_audience: Optional[str] = None,
        duration_hours: Optional[int] = None,
    ) -> "Course":
        """Factory method to create a new course."""
        return cls(
            id=generate_id(),
            name=name,
            description=description,
            instructor=instructor,
            start_date=start_date,
            end_date=end_date,
            price=price,
            max_students=max_students,
            created_at=now,
            updated_at=now,
            target_audience=target_audience,
            duration_hours=duration_hours,
        )


@dataclass
class Student:
    """
    Student entity representing a training center student.
    All datetime fields are timezone-aware (Asia/Damascus).
    
    Profile must be completed before student can use services.
    """
    id: str
    telegram_id: int
    
    # Personal Information
    full_name: str                              # الاسم الثلاثي
    phone_number: str                           # رقم الهاتف (09XXXXXXXX)
    gender: Gender                              # الجنس
    age: int                                    # العمر
    residence: str                              # مكان الإقامة
    
    # Education Information
    education_level: EducationLevel             # المستوى الدراسي
    specialization: Optional[str] = None        # الاختصاص (للجامعة/المعهد)
    
    # Profile Status
    profile_completed: bool = False             # هل اكتمل الملف الشخصي؟
    
    # Optional Fields
    email: Optional[str] = None
    language: Language = Language.ARABIC
    
    # Timestamps
    registered_at: datetime = field(default_factory=lambda: None)
    updated_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        telegram_id: int,
        full_name: str,
        phone_number: str,
        gender: Gender,
        age: int,
        residence: str,
        education_level: EducationLevel,
        now: datetime,
        specialization: Optional[str] = None,
        email: Optional[str] = None,
        language: Language = Language.ARABIC,
    ) -> "Student":
        """Factory method to create a new student with complete profile."""
        return cls(
            id=generate_id(),
            telegram_id=telegram_id,
            full_name=full_name,
            phone_number=phone_number,
            gender=gender,
            age=age,
            residence=residence,
            education_level=education_level,
            specialization=specialization,
            profile_completed=True,
            email=email,
            language=language,
            registered_at=now,
            updated_at=now,
        )
    
    @classmethod
    def create_incomplete(
        cls,
        telegram_id: int,
        now: datetime,
        language: Language = Language.ARABIC,
    ) -> "Student":
        """Factory method to create an incomplete student profile."""
        return cls(
            id=generate_id(),
            telegram_id=telegram_id,
            full_name="",
            phone_number="",
            gender=Gender.MALE,
            age=0,
            residence="",
            education_level=EducationLevel.OTHER,
            specialization=None,
            profile_completed=False,
            email=None,
            language=language,
            registered_at=now,
            updated_at=now,
        )


@dataclass
class Registration:
    """
    Course registration entity.
    All datetime fields are timezone-aware (Asia/Damascus).
    """
    id: str
    student_id: str
    course_id: str
    status: RegistrationStatus = RegistrationStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    registered_at: datetime = field(default_factory=lambda: None)
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None   # Admin telegram_id who approved
    notes: Optional[str] = None          # Admin notes
    
    @classmethod
    def create(
        cls,
        student_id: str,
        course_id: str,
        now: datetime,
    ) -> "Registration":
        """Factory method to create a new registration."""
        return cls(
            id=generate_id(),
            student_id=student_id,
            course_id=course_id,
            registered_at=now,
        )


@dataclass
class ScheduledPost:
    """
    Scheduled social media post entity.
    All datetime fields are timezone-aware (Asia/Damascus).
    
    Note: For Instagram, image_url is required. Posts without images
    will be skipped and logged as errors.
    """
    id: str
    content: str
    scheduled_datetime: datetime  # Timezone-aware (Asia/Damascus)
    platform: Platform
    status: PostStatus = PostStatus.PENDING
    image_url: Optional[str] = None
    published_at: Optional[datetime] = None
    error_message: Optional[str] = None
    sheet_row_index: Optional[int] = None  # Original row in Google Sheets
    
    @classmethod
    def create(
        cls,
        content: str,
        scheduled_datetime: datetime,
        platform: Platform,
        image_url: Optional[str] = None,
        sheet_row_index: Optional[int] = None,
    ) -> "ScheduledPost":
        """Factory method to create a new scheduled post."""
        return cls(
            id=generate_id(),
            content=content,
            scheduled_datetime=scheduled_datetime,
            platform=platform,
            image_url=image_url,
            sheet_row_index=sheet_row_index,
        )
    
    def requires_image(self) -> bool:
        """Check if this post requires an image (Instagram posts)."""
        return self.platform in (Platform.INSTAGRAM, Platform.BOTH)
    
    def can_publish_to_instagram(self) -> bool:
        """Check if this post can be published to Instagram."""
        return bool(self.image_url and self.image_url.strip())
    
    def validate_for_instagram(self) -> Optional[str]:
        """
        Validate post for Instagram publishing.
        Returns error message if invalid, None if valid.
        """
        if self.platform in (Platform.INSTAGRAM, Platform.BOTH):
            if not self.can_publish_to_instagram():
                return "Instagram posts require a valid image_url"
        return None


@dataclass
class UserPreferences:
    """User preferences entity (for Telegram users)."""
    telegram_id: int
    language: Language = Language.ARABIC
    notifications_enabled: bool = True
    
    @classmethod
    def create(
        cls,
        telegram_id: int,
        language: Language = Language.ARABIC,
    ) -> "UserPreferences":
        """Factory method to create default user preferences."""
        return cls(
            telegram_id=telegram_id,
            language=language,
        )


@dataclass
class PaymentRecord:
    """
    Payment record entity for tracking individual payments.
    Each registration can have multiple payment records.
    """
    id: str
    registration_id: str
    amount: float                    # المبلغ المدفوع
    paid_at: datetime               # تاريخ الدفع
    method: PaymentMethod           # طريقة الدفع
    received_by: int                # Admin telegram_id
    notes: Optional[str] = None     # ملاحظات
    
    @classmethod
    def create(
        cls,
        registration_id: str,
        amount: float,
        method: PaymentMethod,
        received_by: int,
        now: datetime,
        notes: Optional[str] = None,
    ) -> "PaymentRecord":
        """Factory method to create a new payment record."""
        return cls(
            id=generate_id(),
            registration_id=registration_id,
            amount=amount,
            paid_at=now,
            method=method,
            received_by=received_by,
            notes=notes,
        )
