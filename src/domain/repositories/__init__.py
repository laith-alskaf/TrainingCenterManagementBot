"""Repository interfaces package."""
from  domain.repositories.interfaces import (
    ICourseRepository,
    IStudentRepository,
    IRegistrationRepository,
    IUserPreferencesRepository,
    IScheduledPostRepository,
    IPaymentRecordRepository,
)

__all__ = [
    "ICourseRepository",
    "IStudentRepository",
    "IRegistrationRepository",
    "IUserPreferencesRepository",
    "IScheduledPostRepository",
    "IPaymentRecordRepository",
]
