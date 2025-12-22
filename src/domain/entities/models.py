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
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


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
    Student entity.
    All datetime fields are timezone-aware (Asia/Damascus).
    """
    id: str
    telegram_id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    language: Language = Language.ARABIC
    registered_at: datetime = field(default_factory=lambda: None)
    
    @classmethod
    def create(
        cls,
        telegram_id: int,
        name: str,
        now: datetime,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        language: Language = Language.ARABIC,
    ) -> "Student":
        """Factory method to create a new student."""
        return cls(
            id=generate_id(),
            telegram_id=telegram_id,
            name=name,
            phone=phone,
            email=email,
            language=language,
            registered_at=now,
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
    registered_at: datetime = field(default_factory=lambda: None)
    confirmed_at: Optional[datetime] = None
    
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
