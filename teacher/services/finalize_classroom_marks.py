# =========================================================
# FINALIZE CLASSROOM MARKS
# Uses Last Attempt Only
# =========================================================
from django.utils import timezone
from teacher.models import Submission
from teacher.services.final_mark_calculator import FinalMarkCalculator


class ClassroomFinalizer:

    @staticmethod
    def finalize(classroom):
        """
        Finalizes marks for all students in a classroom
        using their LAST attempt only.

        Runs ONLY if deadline has passed.
        Recalculates automatically if a newer attempt exists.
        """

        # Ensure deadline passed
        if not classroom.deadline or timezone.now() <= classroom.deadline:
            return

        student_ids = (
            Submission.objects
            .filter(classroom=classroom)
            .values_list("student_id", flat=True)
            .distinct()
        )

        for student_id in student_ids:

            # Get latest attempt
            last_submission = (
                Submission.objects
                .filter(classroom=classroom, student_id=student_id)
                .order_by("-attempt_no")
                .first()
            )

            if not last_submission:
                continue

            # Only finalize evaluated submissions
            if last_submission.status != Submission.Status.EVALUATED:
                continue

            # Compute marks
            final_percentage, final_score = (
                FinalMarkCalculator.calculate(last_submission)
            )

            # Always overwrite on latest attempt
            last_submission.final_percentage = final_percentage
            last_submission.final_score = final_score
            last_submission.finalized_at = timezone.now()

            last_submission.save(update_fields=[
                "final_percentage",
                "final_score",
                "finalized_at"
            ])