# =========================================================
# FINAL MARK CALCULATOR
# EduDOC – Deadline-based Weighted Evaluation
# =========================================================

from django.utils import timezone


class FinalMarkCalculator:
    """
    Computes final score after deadline.

    Weight Distribution:
        Compliance  → 50%
        Plagiarism  → 30% (inverted originality)
        Time Factor → 20%
    """

    # -----------------------------
    # WEIGHTS (Editable if needed)
    # -----------------------------
    COMPLIANCE_WEIGHT = 0.50
    PLAGIARISM_WEIGHT = 0.30
    TIME_WEIGHT = 0.20

    @staticmethod
    def calculate(submission):
        """
        Returns:
            final_percentage (0–100)
            final_score (scaled to classroom.max_marks)
        """

        classroom = submission.classroom
        max_marks = classroom.max_marks or 0

        # -------------------------------------------------
        # 1️⃣ Handle No Submission Safety
        # -------------------------------------------------
        if not submission:
            return 0.0, 0.0

        # -------------------------------------------------
        # 2️⃣ Compliance Component (0–100)
        # -------------------------------------------------
        compliance = submission.compliance_percent or 0
        compliance_component = compliance * FinalMarkCalculator.COMPLIANCE_WEIGHT

        # -------------------------------------------------
        # 3️⃣ Plagiarism Component (invert to originality)
        # -------------------------------------------------
        plagiarism = submission.plagiarism_percent or 0
        originality = 100 - plagiarism
        plagiarism_component = originality * FinalMarkCalculator.PLAGIARISM_WEIGHT

        # -------------------------------------------------
        # 4️⃣ Time Component
        # -------------------------------------------------
        deadline = classroom.deadline
        submitted_at = submission.submitted_at

        # Default: 0
        time_score = 0

        if submitted_at and deadline:
            if submitted_at <= deadline:
                time_score = 100  # On-time
            else:
                # Submitted after deadline.
                # Since unlock was approved, treat as 70.
                time_score = 70

        time_component = time_score * FinalMarkCalculator.TIME_WEIGHT

        # -------------------------------------------------
        # 5️⃣ Final Percentage (0–100)
        # -------------------------------------------------
        final_percentage = (
            compliance_component +
            plagiarism_component +
            time_component
        )

        # Ensure safety bounds
        final_percentage = max(0, min(final_percentage, 100))

        # -------------------------------------------------
        # 6️⃣ Scale to Classroom Max Marks
        # -------------------------------------------------
        final_score = (final_percentage / 100) * max_marks

        return round(final_percentage, 2), round(final_score, 2)