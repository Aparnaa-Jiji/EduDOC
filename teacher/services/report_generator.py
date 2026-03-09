# =========================================================
# REPORT GENERATOR – EduDOC (Advanced Academic Report)
# Production Grade • Hardened
# =========================================================

from pathlib import Path
from typing import Any, List, Dict

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from django.conf import settings

import logging

logger = logging.getLogger(__name__)


class ReportGenerator:

    def __init__(self, submission):
        self.submission = submission

    # =====================================================
    # PUBLIC ENTRY
    # =====================================================
    def generate(self) -> str:
        try:
            return self._build()
        except Exception:
            logger.exception(
                "Report generation failed for submission %s",
                self.submission.id
            )
            return ""

    # =====================================================
    # MAIN BUILDER
    # =====================================================
    def _build(self) -> str:

        filename = f"report_{self.submission.id}.pdf"

        report_dir = Path(settings.MEDIA_ROOT) / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)

        filepath = report_dir / filename

        doc = SimpleDocTemplate(str(filepath))

        styles = getSampleStyleSheet()
        elements: List[Any] = []

        # -------------------------------------------------
        # SAFE DATA EXTRACTION
        # -------------------------------------------------

        student_name = getattr(
            self.submission.student.user,
            "username",
            "N/A"
        )

        classroom_name = getattr(
            self.submission.classroom,
            "name",
            "N/A"
        )

        compliance = float(
            self.submission.compliance_percent or 0
        )

        plagiarism = float(
            self.submission.plagiarism_percent or 0
        )

        issues = getattr(
            self.submission,
            "breakdown_json",
            []
        ) or []

        submitted_at = (
            self.submission.submitted_at.strftime(
                "%d %b %Y %H:%M"
            )
            if self.submission.submitted_at
            else "N/A"
        )

        # =================================================
        # HEADER
        # =================================================

        elements.append(
            Paragraph(
                "EduDOC Academic Compliance Evaluation",
                styles["Title"]
            )
        )

        elements.append(
            Paragraph(
                "Automated Academic Document Guideline Verification",
                styles["Italic"]
            )
        )

        elements.append(Spacer(1, 25))

        # =================================================
        # STUDENT META TABLE
        # =================================================

        meta_table = Table([
            ["Student", student_name],
            ["Classroom", classroom_name],
            ["Attempt", str(self.submission.attempt_no)],
            ["Submitted", submitted_at],
        ], colWidths=[150, 380])

        meta_table.setStyle(TableStyle([

            ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

        ]))

        elements.append(meta_table)
        elements.append(Spacer(1, 30))

        # =================================================
        # SCORE SUMMARY
        # =================================================

        elements.append(
            Paragraph(
                "Evaluation Summary",
                styles["Heading2"]
            )
        )

        elements.append(Spacer(1, 10))

        final_score = max(0, compliance - plagiarism)

        score_table = Table([

            ["Metric", "Value"],

            ["Compliance Score", f"{round(compliance,2)} %"],

            ["Plagiarism Similarity", f"{round(plagiarism,2)} %"],

            ["Final Score", f"{round(final_score,2)} %"],

        ], colWidths=[260, 260])

        score_table.setStyle(TableStyle([

            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#4f46e5")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),

            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

            ("GRID",(0,0),(-1,-1),0.5,colors.grey),

            ("ALIGN",(1,1),(-1,-1),"CENTER"),

        ]))

        elements.append(score_table)
        elements.append(Spacer(1, 35))

        # =================================================
        # GROUP RULES BY CATEGORY
        # =================================================

        categorized: Dict[str, List[dict]] = {}

        for issue in issues:

            category = issue.get("category", "General")

            categorized.setdefault(category, []).append(issue)

        # =================================================
        # RULE TABLES
        # =================================================

        elements.append(
            Paragraph(
                "Guideline Compliance Details",
                styles["Heading2"]
            )
        )

        elements.append(Spacer(1, 15))

        if not categorized:

            elements.append(
                Paragraph(
                    "No violations detected. The document satisfies all guideline rules.",
                    styles["Normal"]
                )
            )

        else:

            for category, rules in categorized.items():

                elements.append(
                    Paragraph(
                        category,
                        styles["Heading3"]
                    )
                )

                elements.append(Spacer(1, 8))

                rows = [["Rule", "Expected", "Found", "Status"]]

                for rule in rules:

                    rows.append([
                        rule.get("rule", "-"),
                        str(rule.get("expected", "-")),
                        str(rule.get("found", "-")),
                        rule.get("status", "-"),
                    ])

                table = Table(
                    rows,
                    colWidths=[170, 130, 130, 80]
                )

                style_commands = [

                    ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#6366f1")),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("GRID",(0,0),(-1,-1),0.25,colors.grey),
                    ("ALIGN",(1,1),(-1,-1),"CENTER"),

                ]

                # Dynamic row coloring
                for i, rule in enumerate(rules, start=1):

                    status = rule.get("status","").upper()

                    if status == "FAIL":
                        style_commands.append(
                            ("TEXTCOLOR",(3,i),(3,i),colors.red)
                        )

                    elif status == "PASS":
                        style_commands.append(
                            ("TEXTCOLOR",(3,i),(3,i),colors.green)
                        )

                    else:
                        style_commands.append(
                            ("TEXTCOLOR",(3,i),(3,i),colors.blue)
                        )

                table.setStyle(TableStyle(style_commands))

                elements.append(table)
                elements.append(Spacer(1, 20))

        # =================================================
        # FOOTER
        # =================================================

        elements.append(Spacer(1, 25))

        elements.append(
            Paragraph(
                "Generated automatically by EduDOC — Academic Document Compliance System",
                styles["Italic"]
            )
        )

        # =================================================
        # BUILD PDF
        # =================================================

        doc.build(elements)

        return f"reports/{filename}"