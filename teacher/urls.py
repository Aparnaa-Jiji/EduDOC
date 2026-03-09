# ======================================================
# TEACHER URLS – EduDOC
# Clean • Namespaced • Production Ready • Batch Scoped
# ======================================================

from django.urls import path
from . import views

app_name = "teacher"


urlpatterns = [

    # ==================================================
    # Dashboard
    # ==================================================
    path(
        "dashboard/",
        views.teacher_dashboard,
        name="teacher_dashboard"
    ),

    # ==================================================
    # Classroom creation & listing
    # ==================================================
    path(
        "create/",
        views.create_classroom,
        name="create_classroom"
    ),

    path(
        "classrooms/",
        views.classrooms_page,
        name="classrooms_page"
    ),

    # ==================================================
    # Classroom Workspace
    # ==================================================
    path(
        "classroom/<int:pk>/",
        views.classroom_detail,
        name="classroom_detail"
    ),

    path(
        "classroom/<int:pk>/edit/",
        views.edit_classroom,
        name="edit_classroom"
    ),

    path(
        "classroom/<int:pk>/delete/",
        views.delete_classroom,
        name="delete_classroom"
    ),

    path(
        "classroom/<int:pk>/bulk/",
        views.bulk_actions,
        name="bulk_actions"
    ),

    # ==================================================
    # Unlock Requests (AJAX)
    # ==================================================
    path(
        "unlock/<int:pk>/approve/",
        views.approve_unlock,
        name="approve_unlock"
    ),

    path(
        "unlock/<int:pk>/reject/",
        views.reject_unlock,
        name="reject_unlock"
    ),

    # ==================================================
    # Batch Student View (Teacher Scoped)
    # ==================================================
    path(
        "batch/<int:batch_id>/students/",
        views.batch_students,
        name="batch_students"
    ),

    # ==================================================
    # Guideline Workflow
    # ==================================================

    # Manual rule editing page
    path(
        "classroom/<int:pk>/rules/",
        views.setup_rules,
        name="setup_rules"
    ),

    # Template preview (PDF → JSON preview)
    path(
        "classroom/<int:classroom_id>/rules/preview/",
        views.preview_guideline_rules,
        name="preview_guideline_rules"
    ),

    # Final save after preview
    path(
        "classroom/<int:classroom_id>/rules/save/",
        views.save_guideline_rules,
        name="save_guideline_rules"
    ),
    path(
        "classroom/<int:classroom_id>/guidelines/",
        views.add_guidelines,
        name="add_guidelines"
    ),
    path(
    "classroom/<int:classroom_id>/rules-pdf/",
    views.export_rules_pdf,
    name="export_rules_pdf"
),

# ===============================
# GUIDELINE WORKFLOW
# ===============================
    path(
        "submission/<int:submission_id>/report/",
        views.submission_report,
        name="submission_report"
    ),

path(
    "classroom/<int:classroom_id>/guidelines/download/",
    views.download_guidelines_pdf,
    name="download_guidelines_pdf",
),
]
