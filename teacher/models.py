# ======================================================
# TEACHER MODELS – EduDOC (Production Grade)
# Stable • Backward Compatible • Non-Breaking Cleanup
# ======================================================

from django.db import models
from django.conf import settings
import uuid


# ======================================================
# CLASSROOM MODEL
# Classroom == Assignment Entity
# ======================================================

class Classroom(models.Model):
    """
    Core Academic Container.

    Architecture:
        Teacher → Classroom → Submission

    A Classroom represents:
        • Assignment
        • Evaluation configuration
        • Rule storage
        • Submission control system

    NOTE:
    Some legacy fields remain intentionally
    for backward compatibility.
    """

    # --------------------------------------------------
    # BASIC INFORMATION
    # --------------------------------------------------

    name = models.CharField(max_length=200)

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "TEACHER"},
        related_name="classrooms",
    )

    # --------------------------------------------------
    # Batch Scoping (ADMIN CONTROLLED)
    # --------------------------------------------------
    batch = models.ForeignKey(
        "student.Batch",
        on_delete=models.CASCADE,
    )

    passkey = models.CharField(
        max_length=10,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # --------------------------------------------------
    # ACADEMIC SETTINGS
    # --------------------------------------------------

    deadline = models.DateTimeField()
    max_marks = models.IntegerField(default=100)

    # --------------------------------------------------
    # LEGACY FIELD (kept to avoid migration break)
    # --------------------------------------------------
    guideline_file = models.FileField(
        upload_to="guidelines/",
        null=True,
        blank=True,
        help_text="Legacy field retained for DB compatibility."
    )

    # --------------------------------------------------
    # RULE ENGINE CONFIGURATION
    # --------------------------------------------------

    # NOTE:
    # rules_locked declared once intentionally.
    # Previous duplicate definitions cleaned.

    rules_locked = models.BooleanField(default=False)

    attempts_allowed = models.PositiveIntegerField(default=3)
    cooldown_minutes = models.PositiveIntegerField(default=10)

    rules_version = models.PositiveIntegerField(default=0)

    rules_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Stores structured compliance rules."
    )

    plagiarism_enabled = models.BooleanField(default=True)
    format_check_enabled = models.BooleanField(default=True)

    # --------------------------------------------------
    # LEGACY CONFIRMATION FLAG
    # --------------------------------------------------
    rules_confirmed = models.BooleanField(
        default=False,
        help_text="Legacy confirmation flag (non-critical)."
    )

    # --------------------------------------------------
    # SAFE PASSKEY GENERATION
    # --------------------------------------------------
    def save(self, *args, **kwargs):
        """
        Generates unique classroom passkey once.
        Collision-safe UUID slicing.
        """
        if not self.passkey:
            while True:
                key = uuid.uuid4().hex[:8].upper()
                if not Classroom.objects.filter(passkey=key).exists():
                    self.passkey = key
                    break

        super().save(*args, **kwargs)

    # --------------------------------------------------
    # META OPTIMIZATION
    # --------------------------------------------------
    class Meta:
        indexes = [
            models.Index(fields=["batch"]),
            models.Index(fields=["teacher"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.teacher.username})"


# ======================================================
# SUBMISSION MODEL
# ======================================================

class Submission(models.Model):
    """
    Represents a student's upload attempt.

    Evaluation Pipeline:
        Upload → Processing → Evaluation → Report → Archive
    """

    # --------------------------------------------------
    # STATUS ENUM
    # --------------------------------------------------
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUBMITTED = "SUBMITTED", "Submitted"
        PROCESSING = "PROCESSING", "Processing"
        ERROR = "ERROR", "Error"
        EVALUATED = "EVALUATED", "Evaluated"

    # --------------------------------------------------
    # RELATIONS
    # --------------------------------------------------

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        "student.Student",
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    # --------------------------------------------------
    # ATTEMPT TRACKING
    # --------------------------------------------------

    attempt_no = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True)

    # --------------------------------------------------
    # FILE STORAGE
    # --------------------------------------------------

    file = models.FileField(upload_to="submissions/")

    annotated_file = models.FileField(
        upload_to="submissions/annotated/",
        null=True,
        blank=True
    )

    # --------------------------------------------------
    # SCORING SYSTEM
    # --------------------------------------------------
        # ---------------------------------------
    # FINALIZATION CONTROL (NEW)
    # ---------------------------------------

    # --------------------------------------------------
    # SCORING SYSTEM
    # --------------------------------------------------

    # FINALIZATION CONTROL
    final_percentage = models.FloatField(
        null=True,
        blank=True,
        help_text="Final computed percentage (0-100)"
    )

    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when marks were finalized"
    )

    score = models.FloatField(null=True, blank=True)
    penalty = models.FloatField(default=0)

    final_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    plagiarism_percent = models.FloatField(null=True, blank=True)
    compliance_percent = models.FloatField(null=True, blank=True)

    # Detailed evaluation audit
    breakdown_json = models.JSONField(
        default=dict,
        blank=True,
        null=True,
    )

    report_path = models.FileField(
        upload_to="reports/",
        null=True,
        blank=True
    )

    # --------------------------------------------------
    # PROCESS STATUS
    # --------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # --------------------------------------------------
    # DATABASE CONSTRAINTS
    # --------------------------------------------------

    class Meta:
        ordering = ["-submitted_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "student", "attempt_no"],
                name="unique_attempt_per_student"
            )
        ]

        indexes = [
            models.Index(fields=["classroom"]),
            models.Index(fields=["student"]),
            models.Index(fields=["submitted_at"]),
            models.Index(fields=["student", "classroom"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.classroom.name} (Attempt {self.attempt_no})"

    # --------------------------------------------------
    # SAFE RULE ACCESSOR (Backward Compatible)
    # --------------------------------------------------
    def get_rules(self):
        """
        Returns rules safely.

        New system:
            Uses classroom.rules_json

        Legacy guideline relation may not exist,
        so fallback logic prevents runtime crashes.
        """
        if self.classroom.rules_json:
            return self.classroom.rules_json

        return {}


# ======================================================
# GUIDELINE DRAFT MODEL (LEGACY)
# ======================================================

class GuidelineDraft(models.Model):
    """
    Legacy extraction preview model.

    Retained ONLY to prevent migration conflicts.
    Not required in manual-rule architecture.
    """

    classroom = models.ForeignKey(
        "teacher.Classroom",
        on_delete=models.CASCADE,
        related_name="rule_drafts"
    )

    uploaded_file = models.FileField(upload_to="guidelines/drafts/")
    extracted_rules = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

