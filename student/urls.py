# =========================================================
# STUDENT URLS – EduDOC
# Clean • Non-duplicated • Production Ready
# =========================================================

from django.urls import path
from . import views
from django.views.decorators.http import require_POST


app_name = "student"   # enables namespacing (recommended)


urlpatterns = [

    # =====================================================
    # Dashboard
    # =====================================================
    path("dashboard/", views.student_dashboard, name="student_dashboard"),

    # =====================================================
    # Classroom Join
    # =====================================================
    path("join/", views.join_classroom, name="join_classroom"),

    # =====================================================
    # Classroom Workspace
    # =====================================================
    path(
        "classroom/<int:classroom_id>/",
        views.classroom_workspace,
        name="classroom_workspace"
    ),

    # =====================================================
    # Upload Submission
    # =====================================================
    path(
        "upload/<int:classroom_id>/",
        views.upload_submission,
        name="upload_submission"
    ),

    # =====================================================
    # Detailed Report
    # =====================================================
    path(
        "report/<int:submission_id>/",
        views.report_detail,
        name="report_detail"
    ),

    # =====================================================
    # Unlock Request
    # =====================================================
    path(
        "unlock/<int:classroom_id>/",
        views.request_unlock,
        name="unlock_request"
    ),



# =====================================================
# Edit Batch
# =====================================================


# =====================================================
# Delete Batch
# =====================================================


path(
    "report/<int:submission_id>/download/",
    views.download_report_pdf,
    name="download_report_pdf",
),

path(
    "batches/<int:id>/add-student/",
    views.student_add,
    name="student_add"
),

path(
    "batches/<int:id>/upload-csv/",
    views.student_bulk_upload,
    name="student_bulk_upload"
),


# -------------------------------------------------
# Export CSV (Admin)
# -------------------------------------------------
path(
    "batches/<int:id>/export/",
    views.batch_export_csv,
    name="batch_export_csv"
),

path(
    "batches/student/<int:id>/delete/",
    views.student_delete,
    name="student_delete"
),


path("classrooms/", views.classroom_list, name="classroom_list"),
path("classroom/<int:classroom_id>/unlock/",
         views.request_unlock,
         name="request_unlock"),
path("unjoin/", views.unjoin_classroom, name="unjoin_classroom"),
path(
    "classroom/<int:classroom_id>/download-rules/",
    views.download_rules,
    name="download_rules",
),

path(
    "download-annotated/<int:submission_id>/",
    views.download_annotated,
    name="download_annotated"
)
]

