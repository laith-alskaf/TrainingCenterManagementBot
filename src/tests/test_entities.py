"""
Unit tests for domain entities.
"""
import pytest
from datetime import datetime
import pytz

from  domain.entities import (
    Course, Student, Registration, ScheduledPost, UserPreferences,
    CourseStatus, RegistrationStatus, PostStatus, Platform, Language,
)
from  domain.value_objects import SYRIA_TZ, now_syria


class TestCourse:
    """Tests for Course entity."""
    
    def test_create_course(self):
        """Test course creation with factory method."""
        now = now_syria()
        start = now.replace(day=1)
        end = now.replace(day=28)
        
        course = Course.create(
            name="Python Basics",
            description="Learn Python programming",
            instructor="John Doe",
            start_date=start,
            end_date=end,
            price=100.0,
            max_students=20,
            now=now,
        )
        
        assert course.id is not None
        assert course.name == "Python Basics"
        assert course.status == CourseStatus.DRAFT
        assert course.created_at == now
        assert course.start_date.tzinfo is not None
    
    def test_course_statuses(self):
        """Test course status enum values."""
        assert CourseStatus.DRAFT.value == "draft"
        assert CourseStatus.PUBLISHED.value == "published"
        assert CourseStatus.ONGOING.value == "ongoing"
        assert CourseStatus.COMPLETED.value == "completed"


class TestStudent:
    """Tests for Student entity."""
    
    def test_create_student(self):
        """Test student creation with factory method."""
        now = now_syria()
        
        student = Student.create(
            telegram_id=123456789,
            name="Ahmed Ali",
            now=now,
            phone="+963912345678",
            email="ahmed@example.com",
        )
        
        assert student.id is not None
        assert student.telegram_id == 123456789
        assert student.name == "Ahmed Ali"
        assert student.language == Language.ARABIC
        assert student.registered_at == now
    
    def test_student_default_language(self):
        """Test student defaults to Arabic language."""
        now = now_syria()
        student = Student.create(telegram_id=1, name="Test", now=now)
        assert student.language == Language.ARABIC


class TestScheduledPost:
    """Tests for ScheduledPost entity."""
    
    def test_create_post(self):
        """Test scheduled post creation."""
        now = now_syria()
        
        post = ScheduledPost.create(
            content="Hello World!",
            scheduled_datetime=now,
            platform=Platform.FACEBOOK,
        )
        
        assert post.id is not None
        assert post.content == "Hello World!"
        assert post.status == PostStatus.PENDING
        assert post.scheduled_datetime.tzinfo is not None
    
    def test_instagram_requires_image(self):
        """Test that Instagram posts require images."""
        now = now_syria()
        
        # Instagram without image
        post = ScheduledPost.create(
            content="Test",
            scheduled_datetime=now,
            platform=Platform.INSTAGRAM,
            image_url=None,
        )
        
        assert post.requires_image() is True
        assert post.can_publish_to_instagram() is False
        
        error = post.validate_for_instagram()
        assert error is not None
        assert "image_url" in error.lower()
    
    def test_instagram_with_image(self):
        """Test Instagram post with valid image."""
        now = now_syria()
        
        post = ScheduledPost.create(
            content="Test",
            scheduled_datetime=now,
            platform=Platform.INSTAGRAM,
            image_url="https://example.com/image.jpg",
        )
        
        assert post.can_publish_to_instagram() is True
        assert post.validate_for_instagram() is None
    
    def test_facebook_allows_text_only(self):
        """Test Facebook posts can be text-only."""
        now = now_syria()
        
        post = ScheduledPost.create(
            content="Test",
            scheduled_datetime=now,
            platform=Platform.FACEBOOK,
        )
        
        assert post.requires_image() is False
        assert post.validate_for_instagram() is None
    
    def test_both_platforms_image_validation(self):
        """Test 'both' platform validates Instagram requirement."""
        now = now_syria()
        
        # Without image
        post = ScheduledPost.create(
            content="Test",
            scheduled_datetime=now,
            platform=Platform.BOTH,
        )
        
        assert post.requires_image() is True
        assert post.validate_for_instagram() is not None
        
        # With image
        post_with_image = ScheduledPost.create(
            content="Test",
            scheduled_datetime=now,
            platform=Platform.BOTH,
            image_url="https://example.com/image.jpg",
        )
        
        assert post_with_image.validate_for_instagram() is None


class TestUserPreferences:
    """Tests for UserPreferences entity."""
    
    def test_create_preferences(self):
        """Test user preferences creation."""
        prefs = UserPreferences.create(
            telegram_id=123456789,
            language=Language.ENGLISH,
        )
        
        assert prefs.telegram_id == 123456789
        assert prefs.language == Language.ENGLISH
        assert prefs.notifications_enabled is True
    
    def test_default_preferences(self):
        """Test default language is Arabic."""
        prefs = UserPreferences.create(telegram_id=1)
        assert prefs.language == Language.ARABIC
