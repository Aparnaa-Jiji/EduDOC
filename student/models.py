from django.db import models
from django.conf import settings


from datetime import date


def current_academic_year():
    """
    Returns academic year in format YYYY-YY

    Example:
        2026 -> 2026-27
    """
    year = date.today().year
    next_year_short = str(year + 1)[-2:]
    return f"{year}-{next_year_short}"

# =====================================================
# Batch Model – Academic Structure
# =====================================================
class Batch(models.Model):
    """
    Represents an institutional academic batch.

    Examples:
        S1 MCA – 2025-26
        S2 BCA – 2025-26
    """

    name = models.CharField(max_length=100)  # S1 MCA
    academic_year = models.CharField(
        max_length=9,
        default=current_academic_year
    )


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "academic_year")
        ordering = ["-academic_year", "name"]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


# =====================================================
# Student Profile
# =====================================================
class Student(models.Model):
    """
    Student profile (1-to-1 with User)
    Must belong to exactly one batch.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,  # prevents accidental deletion
        related_name="students"
    )


    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]
        indexes = [
    models.Index(fields=["batch"]),
]


    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"



# =====================================================
# Classroom Membership
# =====================================================
class ClassroomMembership(models.Model):
    """
    Student enrollment into classroom.
    Stores per-student submission controls.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="memberships"
    )

    classroom = models.ForeignKey(
        "teacher.Classroom",
        on_delete=models.CASCADE,
        related_name="student_memberships"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    # submission rules
    attempts_allowed = models.IntegerField(default=3)
    cooldown_minutes = models.IntegerField(default=10)

    # lock state
    is_locked = models.BooleanField(default=False)
    locked_until = models.DateTimeField(null=True, blank=True)

    # =====================================================
    # Personal Unlock (Deadline Override)
    # =====================================================

    unlock_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Temporary personal unlock window"
    )

    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="membership_unlocks"
    )

    unlock_note = models.TextField(
        blank=True,
        help_text="Teacher decision note (optional)"
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "classroom"],
                name="unique_student_classroom"
            )
        ]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["classroom"]),
        ]

    def __str__(self):
        return f"{self.student} -> {self.classroom.name}"


# =====================================================
# Unlock Request
# =====================================================
class UnlockRequest(models.Model):
    """
    Student requests additional attempt.
    Teacher approves/rejects.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="unlock_requests"
    )

    classroom = models.ForeignKey(
        "teacher.Classroom",
        on_delete=models.CASCADE,
        related_name="unlock_requests"
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="decided_unlock_requests"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} -> {self.classroom.name} ({self.status})"
