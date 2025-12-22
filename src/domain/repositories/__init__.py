"""Repository interfaces package."""
from  domain.repositories.interfaces import (
    ICourseRepository,
    IStudentRepository,
    IRegistrationRepository,
    IUserPreferencesRepository,
    IScheduledPostRepository,
)

__all__ = [
    "ICourseRepository",
    "IStudentRepository",
    "IRegistrationRepository",
    "IUserPreferencesRepository",
    "IScheduledPostRepository",
]
