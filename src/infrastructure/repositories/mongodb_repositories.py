"""
MongoDB repository implementations.
"""
from typing import List, Optional
from datetime import datetime

from domain.entities import (
    Course, Student, Registration, ScheduledPost, UserPreferences,
    CourseStatus, RegistrationStatus, PostStatus, Language,
)
from domain.repositories import (
    ICourseRepository, IStudentRepository, IRegistrationRepository,
    IUserPreferencesRepository, IScheduledPostRepository,
)
from domain.value_objects import datetime_to_mongodb, datetime_from_mongodb, now_syria
from infrastructure.database import MongoDB


class MongoDBCourseRepository(ICourseRepository):
    """MongoDB implementation of course repository."""
    
    COLLECTION = "courses"
    
    def _to_document(self, course: Course) -> dict:
        """Convert course entity to MongoDB document."""
        return {
            "_id": course.id,
            "name": course.name,
            "description": course.description,
            "instructor": course.instructor,
            "start_date": datetime_to_mongodb(course.start_date) if course.start_date else None,
            "end_date": datetime_to_mongodb(course.end_date) if course.end_date else None,
            "price": course.price,
            "max_students": course.max_students,
            "status": course.status.value,
            "created_at": datetime_to_mongodb(course.created_at) if course.created_at else None,
            "updated_at": datetime_to_mongodb(course.updated_at) if course.updated_at else None,
            "materials_folder_id": course.materials_folder_id,
            "target_audience": course.target_audience,
            "duration_hours": course.duration_hours,
        }
    
    def _from_document(self, doc: dict) -> Course:
        """Convert MongoDB document to course entity."""
        return Course(
            id=doc["_id"],
            name=doc["name"],
            description=doc["description"],
            instructor=doc["instructor"],
            start_date=datetime_from_mongodb(doc["start_date"]) if doc.get("start_date") else None,
            end_date=datetime_from_mongodb(doc["end_date"]) if doc.get("end_date") else None,
            price=doc["price"],
            max_students=doc["max_students"],
            status=CourseStatus(doc["status"]),
            created_at=datetime_from_mongodb(doc["created_at"]) if doc.get("created_at") else None,
            updated_at=datetime_from_mongodb(doc["updated_at"]) if doc.get("updated_at") else None,
            materials_folder_id=doc.get("materials_folder_id"),
            target_audience=doc.get("target_audience"),
            duration_hours=doc.get("duration_hours"),
        )
    
    async def get_by_id(self, course_id: str) -> Optional[Course]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({"_id": course_id})
        return self._from_document(doc) if doc else None
    
    async def get_all(self) -> List[Course]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({})
        return [self._from_document(doc) async for doc in cursor]
    
    async def get_available(self) -> List[Course]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({
            "status": {"$in": [CourseStatus.PUBLISHED.value, CourseStatus.ONGOING.value]}
        })
        return [self._from_document(doc) async for doc in cursor]
    
    async def save(self, course: Course) -> Course:
        collection = MongoDB.get_collection(self.COLLECTION)
        await collection.replace_one(
            {"_id": course.id},
            self._to_document(course),
            upsert=True
        )
        return course
    
    async def delete(self, course_id: str) -> bool:
        collection = MongoDB.get_collection(self.COLLECTION)
        result = await collection.delete_one({"_id": course_id})
        return result.deleted_count > 0


class MongoDBStudentRepository(IStudentRepository):
    """MongoDB implementation of student repository."""
    
    COLLECTION = "students"
    
    def _to_document(self, student: Student) -> dict:
        """Convert student entity to MongoDB document."""
        return {
            "_id": student.id,
            "telegram_id": student.telegram_id,
            "name": student.name,
            "phone": student.phone,
            "email": student.email,
            "language": student.language.value,
            "registered_at": datetime_to_mongodb(student.registered_at) if student.registered_at else None,
        }
    
    def _from_document(self, doc: dict) -> Student:
        """Convert MongoDB document to student entity."""
        return Student(
            id=doc["_id"],
            telegram_id=doc["telegram_id"],
            name=doc["name"],
            phone=doc.get("phone"),
            email=doc.get("email"),
            language=Language(doc.get("language", "ar")),
            registered_at=datetime_from_mongodb(doc["registered_at"]) if doc.get("registered_at") else None,
        )
    
    async def get_by_id(self, student_id: str) -> Optional[Student]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({"_id": student_id})
        return self._from_document(doc) if doc else None
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Student]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({"telegram_id": telegram_id})
        return self._from_document(doc) if doc else None
    
    async def get_all(self) -> List[Student]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({})
        return [self._from_document(doc) async for doc in cursor]
    
    async def save(self, student: Student) -> Student:
        collection = MongoDB.get_collection(self.COLLECTION)
        await collection.replace_one(
            {"_id": student.id},
            self._to_document(student),
            upsert=True
        )
        return student
    
    async def delete(self, student_id: str) -> bool:
        collection = MongoDB.get_collection(self.COLLECTION)
        result = await collection.delete_one({"_id": student_id})
        return result.deleted_count > 0


class MongoDBRegistrationRepository(IRegistrationRepository):
    """MongoDB implementation of registration repository."""
    
    COLLECTION = "registrations"
    
    def _to_document(self, registration: Registration) -> dict:
        """Convert registration entity to MongoDB document."""
        return {
            "_id": registration.id,
            "student_id": registration.student_id,
            "course_id": registration.course_id,
            "status": registration.status.value,
            "registered_at": datetime_to_mongodb(registration.registered_at) if registration.registered_at else None,
            "confirmed_at": datetime_to_mongodb(registration.confirmed_at) if registration.confirmed_at else None,
        }
    
    def _from_document(self, doc: dict) -> Registration:
        """Convert MongoDB document to registration entity."""
        return Registration(
            id=doc["_id"],
            student_id=doc["student_id"],
            course_id=doc["course_id"],
            status=RegistrationStatus(doc["status"]),
            registered_at=datetime_from_mongodb(doc["registered_at"]) if doc.get("registered_at") else None,
            confirmed_at=datetime_from_mongodb(doc["confirmed_at"]) if doc.get("confirmed_at") else None,
        )
    
    async def get_by_id(self, registration_id: str) -> Optional[Registration]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({"_id": registration_id})
        return self._from_document(doc) if doc else None
    
    async def get_by_student_and_course(
        self, student_id: str, course_id: str
    ) -> Optional[Registration]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({
            "student_id": student_id,
            "course_id": course_id,
        })
        return self._from_document(doc) if doc else None
    
    async def get_by_student(self, student_id: str) -> List[Registration]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({"student_id": student_id})
        return [self._from_document(doc) async for doc in cursor]
    
    async def get_by_course(self, course_id: str) -> List[Registration]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({"course_id": course_id})
        return [self._from_document(doc) async for doc in cursor]
    
    async def count_by_course(self, course_id: str) -> int:
        collection = MongoDB.get_collection(self.COLLECTION)
        return await collection.count_documents({
            "course_id": course_id,
            "status": {"$in": [RegistrationStatus.PENDING.value, RegistrationStatus.CONFIRMED.value]}
        })
    
    async def save(self, registration: Registration) -> Registration:
        collection = MongoDB.get_collection(self.COLLECTION)
        await collection.replace_one(
            {"_id": registration.id},
            self._to_document(registration),
            upsert=True
        )
        return registration
    
    async def delete(self, registration_id: str) -> bool:
        collection = MongoDB.get_collection(self.COLLECTION)
        result = await collection.delete_one({"_id": registration_id})
        return result.deleted_count > 0


class MongoDBUserPreferencesRepository(IUserPreferencesRepository):
    """MongoDB implementation of user preferences repository."""
    
    COLLECTION = "user_preferences"
    
    def _to_document(self, prefs: UserPreferences) -> dict:
        """Convert user preferences to MongoDB document."""
        return {
            "_id": prefs.telegram_id,
            "telegram_id": prefs.telegram_id,
            "language": prefs.language.value,
            "notifications_enabled": prefs.notifications_enabled,
        }
    
    def _from_document(self, doc: dict) -> UserPreferences:
        """Convert MongoDB document to user preferences."""
        telegram_id = doc.get("telegram_id") or doc.get("_id")
        return UserPreferences(
            telegram_id=telegram_id,
            language=Language(doc.get("language", "ar")),
            notifications_enabled=doc.get("notifications_enabled", True),
        )
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserPreferences]:
        collection = MongoDB.get_collection(self.COLLECTION)
        doc = await collection.find_one({"_id": telegram_id})
        return self._from_document(doc) if doc else None
    
    async def save(self, prefs: UserPreferences) -> UserPreferences:
        collection = MongoDB.get_collection(self.COLLECTION)
        await collection.replace_one(
            {"_id": prefs.telegram_id},
            self._to_document(prefs),
            upsert=True
        )
        return prefs
    
    async def set_language(self, telegram_id: int, language: Language) -> None:
        """Set language for a user, creating preferences if needed."""
        collection = MongoDB.get_collection(self.COLLECTION)
        prefs = UserPreferences(
            telegram_id=telegram_id,
            language=language,
            notifications_enabled=True,
        )
        await collection.replace_one(
            {"_id": telegram_id},
            self._to_document(prefs),
            upsert=True
        )
    
    async def get_all_with_notifications(self) -> List[UserPreferences]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({"notifications_enabled": True})
        return [self._from_document(doc) async for doc in cursor]


class MongoDBScheduledPostRepository(IScheduledPostRepository):
    """MongoDB implementation of scheduled post repository."""
    
    COLLECTION = "scheduled_posts"
    
    def _to_document(self, post: ScheduledPost) -> dict:
        """Convert scheduled post to MongoDB document."""
        return {
            "_id": post.id,
            "content": post.content,
            "scheduled_datetime": datetime_to_mongodb(post.scheduled_datetime) if post.scheduled_datetime else None,
            "platform": post.platform.value,
            "status": post.status.value,
            "image_url": post.image_url,
            "published_at": datetime_to_mongodb(post.published_at) if post.published_at else None,
            "error_message": post.error_message,
            "sheet_row_index": post.sheet_row_index,
        }
    
    def _from_document(self, doc: dict) -> ScheduledPost:
        """Convert MongoDB document to scheduled post."""
        from domain.entities import Platform, PostStatus
        return ScheduledPost(
            id=doc["_id"],
            content=doc["content"],
            scheduled_datetime=datetime_from_mongodb(doc["scheduled_datetime"]) if doc.get("scheduled_datetime") else None,
            platform=Platform(doc["platform"]),
            status=PostStatus(doc["status"]),
            image_url=doc.get("image_url"),
            published_at=datetime_from_mongodb(doc["published_at"]) if doc.get("published_at") else None,
            error_message=doc.get("error_message"),
            sheet_row_index=doc.get("sheet_row_index"),
        )
    
    async def get_pending(self) -> List[ScheduledPost]:
        collection = MongoDB.get_collection(self.COLLECTION)
        cursor = collection.find({"status": PostStatus.PENDING.value})
        return [self._from_document(doc) async for doc in cursor]
    
    async def save(self, post: ScheduledPost) -> ScheduledPost:
        collection = MongoDB.get_collection(self.COLLECTION)
        await collection.replace_one(
            {"_id": post.id},
            self._to_document(post),
            upsert=True
        )
        return post
