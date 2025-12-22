"""Application use cases package."""
from application.use_cases.use_cases import (
    # Course
    GetCoursesUseCase,
    GetCourseByIdUseCase,
    CreateCourseUseCase,
    CreateCourseResult,
    # Registration (legacy)
    RegisterStudentUseCase,
    GetStudentRegistrationsUseCase,
    RegistrationResult,
    # File Upload
    UploadFileUseCase,
    UploadToCoursesUseCase,
    GetMaterialsUseCase,
    UploadResult,
    # Publishing
    PublishPostUseCase,
    CheckAndPublishPostsUseCase,
    PublishPostResult,
    # Language
    SetLanguageUseCase,
    GetLanguageUseCase,
    # Broadcast
    BroadcastMessageUseCase,
    BroadcastResult,
)

from application.use_cases.registration_use_cases import (
    # Registration v2
    RequestRegistrationUseCase,
    ApproveRegistrationUseCase,
    RejectRegistrationUseCase,
    GetPendingRegistrationsUseCase,
    RegistrationRequestResult,
    ApprovalResult,
    # Payment
    AddPaymentUseCase,
    GetPaymentHistoryUseCase,
    GetCourseStudentsUseCase,
    PaymentResult,
)

from application.use_cases.notification_use_cases import (
    # Notifications
    GetCoursesToRemindUseCase,
    GetTargetedNotificationRecipientsUseCase,
    GetStudentProfileUseCase,
    # Helpers
    format_notification_message,
    get_notification_emoji,
    get_notification_label,
    # Results
    NotificationResult,
    StudentProfileResult,
)

__all__ = [
    # Legacy
    "GetCoursesUseCase",
    "GetCourseByIdUseCase",
    "CreateCourseUseCase",
    "CreateCourseResult",
    "RegisterStudentUseCase",
    "GetStudentRegistrationsUseCase",
    "RegistrationResult",
    "UploadFileUseCase",
    "UploadToCoursesUseCase",
    "GetMaterialsUseCase",
    "UploadResult",
    "PublishPostUseCase",
    "CheckAndPublishPostsUseCase",
    "PublishPostResult",
    "SetLanguageUseCase",
    "GetLanguageUseCase",
    "BroadcastMessageUseCase",
    "BroadcastResult",
    # Registration v2
    "RequestRegistrationUseCase",
    "ApproveRegistrationUseCase",
    "RejectRegistrationUseCase",
    "GetPendingRegistrationsUseCase",
    "RegistrationRequestResult",
    "ApprovalResult",
    # Payment
    "AddPaymentUseCase",
    "GetPaymentHistoryUseCase",
    "GetCourseStudentsUseCase",
    "PaymentResult",
    # Notifications
    "GetCoursesToRemindUseCase",
    "GetTargetedNotificationRecipientsUseCase",
    "GetStudentProfileUseCase",
    "format_notification_message",
    "get_notification_emoji",
    "get_notification_label",
    "NotificationResult",
    "StudentProfileResult",
]
