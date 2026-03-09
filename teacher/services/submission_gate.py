# =========================================================
# SUBMISSION GATE – EduDOC
# Single Source of Truth
# =========================================================

from datetime import timedelta
from django.utils import timezone
from teacher.models import Submission

def get_submission_gate(student, classroom, unlock_active=False):
    # -----------------------------------------------------
    # UNLOCK OVERRIDE (HIGHEST PRIORITY)
    # -----------------------------------------------------
    if unlock_active:
        return {
            "allowed": True,
            "remaining_seconds": 0,
            "attempts_used": 0,
            "attempts_allowed": classroom.attempts_allowed,
        }
    """
    Central attempt limiter logic.

    Returns:
        {
            allowed: bool,
            remaining_seconds: int,
            attempts_used: int,
            attempts_allowed: int,
        }
    """

    now = timezone.now()

    submissions = Submission.objects.filter(
        student=student,
        classroom=classroom
    ).order_by("submitted_at")

    attempts_allowed = classroom.attempts_allowed
    total_submissions = submissions.count()

    # -----------------------------------------------------
    # Allowed immediately
    # -----------------------------------------------------
    if unlock_active or total_submissions < attempts_allowed:
        return {
            "allowed": True,
            "remaining_seconds": 0,
            "attempts_used": total_submissions,
            "attempts_allowed": attempts_allowed,
        }

    # -----------------------------------------------------
    # Rolling 24h window logic (YOUR EXISTING METHOD)
    # -----------------------------------------------------
    cycle_start_submission = submissions[
        total_submissions - attempts_allowed
    ]

    window_end = cycle_start_submission.submitted_at + timedelta(hours=24)

    if now >= window_end:
        return {
            "allowed": True,
            "remaining_seconds": 0,
            "attempts_used": total_submissions,
            "attempts_allowed": attempts_allowed,
        }

    remaining_seconds = int((window_end - now).total_seconds())

    return {
        "allowed": False,
        "remaining_seconds": max(0, remaining_seconds),
        "attempts_used": total_submissions,
        "attempts_allowed": attempts_allowed,
    }