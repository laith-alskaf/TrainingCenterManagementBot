"""
Dependency injection container for the application.
Wires up all components following Clean Architecture.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from config import Config, config
from infrastructure.database import MongoDB
from infrastructure.repositories import (
    MongoDBCourseRepository,
    MongoDBStudentRepository,
    MongoDBRegistrationRepository,
    MongoDBUserPreferencesRepository,
    MongoDBScheduledPostRepository,
)
from infrastructure.adapters import (
    GoogleDriveAdapter,
    GoogleSheetsAdapter,
    MetaGraphAdapter,
)
from infrastructure.scheduler import PostScheduler
from application.use_cases import (
    GetCoursesUseCase,
    GetCourseByIdUseCase,
    CreateCourseUseCase,
    RegisterStudentUseCase,
    GetStudentRegistrationsUseCase,
    UploadFileUseCase,
    UploadToCoursesUseCase,
    GetMaterialsUseCase,
    PublishPostUseCase,
    CheckAndPublishPostsUseCase,
    SetLanguageUseCase,
    GetLanguageUseCase,
    BroadcastMessageUseCase,
)

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """
    Dependency injection container.
    Holds all repositories, adapters, and use cases.
    """
    # Repositories
    course_repo: MongoDBCourseRepository
    student_repo: MongoDBStudentRepository
    registration_repo: MongoDBRegistrationRepository
    user_prefs_repo: MongoDBUserPreferencesRepository
    post_repo: MongoDBScheduledPostRepository
    
    # Adapters
    drive_adapter: GoogleDriveAdapter
    sheets_adapter: GoogleSheetsAdapter
    meta_adapter: MetaGraphAdapter
    
    # Use Cases
    get_courses: GetCoursesUseCase
    get_course_by_id: GetCourseByIdUseCase
    create_course: CreateCourseUseCase
    register_student: RegisterStudentUseCase
    get_registrations: GetStudentRegistrationsUseCase
    upload_file: UploadFileUseCase
    upload_to_courses: UploadToCoursesUseCase
    get_materials: GetMaterialsUseCase
    publish_post: PublishPostUseCase
    check_and_publish: CheckAndPublishPostsUseCase
    set_language: SetLanguageUseCase
    get_language: GetLanguageUseCase
    broadcast_message: BroadcastMessageUseCase
    
    # Scheduler
    scheduler: PostScheduler


async def create_container(app_config: Optional[Config] = None) -> Container:
    """
    Create and initialize the dependency injection container.
    
    Args:
        app_config: Application configuration (defaults to global config)
        
    Returns:
        Fully initialized Container
    """
    if app_config is None:
        app_config = config
    
    logger.info("Initializing dependency injection container...")
    
    # Connect to MongoDB
    await MongoDB.connect(
        uri=app_config.mongodb.uri,
        database_name=app_config.mongodb.database_name,
    )
    
    # Create repositories
    course_repo = MongoDBCourseRepository()
    student_repo = MongoDBStudentRepository()
    registration_repo = MongoDBRegistrationRepository()
    user_prefs_repo = MongoDBUserPreferencesRepository()
    post_repo = MongoDBScheduledPostRepository()
    
    # Create adapters
    drive_adapter = GoogleDriveAdapter(
        service_account_file=app_config.google.service_account_file,
        folder_id=app_config.google.drive_folder_id,
    )
    sheets_adapter = GoogleSheetsAdapter(
        service_account_file=app_config.google.service_account_file,
        spreadsheet_id=app_config.google.sheets_id,
        sheet_name=app_config.google.sheets_name,
    )
    meta_adapter = MetaGraphAdapter(
        access_token=app_config.meta.access_token,
        facebook_page_id=app_config.meta.facebook_page_id,
        instagram_account_id=app_config.meta.instagram_account_id,
    )
    
    # Create use cases
    get_courses = GetCoursesUseCase(course_repo)
    get_course_by_id = GetCourseByIdUseCase(course_repo)
    create_course = CreateCourseUseCase(course_repo, drive_adapter)
    register_student = RegisterStudentUseCase(student_repo, course_repo, registration_repo)
    get_registrations = GetStudentRegistrationsUseCase(student_repo, registration_repo, course_repo)
    upload_file = UploadFileUseCase(drive_adapter)
    upload_to_courses = UploadToCoursesUseCase(drive_adapter, course_repo)
    get_materials = GetMaterialsUseCase(drive_adapter, course_repo)
    set_language = SetLanguageUseCase(user_prefs_repo)
    get_language = GetLanguageUseCase(user_prefs_repo)
    broadcast_message = BroadcastMessageUseCase(user_prefs_repo, student_repo)
    publish_post = PublishPostUseCase(meta_adapter)
    
    # Create scheduler
    scheduler = PostScheduler(
        check_interval_minutes=app_config.scheduler.check_interval_minutes,
    )
    
    # Create check_and_publish use case with callbacks (will be set up later)
    check_and_publish = CheckAndPublishPostsUseCase(
        sheets_adapter=sheets_adapter,
        publish_use_case=publish_post,
    )
    
    logger.info("Dependency injection container initialized successfully")
    
    return Container(
        # Repositories
        course_repo=course_repo,
        student_repo=student_repo,
        registration_repo=registration_repo,
        user_prefs_repo=user_prefs_repo,
        post_repo=post_repo,
        # Adapters
        drive_adapter=drive_adapter,
        sheets_adapter=sheets_adapter,
        meta_adapter=meta_adapter,
        # Use Cases
        get_courses=get_courses,
        get_course_by_id=get_course_by_id,
        create_course=create_course,
        register_student=register_student,
        get_registrations=get_registrations,
        upload_file=upload_file,
        upload_to_courses=upload_to_courses,
        get_materials=get_materials,
        publish_post=publish_post,
        check_and_publish=check_and_publish,
        set_language=set_language,
        get_language=get_language,
        broadcast_message=broadcast_message,
        # Scheduler
        scheduler=scheduler,
    )


async def shutdown_container(container: Container) -> None:
    """
    Shutdown the container and clean up resources.
    
    Args:
        container: Container to shutdown
    """
    logger.info("Shutting down application...")
    
    # Stop scheduler
    container.scheduler.stop()
    
    # Disconnect from MongoDB
    await MongoDB.disconnect()
    
    logger.info("Application shutdown complete")
