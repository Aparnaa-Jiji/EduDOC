# ======================================================
# ACCOUNTS URLS – EduDOC
# Centralized authentication + admin authority
# ======================================================

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = "accounts"


urlpatterns = [

    # ==================================================
    # Core
    # ==================================================
    path("", views.home, name="home"),


    # ==================================================
    # Authentication
    # ==================================================
    path("teacher-register/", views.teacher_register, name="teacher-register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # ==================================================
    # Admin Dashboard
    # ==================================================
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("teachers/", views.teacher_list, name="teacher_list"),

    # --------------------------------------------------
    # Teacher approval / user control
    # --------------------------------------------------
    path(
        "approve-teacher/<int:user_id>/",
        views.approve_teacher,
        name="approve_teacher"
    ),

    path(
        "toggle-user/<int:user_id>/",
        views.toggle_user_status,
        name="toggle_user_status"
    ),

    # ==================================================
    # 🔥 NEW — Teacher → Batch Assignment
    # ==================================================

    # assignment page
    path(
        "teacher/<int:teacher_id>/assign-batches/",
        views.teacher_batch_assign,
        name="teacher_batch_assign"
    ),

    # save mapping (POST)
    path(
        "teacher/<int:teacher_id>/assign-batches/save/",
        views.save_teacher_batches,
        name="save_teacher_batches"
    ),
        # ==================================================
    # Password Reset
    # ==================================================

    path(
    "password-reset/",
    auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/password-reset/done/"   # ADD THIS LINE
    ),
    name="password_reset"
),


    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    path(
    "reset/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/reset/done/"   # ADD THIS LINE
    ),
    name="password_reset_confirm"
),


    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),
    path("admin-batches/", views.admin_batch_list, name="admin_batch_list"),
    path("admin-batches/create/", views.admin_batch_create, name="admin_batch_create"),
    path(
    "admin-batches/<int:id>/",
    views.admin_batch_detail,
    name="admin_batch_detail"
),

    path(
    "admin-batches/<int:id>/edit/",
    views.admin_batch_edit,
    name="admin_batch_edit"
),
path(
    "admin-batches/<int:id>/delete/",
    views.admin_batch_delete,
    name="admin_batch_delete"
),

path("teacher/profile/", views.teacher_profile, name="teacher_profile"),

 path(
        "teacher/profile/edit/",
        views.edit_teacher_profile,
        name="edit_teacher_profile"
    ),

path(
    "teacher/profile/update/",
    views.update_teacher_profile_section,
    name="update_teacher_profile_section"
),
path(
    "force-password-change/",
    views.force_password_change,
    name="force_password_change"
),
]
