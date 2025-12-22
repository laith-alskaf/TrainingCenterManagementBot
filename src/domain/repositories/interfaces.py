"""
Repository interfaces for the domain layer.
Following the Repository pattern for data access abstraction.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from  domain.entities import (
    Course,
    Student,
    Registration,
    ScheduledPost,
    UserPreferences,
    PaymentRecord,
    Language,
    PostStatus,
    RegistrationStatus,
)


class ICourseRepository(ABC):
    """Interface for course data access."""
    
    @abstractmethod
    async def get_by_id(self, course_id: str) -> Optional[Course]:
        """Get a course by ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Course]:
        """Get all courses."""
        pass
    
    @abstractmethod
    async def get_available(self) -> List[Course]:
        """Get all available (published/ongoing) courses."""
        pass
    
    @abstractmethod
    async def save(self, course: Course) -> Course:
        """Save a course (insert or update)."""
        pass
    
    @abstractmethod
    async def delete(self, course_id: str) -> bool:
        """Delete a course by ID."""
        pass


class IStudentRepository(ABC):
    """Interface for student data access."""
    
    @abstractmethod
    async def get_by_id(self, student_id: str) -> Optional[Student]:
        """Get a student by ID."""
        pass
    
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Student]:
        """Get a student by Telegram ID."""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Student]:
        """Get all students."""
        pass
    
    @abstractmethod
    async def save(self, student: Student) -> Student:
        """Save a student (insert or update)."""
        pass
    
    @abstractmethod
    async def delete(self, student_id: str) -> bool:
        """Delete a student by ID."""
        pass


class IRegistrationRepository(ABC):
    """Interface for registration data access."""
    
    @abstractmethod
    async def get_by_id(self, registration_id: str) -> Optional[Registration]:
        """Get a registration by ID."""
        pass
    
    @abstractmethod
    async def get_by_student_and_course(
        self, 
        student_id: str, 
        course_id: str
    ) -> Optional[Registration]:
        """Get a registration by student and course."""
        pass
    
    @abstractmethod
    async def get_by_student(self, student_id: str) -> List[Registration]:
        """Get all registrations for a student."""
        pass
    
    @abstractmethod
    async def get_by_course(self, course_id: str) -> List[Registration]:
        """Get all registrations for a course."""
        pass
    
    @abstractmethod
    async def save(self, registration: Registration) -> Registration:
        """Save a registration (insert or update)."""
        pass
    
    @abstractmethod
    async def delete(self, registration_id: str) -> bool:
        """Delete a registration by ID."""
        pass
    
    @abstractmethod
    async def count_by_course(self, course_id: str) -> int:
        """Count registrations for a course."""
        pass
    
    @abstractmethod
    async def get_by_status(self, status: RegistrationStatus) -> List[Registration]:
        """Get all registrations with a specific status."""
        pass


class IUserPreferencesRepository(ABC):
    """Interface for user preferences data access."""
    
    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserPreferences]:
        """Get preferences for a Telegram user."""
        pass
    
    @abstractmethod
    async def save(self, preferences: UserPreferences) -> UserPreferences:
        """Save user preferences (insert or update)."""
        pass
    
    @abstractmethod
    async def set_language(self, telegram_id: int, language: Language) -> UserPreferences:
        """Update user language preference."""
        pass
    
    @abstractmethod
    async def get_all_with_notifications(self) -> List[UserPreferences]:
        """Get all users with notifications enabled."""
        pass


class IScheduledPostRepository(ABC):
    """Interface for scheduled post data access."""
    
    @abstractmethod
    async def get_by_id(self, post_id: str) -> Optional[ScheduledPost]:
        """Get a post by ID."""
        pass
    
    @abstractmethod
    async def get_pending(self) -> List[ScheduledPost]:
        """Get all pending posts."""
        pass
    
    @abstractmethod
    async def save(self, post: ScheduledPost) -> ScheduledPost:
        """Save a post (insert or update)."""
        pass
    
    @abstractmethod
    async def update_status(
        self, 
        post_id: str, 
        status: PostStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update post status."""
        pass


class IPaymentRecordRepository(ABC):
    """Interface for payment record data access."""
    
    @abstractmethod
    async def get_by_id(self, record_id: str) -> Optional[PaymentRecord]:
        """Get a payment record by ID."""
        pass
    
    @abstractmethod
    async def get_by_registration(self, registration_id: str) -> List[PaymentRecord]:
        """Get all payment records for a registration."""
        pass
    
    @abstractmethod
    async def save(self, record: PaymentRecord) -> PaymentRecord:
        """Save a payment record."""
        pass
    
    @abstractmethod
    async def get_total_paid(self, registration_id: str) -> float:
        """Get total amount paid for a registration."""
        pass
    
    @abstractmethod
    async def delete(self, record_id: str) -> bool:
        """Delete a payment record."""
        pass
