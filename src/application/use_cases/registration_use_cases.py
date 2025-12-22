"""
Registration-related use cases for managing course registrations.
Following Clean Architecture principles with proper dependency injection.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

from domain.entities import (
    Student, Registration, Course, PaymentRecord,
    RegistrationStatus, PaymentStatus, PaymentMethod,
)
from domain.repositories import (
    IStudentRepository, IRegistrationRepository, ICourseRepository,
    IPaymentRecordRepository,
)
from domain.value_objects import now_syria


# ============================================================================
# Result Dataclasses
# ============================================================================

@dataclass
class RegistrationRequestResult:
    """Result of a registration request."""
    success: bool
    registration: Optional[Registration] = None
    student: Optional[Student] = None
    error: Optional[str] = None


@dataclass
class ApprovalResult:
    """Result of approval/rejection."""
    success: bool
    registration: Optional[Registration] = None
    error: Optional[str] = None


@dataclass
class PaymentResult:
    """Result of payment operation."""
    success: bool
    payment: Optional[PaymentRecord] = None
    total_paid: float = 0.0
    error: Optional[str] = None


# ============================================================================
# Registration Use Cases
# ============================================================================

class RequestRegistrationUseCase:
    """
    Handle course registration requests from students.
    Creates student if not exists, creates pending registration.
    """
    
    def __init__(
        self,
        student_repository: IStudentRepository,
        registration_repository: IRegistrationRepository,
        course_repository: ICourseRepository,
    ):
        self._student_repo = student_repository
        self._registration_repo = registration_repository
        self._course_repo = course_repository
    
    async def execute(
        self,
        telegram_id: int,
        full_name: str,
        phone_number: str,
        course_id: str,
    ) -> RegistrationRequestResult:
        """Execute registration request."""
        try:
            # Validate course exists
            course = await self._course_repo.get_by_id(course_id)
            if not course:
                return RegistrationRequestResult(
                    success=False,
                    error="Course not found"
                )
            
            # Get or create student
            student = await self._student_repo.get_by_telegram_id(telegram_id)
            if student:
                # Update name and phone if changed
                student.full_name = full_name
                student.phone_number = phone_number
                await self._student_repo.save(student)
            else:
                student = Student.create(
                    telegram_id=telegram_id,
                    full_name=full_name,
                    phone_number=phone_number,
                    now=now_syria(),
                )
                await self._student_repo.save(student)
            
            # Check if already registered
            existing = await self._registration_repo.get_by_student_and_course(
                student.id, course_id
            )
            if existing:
                return RegistrationRequestResult(
                    success=False,
                    error="Already registered for this course"
                )
            
            # Check course capacity
            count = await self._registration_repo.count_by_course(course_id)
            if count >= course.max_students:
                return RegistrationRequestResult(
                    success=False,
                    error="Course is full"
                )
            
            # Create registration
            registration = Registration.create(
                student_id=student.id,
                course_id=course_id,
                now=now_syria(),
            )
            await self._registration_repo.save(registration)
            
            return RegistrationRequestResult(
                success=True,
                registration=registration,
                student=student,
            )
            
        except Exception as e:
            return RegistrationRequestResult(
                success=False,
                error=str(e)
            )


class ApproveRegistrationUseCase:
    """Approve a pending registration."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
    ):
        self._registration_repo = registration_repository
    
    async def execute(
        self,
        registration_id: str,
        admin_telegram_id: int,
        notes: Optional[str] = None,
    ) -> ApprovalResult:
        """Approve registration."""
        try:
            registration = await self._registration_repo.get_by_id(registration_id)
            if not registration:
                return ApprovalResult(success=False, error="Registration not found")
            
            if registration.status != RegistrationStatus.PENDING:
                return ApprovalResult(
                    success=False,
                    error=f"Registration is not pending (status: {registration.status.value})"
                )
            
            registration.status = RegistrationStatus.APPROVED
            registration.approved_at = now_syria()
            registration.approved_by = admin_telegram_id
            if notes:
                registration.notes = notes
            
            await self._registration_repo.save(registration)
            
            return ApprovalResult(success=True, registration=registration)
            
        except Exception as e:
            return ApprovalResult(success=False, error=str(e))


class RejectRegistrationUseCase:
    """Reject a pending registration."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
    ):
        self._registration_repo = registration_repository
    
    async def execute(
        self,
        registration_id: str,
        admin_telegram_id: int,
        reason: Optional[str] = None,
    ) -> ApprovalResult:
        """Reject registration."""
        try:
            registration = await self._registration_repo.get_by_id(registration_id)
            if not registration:
                return ApprovalResult(success=False, error="Registration not found")
            
            if registration.status != RegistrationStatus.PENDING:
                return ApprovalResult(
                    success=False,
                    error=f"Registration is not pending (status: {registration.status.value})"
                )
            
            registration.status = RegistrationStatus.REJECTED
            registration.approved_at = now_syria()
            registration.approved_by = admin_telegram_id
            registration.notes = reason or "Rejected by admin"
            
            await self._registration_repo.save(registration)
            
            return ApprovalResult(success=True, registration=registration)
            
        except Exception as e:
            return ApprovalResult(success=False, error=str(e))


class GetPendingRegistrationsUseCase:
    """Get all pending registrations."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
        student_repository: IStudentRepository,
        course_repository: ICourseRepository,
    ):
        self._registration_repo = registration_repository
        self._student_repo = student_repository
        self._course_repo = course_repository
    
    async def execute(self) -> List[dict]:
        """Get pending registrations with student and course info."""
        registrations = await self._registration_repo.get_by_status(
            RegistrationStatus.PENDING
        )
        
        result = []
        for reg in registrations:
            student = await self._student_repo.get_by_id(reg.student_id)
            course = await self._course_repo.get_by_id(reg.course_id)
            
            result.append({
                "registration": reg,
                "student": student,
                "course": course,
            })
        
        return result


# ============================================================================
# Payment Use Cases
# ============================================================================

class AddPaymentUseCase:
    """Add a payment record for a registration."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
        payment_repository: IPaymentRecordRepository,
        course_repository: ICourseRepository,
    ):
        self._registration_repo = registration_repository
        self._payment_repo = payment_repository
        self._course_repo = course_repository
    
    async def execute(
        self,
        registration_id: str,
        amount: float,
        method: PaymentMethod,
        admin_telegram_id: int,
        notes: Optional[str] = None,
    ) -> PaymentResult:
        """Add payment and update payment status."""
        try:
            # Validate registration
            registration = await self._registration_repo.get_by_id(registration_id)
            if not registration:
                return PaymentResult(success=False, error="Registration not found")
            
            if registration.status != RegistrationStatus.APPROVED:
                return PaymentResult(
                    success=False,
                    error="Can only add payments to approved registrations"
                )
            
            # Get course price
            course = await self._course_repo.get_by_id(registration.course_id)
            if not course:
                return PaymentResult(success=False, error="Course not found")
            
            # Create payment record
            payment = PaymentRecord.create(
                registration_id=registration_id,
                amount=amount,
                method=method,
                received_by=admin_telegram_id,
                now=now_syria(),
                notes=notes,
            )
            await self._payment_repo.save(payment)
            
            # Calculate total paid and update status
            total_paid = await self._payment_repo.get_total_paid(registration_id)
            
            if total_paid >= course.price:
                registration.payment_status = PaymentStatus.PAID
            elif total_paid > 0:
                registration.payment_status = PaymentStatus.PARTIAL
            
            await self._registration_repo.save(registration)
            
            return PaymentResult(
                success=True,
                payment=payment,
                total_paid=total_paid,
            )
            
        except Exception as e:
            return PaymentResult(success=False, error=str(e))


class GetPaymentHistoryUseCase:
    """Get payment history for a registration."""
    
    def __init__(
        self,
        payment_repository: IPaymentRecordRepository,
    ):
        self._payment_repo = payment_repository
    
    async def execute(self, registration_id: str) -> List[PaymentRecord]:
        """Get all payments for a registration."""
        return await self._payment_repo.get_by_registration(registration_id)


class GetCourseStudentsUseCase:
    """Get all students registered for a course."""
    
    def __init__(
        self,
        registration_repository: IRegistrationRepository,
        student_repository: IStudentRepository,
        payment_repository: IPaymentRecordRepository,
        course_repository: ICourseRepository,
    ):
        self._registration_repo = registration_repository
        self._student_repo = student_repository
        self._payment_repo = payment_repository
        self._course_repo = course_repository
    
    async def execute(self, course_id: str) -> List[dict]:
        """Get students with their registration and payment info."""
        course = await self._course_repo.get_by_id(course_id)
        if not course:
            return []
        
        registrations = await self._registration_repo.get_by_course(course_id)
        
        result = []
        for reg in registrations:
            student = await self._student_repo.get_by_id(reg.student_id)
            total_paid = await self._payment_repo.get_total_paid(reg.id)
            
            result.append({
                "student": student,
                "registration": reg,
                "total_paid": total_paid,
                "remaining": max(0, course.price - total_paid),
                "course": course,
            })
        
        return result
