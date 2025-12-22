"""
Application use cases for the Training Center Management Platform.
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from domain.entities import (
    Course, Student, Registration, ScheduledPost, UserPreferences,
    CourseStatus, RegistrationStatus, PostStatus, Platform, Language,
)
from domain.repositories import (
    ICourseRepository, IStudentRepository, IRegistrationRepository,
    IUserPreferencesRepository, IScheduledPostRepository,
)
from domain.value_objects import now_syria, is_past_or_now
from infrastructure.adapters import (
    GoogleDriveAdapter, GoogleSheetsAdapter, MetaGraphAdapter, PublishResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Course Use Cases
# ============================================================================

class GetCoursesUseCase:
    """Get available courses."""
    
    def __init__(self, course_repo: ICourseRepository):
        self._course_repo = course_repo
    
    async def execute(self, available_only: bool = True) -> List[Course]:
        """Get courses, optionally filtered to available only."""
        if available_only:
            return await self._course_repo.get_available()
        return await self._course_repo.get_all()


class GetCourseByIdUseCase:
    """Get a specific course by ID."""
    
    def __init__(self, course_repo: ICourseRepository):
        self._course_repo = course_repo
    
    async def execute(self, course_id: str) -> Optional[Course]:
        return await self._course_repo.get_by_id(course_id)


@dataclass
class CreateCourseResult:
    """Result of course creation."""
    success: bool
    course: Optional[Course] = None
    error: Optional[str] = None


class CreateCourseUseCase:
    """Create a new course with Google Drive folder."""
    
    def __init__(
        self,
        course_repo: ICourseRepository,
        drive_adapter: GoogleDriveAdapter,
    ):
        self._course_repo = course_repo
        self._drive = drive_adapter
    
    async def execute(
        self,
        name: str,
        description: str,
        instructor: str,
        start_date: datetime,
        end_date: datetime,
        price: float,
        max_students: int,
        target_audience: Optional[str] = None,
        duration_hours: Optional[int] = None,
    ) -> CreateCourseResult:
        """
        Create a new course and its Google Drive folder.
        
        The course is created with PUBLISHED status.
        A Google Drive folder is automatically created for course materials.
        """
        try:
            now = now_syria()
            
            # Validate inputs
            if not name or len(name.strip()) < 2:
                return CreateCourseResult(success=False, error="Course name too short")
            
            if price < 0:
                return CreateCourseResult(success=False, error="Price cannot be negative")
            
            if max_students < 1:
                return CreateCourseResult(success=False, error="Max students must be at least 1")
            
            if start_date >= end_date:
                return CreateCourseResult(success=False, error="Start date must be before end date")
            
            # Create Google Drive folder for course materials
            try:
                folder_id = await self._drive.create_folder(name)
                logger.info(f"Created Drive folder for course '{name}': {folder_id}")
            except Exception as e:
                logger.error(f"Failed to create Drive folder: {e}")
                folder_id = None  # Course can still be created without folder
            
            # Create course
            course = Course.create(
                name=name.strip(),
                description=description.strip(),
                instructor=instructor.strip(),
                start_date=start_date,
                end_date=end_date,
                price=price,
                max_students=max_students,
                now=now,
                target_audience=target_audience.strip() if target_audience else None,
                duration_hours=duration_hours,
            )
            
            # Set folder ID and status
            course.materials_folder_id = folder_id
            course.status = CourseStatus.PUBLISHED
            
            # Save to database
            await self._course_repo.save(course)
            
            logger.info(f"Created course: {course.id} - {course.name}")
            return CreateCourseResult(success=True, course=course)
            
        except Exception as e:
            logger.error(f"Failed to create course: {e}")
            return CreateCourseResult(success=False, error=str(e))


# ============================================================================
# Student Registration Use Cases
# ============================================================================

@dataclass
class RegistrationResult:
    """Result of a registration attempt."""
    success: bool
    registration: Optional[Registration] = None
    error: Optional[str] = None


class RegisterStudentUseCase:
    """Register a student for a course."""
    
    def __init__(
        self,
        student_repo: IStudentRepository,
        course_repo: ICourseRepository,
        registration_repo: IRegistrationRepository,
    ):
        self._student_repo = student_repo
        self._course_repo = course_repo
        self._registration_repo = registration_repo
    
    async def execute(
        self,
        telegram_id: int,
        name: str,
        course_id: str,
        phone: Optional[str] = None,
        email: Optional[str] = None,
    ) -> RegistrationResult:
        """Register a student for a course."""
        now = now_syria()
        
        # Get or create student
        student = await self._student_repo.get_by_telegram_id(telegram_id)
        if student is None:
            student = Student.create(
                telegram_id=telegram_id,
                full_name=name,
                phone_number=phone or "",
                now=now,
                email=email,
            )
            await self._student_repo.save(student)
        
        # Verify course exists and is available
        course = await self._course_repo.get_by_id(course_id)
        if course is None:
            return RegistrationResult(success=False, error="Course not found")
        
        if course.status not in (CourseStatus.PUBLISHED, CourseStatus.ONGOING):
            return RegistrationResult(success=False, error="Course is not available for registration")
        
        # Check if already registered
        existing = await self._registration_repo.get_by_student_and_course(student.id, course_id)
        if existing:
            return RegistrationResult(success=False, error="Already registered for this course")
        
        # Check course capacity
        count = await self._registration_repo.count_by_course(course_id)
        if count >= course.max_students:
            return RegistrationResult(success=False, error="Course is full")
        
        # Create registration
        registration = Registration.create(
            student_id=student.id,
            course_id=course_id,
            now=now,
        )
        await self._registration_repo.save(registration)
        
        return RegistrationResult(success=True, registration=registration)


class GetStudentRegistrationsUseCase:
    """Get all registrations for a student."""
    
    def __init__(
        self,
        student_repo: IStudentRepository,
        registration_repo: IRegistrationRepository,
        course_repo: ICourseRepository,
    ):
        self._student_repo = student_repo
        self._registration_repo = registration_repo
        self._course_repo = course_repo
    
    async def execute(self, telegram_id: int) -> List[tuple]:
        """Get registrations as (registration, course) tuples."""
        student = await self._student_repo.get_by_telegram_id(telegram_id)
        if student is None:
            return []
        
        registrations = await self._registration_repo.get_by_student(student.id)
        results = []
        for reg in registrations:
            course = await self._course_repo.get_by_id(reg.course_id)
            if course:
                results.append((reg, course))
        return results


# ============================================================================
# File Upload Use Cases
# ============================================================================

@dataclass
class UploadResult:
    """Result of a file upload."""
    success: bool
    shareable_link: Optional[str] = None
    links: Optional[List[str]] = None  # For multi-course uploads
    error: Optional[str] = None


class UploadFileUseCase:
    """Upload a file to Google Drive."""
    
    def __init__(self, drive_adapter: GoogleDriveAdapter):
        self._drive = drive_adapter
    
    async def execute(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        folder_id: Optional[str] = None,
    ) -> UploadResult:
        """Upload file bytes to Google Drive."""
        try:
            link = await self._drive.upload_file_bytes(
                file_bytes=file_bytes,
                file_name=file_name,
                mime_type=mime_type,
                folder_id=folder_id,
            )
            return UploadResult(success=True, shareable_link=link)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return UploadResult(success=False, error=str(e))


class UploadToCoursesUseCase:
    """Upload a file to multiple course folders."""
    
    def __init__(
        self,
        drive_adapter: GoogleDriveAdapter,
        course_repo: ICourseRepository,
    ):
        self._drive = drive_adapter
        self._course_repo = course_repo
    
    async def execute(
        self,
        file_bytes: bytes,
        file_name: str,
        mime_type: str,
        course_ids: List[str],
    ) -> UploadResult:
        """
        Upload file to multiple course folders.
        
        Args:
            file_bytes: File content
            file_name: File name
            mime_type: MIME type
            course_ids: List of course IDs to upload to
            
        Returns:
            UploadResult with list of links for each course
        """
        if not course_ids:
            return UploadResult(success=False, error="No courses selected")
        
        links = []
        errors = []
        
        for course_id in course_ids:
            course = await self._course_repo.get_by_id(course_id)
            if course is None:
                errors.append(f"Course {course_id} not found")
                continue
            
            if course.materials_folder_id is None:
                # Create folder if missing
                try:
                    folder_id = await self._drive.create_folder(course.name)
                    course.materials_folder_id = folder_id
                    await self._course_repo.save(course)
                except Exception as e:
                    errors.append(f"Failed to create folder for {course.name}: {e}")
                    continue
            
            try:
                link = await self._drive.upload_file_bytes(
                    file_bytes=file_bytes,
                    file_name=file_name,
                    mime_type=mime_type,
                    folder_id=course.materials_folder_id,
                )
                links.append(link)
                logger.info(f"Uploaded {file_name} to course {course.name}")
            except Exception as e:
                errors.append(f"Failed to upload to {course.name}: {e}")
        
        if links:
            return UploadResult(
                success=True,
                links=links,
                shareable_link=links[0] if len(links) == 1 else None,
                error="; ".join(errors) if errors else None,
            )
        else:
            return UploadResult(
                success=False,
                error="; ".join(errors) if errors else "Failed to upload to any course",
            )


class GetMaterialsUseCase:
    """Get course materials from Google Drive."""
    
    def __init__(
        self,
        drive_adapter: GoogleDriveAdapter,
        course_repo: ICourseRepository,
    ):
        self._drive = drive_adapter
        self._course_repo = course_repo
    
    async def execute(self, course_id: str) -> List[dict]:
        """Get materials for a course."""
        course = await self._course_repo.get_by_id(course_id)
        if course is None or course.materials_folder_id is None:
            return []
        
        try:
            return await self._drive.list_files(course.materials_folder_id)
        except Exception as e:
            logger.error(f"Failed to get materials: {e}")
            return []


# ============================================================================
# Post Publishing Use Cases
# ============================================================================

@dataclass
class PublishPostResult:
    """Result of publishing a post."""
    success: bool
    facebook_result: Optional[PublishResult] = None
    instagram_result: Optional[PublishResult] = None
    error: Optional[str] = None
    skipped_instagram: bool = False


class PublishPostUseCase:
    """Publish a post to social media."""
    
    def __init__(self, meta_adapter: MetaGraphAdapter):
        self._meta = meta_adapter
    
    async def execute(self, post: ScheduledPost) -> PublishPostResult:
        """
        Publish a scheduled post to the specified platform(s).
        
        Note: Instagram posts without images are skipped and logged as errors.
        """
        # Validate Instagram posts
        validation_error = post.validate_for_instagram()
        if validation_error:
            if post.platform == Platform.INSTAGRAM:
                return PublishPostResult(
                    success=False,
                    error=validation_error,
                    skipped_instagram=True,
                )
            elif post.platform == Platform.BOTH:
                logger.warning(f"Post {post.id}: {validation_error}, publishing to Facebook only")
        
        facebook_result = None
        instagram_result = None
        
        # Publish to Facebook
        if post.platform in (Platform.FACEBOOK, Platform.BOTH):
            facebook_result = await self._meta.publish_to_facebook(
                content=post.content,
                image_url=post.image_url,
            )
        
        # Publish to Instagram (only if image is available)
        if post.platform in (Platform.INSTAGRAM, Platform.BOTH) and post.can_publish_to_instagram():
            instagram_result = await self._meta.publish_to_instagram(
                image_url=post.image_url,
                caption=post.content,
            )
        
        # Determine overall success
        success = True
        if post.platform == Platform.FACEBOOK:
            success = facebook_result.success if facebook_result else False
        elif post.platform == Platform.INSTAGRAM:
            success = instagram_result.success if instagram_result else False
        else:  # BOTH
            success = (
                (facebook_result.success if facebook_result else False) and
                (instagram_result.success if instagram_result and post.can_publish_to_instagram() else True)
            )
        
        return PublishPostResult(
            success=success,
            facebook_result=facebook_result,
            instagram_result=instagram_result,
            skipped_instagram=not post.can_publish_to_instagram() and post.platform in (Platform.INSTAGRAM, Platform.BOTH),
        )


class CheckAndPublishPostsUseCase:
    """Check for due posts and publish them."""
    
    def __init__(
        self,
        sheets_adapter: GoogleSheetsAdapter,
        publish_use_case: PublishPostUseCase,
        on_success_callback: Optional[callable] = None,
        on_error_callback: Optional[callable] = None,
    ):
        self._sheets = sheets_adapter
        self._publish = publish_use_case
        self._on_success = on_success_callback
        self._on_error = on_error_callback
    
    async def execute(self) -> int:
        """
        Check for pending posts and publish those that are due.
        Returns the number of successfully published posts.
        """
        try:
            posts = await self._sheets.get_scheduled_posts()
        except Exception as e:
            error_msg = f"Failed to fetch posts from Google Sheets: {e}"
            logger.error(error_msg)
            if self._on_error:
                await self._on_error(error_msg)
            return 0
        
        published_count = 0
        
        for post in posts:
            # Check if post is due (current Syria time >= scheduled time)
            if not is_past_or_now(post.scheduled_datetime):
                continue
            
            # Publish the post
            result = await self._publish.execute(post)
            
            if result.success:
                # Mark as published in Google Sheets
                try:
                    await self._sheets.mark_post_published(post.sheet_row_index)
                    published_count += 1
                    logger.info(f"Published post row {post.sheet_row_index}")
                    
                    if self._on_success:
                        await self._on_success(post, result)
                except Exception as e:
                    logger.error(f"Failed to mark post as published: {e}")
            else:
                error_msg = result.error or "Unknown error"
                logger.error(f"Failed to publish post row {post.sheet_row_index}: {error_msg}")
                
                try:
                    await self._sheets.add_error_note(post.sheet_row_index, error_msg)
                except Exception as e:
                    logger.error(f"Failed to add error note: {e}")
                
                if self._on_error:
                    await self._on_error(f"Failed to publish post: {error_msg}")
        
        return published_count


# ============================================================================
# Language Preference Use Cases
# ============================================================================

class SetLanguageUseCase:
    """Set user language preference."""
    
    def __init__(self, prefs_repo: IUserPreferencesRepository):
        self._prefs_repo = prefs_repo
    
    async def execute(self, telegram_id: int, language: Language) -> UserPreferences:
        """Set the language preference for a user."""
        return await self._prefs_repo.set_language(telegram_id, language)


class GetLanguageUseCase:
    """Get user language preference."""
    
    def __init__(self, prefs_repo: IUserPreferencesRepository):
        self._prefs_repo = prefs_repo
    
    async def execute(self, telegram_id: int) -> Language:
        """Get the language preference for a user, defaulting to Arabic."""
        prefs = await self._prefs_repo.get_by_telegram_id(telegram_id)
        return prefs.language if prefs else Language.ARABIC


# ============================================================================
# Broadcasting Use Cases
# ============================================================================

@dataclass
class BroadcastResult:
    """Result of a broadcast."""
    total_users: int
    successful: int
    failed: int


class BroadcastMessageUseCase:
    """Broadcast a message to all users."""
    
    def __init__(
        self,
        prefs_repo: IUserPreferencesRepository,
        student_repo: IStudentRepository,
    ):
        self._prefs_repo = prefs_repo
        self._student_repo = student_repo
        self._send_message_callback: Optional[callable] = None
    
    def set_send_callback(self, callback: callable) -> None:
        """Set the callback for sending messages."""
        self._send_message_callback = callback
    
    async def execute(self, message: str) -> BroadcastResult:
        """Broadcast a message to all students with notifications enabled."""
        if self._send_message_callback is None:
            raise RuntimeError("Send message callback not set")
        
        # Get all students
        students = await self._student_repo.get_all()
        
        # Filter by notification preferences
        notified_users = []
        for student in students:
            prefs = await self._prefs_repo.get_by_telegram_id(student.telegram_id)
            if prefs is None or prefs.notifications_enabled:
                notified_users.append(student)
        
        successful = 0
        failed = 0
        
        for student in notified_users:
            try:
                await self._send_message_callback(student.telegram_id, message)
                successful += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {student.telegram_id}: {e}")
                failed += 1
        
        return BroadcastResult(
            total_users=len(notified_users),
            successful=successful,
            failed=failed,
        )
