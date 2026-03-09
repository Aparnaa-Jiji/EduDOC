# ======================================================
# ACCOUNTS MODELS – EduDOC (Production Grade)
# Central authority for:
#   • Users
#   • Roles
#   • Approvals
#   • Teacher → Batch assignment (ADMIN controlled)
# ======================================================

from django.contrib.auth.models import AbstractUser
from django.db import models


# ======================================================
# USER MODEL
# ======================================================
class User(AbstractUser):
    """
    Custom User model for EduDOC.

    Extends Django AbstractUser and adds:
    - role based authorization
    - approval workflow
    """

    # ======================================================
    # Role definitions
    # ======================================================
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    # ======================================================
    # Approval system
    # ======================================================
    is_approved = models.BooleanField(default=False)
    first_login = models.BooleanField(default=True)
    # institutional systems should enforce unique emails
    email = models.EmailField(unique=True)

    # ======================================================
    # Business rules
    # ======================================================
    def save(self, *args, **kwargs):

    # -------------------------------------------------
    # Superuser ALWAYS = ADMIN
    # -------------------------------------------------
        if self.is_superuser:
            self.role = self.Role.ADMIN
            self.is_approved = True

    # -------------------------------------------------
    # Students auto-approved
    # -------------------------------------------------
        elif self.role == self.Role.STUDENT:
            self.is_approved = True

    # -------------------------------------------------
    # Teachers require approval
    # -------------------------------------------------
        elif self.role == self.Role.TEACHER:
            if self.is_approved is None:
                self.is_approved = False
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.username} ({self.role})"


# ======================================================
# NEW — Teacher ↔ Batch Assignment
# ======================================================
# IMPORTANT:
# This is ADMIN functionality
# Therefore belongs inside accounts app
# NOT teacher app
# ======================================================

from student.models import Batch


class TeacherBatch(models.Model):
    """
    Administrative mapping.

    Defines which batches a teacher is allowed to handle.

    Security critical:
        All teacher queries must filter using this mapping.

    Controlled ONLY by Admin dashboard.
    """

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": User.Role.TEACHER},
        related_name="assigned_batches"
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="assigned_teachers"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("teacher", "batch")
        indexes = [
            models.Index(fields=["teacher"]),
            models.Index(fields=["batch"]),
        ]

    def __str__(self):
        return f"{self.teacher.username} → {self.batch.name}"

from django.conf import settings
from django.db import models

# accounts/models.py

class TeacherProfile(models.Model):

    class DesignationChoices(models.TextChoices):
        LECTURER = "LECTURER", "Lecturer"
        ASSISTANT_PROF = "ASSISTANT_PROF", "Assistant Professor"
        ASSOCIATE_PROF = "ASSOCIATE_PROF", "Associate Professor"
        PROFESSOR = "PROFESSOR", "Professor"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # Institutional
    department = models.CharField(max_length=150, blank=True)
    designation = models.CharField(
        max_length=30,
        choices=DesignationChoices.choices,
        blank=True
    )

    # Academic Credentials
    highest_qualification = models.CharField(max_length=150, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    qualification_institution = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(null=True, blank=True)

    # Professional Metadata
    phone = models.CharField(max_length=20, blank=True)
    linkedin_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)

    # NEW
    profile_image = models.ImageField(
        upload_to="teacher_profiles/",
        blank=True,
        null=True
    )

    def profile_completion(self):
        fields = [
            self.department,
            self.designation,
            self.highest_qualification,
            self.specialization,
            self.qualification_institution,
            self.experience_years,
            self.phone,
            self.linkedin_url,
            self.website_url,
            self.profile_image,
        ]

        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_teacher_profile(sender, instance, created, **kwargs):
    """
    Automatically create TeacherProfile for every teacher.
    """
    if created and instance.role == User.Role.TEACHER:
        TeacherProfile.objects.create(user=instance)