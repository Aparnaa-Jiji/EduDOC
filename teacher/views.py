# ======================================================
# TEACHER VIEWS – EduDOC (Production Safe + Batch Scoped)
# ======================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseForbidden,
    FileResponse,
)
from collections import defaultdict
import tempfile
import os
from django.core.mail import send_mail
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from django.http import HttpResponse
from .services.rule_adapter import adapt_rules_to_form

from .utils import build_rule_config
from django.contrib import messages
from django.db.models import Max
from student.models import ClassroomMembership
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import ClassroomForm, ManualComplianceForm
from datetime import timedelta
from django.utils import timezone
from student.models import ClassroomMembership

from teacher.services.submission_gate import get_submission_gate
from .services.rule_adapter import adapt_rules_to_form
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageBreak
from reportlab.platypus import KeepTogether
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import HRFlowable
from reportlab.platypus import Paragraph, Spacer, ListFlowable, ListItem
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import json

import csv
import zipfile
import json
import os
from io import BytesIO
from datetime import timedelta

from django.conf import settings

from .forms import ClassroomForm
from .models import Classroom,Submission
from student.models import UnlockRequest, Batch
from accounts.models import TeacherBatch

User = get_user_model()


# ======================================================
# ROLE GUARD
# ======================================================
def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != User.Role.TEACHER:
            return redirect("accounts:login")
        return view_func(request, *args, **kwargs)
    return wrapper


# ======================================================
# BATCH ACCESS HELPER (CRITICAL)
# ======================================================
def get_assigned_batches(user):
    return Batch.objects.filter(
        assigned_teachers__teacher=user
    ).distinct()


def teacher_base_context(request):
    return {
        "sidebar_batches": get_assigned_batches(request.user)
    }


# ======================================================
# DASHBOARD
# ======================================================
@login_required
@teacher_required
def teacher_dashboard(request):

    now = timezone.now()
    assigned_batches = get_assigned_batches(request.user)

    classrooms = Classroom.objects.filter(
        teacher=request.user,
        batch__in=assigned_batches
    )

    active_classrooms = classrooms.filter(deadline__gte=now)

    today_end = now.replace(hour=23, minute=59, second=59)
    next_72 = now + timedelta(hours=72)

    deadlines_today = active_classrooms.filter(
        deadline__range=(now, today_end)
    ).count()

    deadlines_soon = active_classrooms.filter(
        deadline__range=(today_end, next_72)
    ).count()

    submissions = Submission.objects.filter(
        classroom__teacher=request.user,
        classroom__batch__in=assigned_batches
    ).select_related("student", "classroom")

    recent_activity = submissions.order_by("-submitted_at")[:5]

    pending_unlock_qs = UnlockRequest.objects.filter(
        classroom__teacher=request.user,
        classroom__batch__in=assigned_batches,
        status=UnlockRequest.Status.PENDING
    ).select_related("classroom", "student")

    unlock_requests = pending_unlock_qs.count()

    return render(request, "teacher/teacher_dashboard.html", {
        "active_classrooms": active_classrooms,
        "total_classrooms": classrooms.count(),
        "deadlines_today": deadlines_today,
        "deadlines_soon": deadlines_soon,
        "recent_activity": recent_activity,
        "unlock_requests": unlock_requests,
        "pending_unlock_list": pending_unlock_qs,
        "assigned_batches": assigned_batches,
        "sidebar_batches": assigned_batches,
    })


# ======================================================
# CREATE CLASSROOM
# ======================================================
@login_required
@teacher_required
def create_classroom(request):

    assigned_batches = get_assigned_batches(request.user)

    form = ClassroomForm(request.POST or None)
    form.fields["batch"].queryset = assigned_batches

    if request.method == "POST" and form.is_valid():

        classroom = form.save(commit=False)
        classroom.teacher = request.user

        if classroom.batch not in assigned_batches:
            raise PermissionDenied("Unauthorized batch selection")

        classroom.save()
        # -------------------------------------------------
        # 🔥 AUTO SEND PASSKEY TO BATCH STUDENTS
        # -------------------------------------------------

        students = classroom.batch.students.select_related("user")

        recipient_list = [
            student.user.email
            for student in students
            if student.user.email
        ]

        if recipient_list:
            send_mail(
                subject=f"New Classroom Created – {classroom.name}",
                message=f"""
    Dear Student,

    A new classroom has been created for your batch.

    --------------------------------------------------
    Classroom Name : {classroom.name}
    Teacher        : {request.user.first_name} {request.user.last_name}
    Passkey        : {classroom.passkey}
    Deadline       : {classroom.deadline}
    --------------------------------------------------

    Use this passkey inside your Student Dashboard to join the classroom.

    Regards,
    EduDOC System
    """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True,   # do not break classroom creation
            )

        messages.success(request, "Classroom created and passkey emailed to students.")

        return redirect("teacher:classrooms_page")

    return render(request, "teacher/create_classroom.html", {"form": form})


# ======================================================
# CLASSROOM LIST (Paginated)
# ======================================================
@login_required
@teacher_required
@login_required
@teacher_required
def classrooms_page(request):

    assigned_batches = get_assigned_batches(request.user)
    now = timezone.now()

    # ==================================================
    # BASE QUERYSET (STRICT BATCH SCOPED)
    # ==================================================
    base_qs = Classroom.objects.filter(
        teacher=request.user,
        batch__in=assigned_batches
    )

    classrooms_qs = base_qs

    # ==================================================
    # SEARCH
    # ==================================================
    search = request.GET.get("search", "").strip()
    if search:
        classrooms_qs = classrooms_qs.filter(
            Q(name__icontains=search)
        )

    # ==================================================
    # STATUS FILTER
    # ==================================================
    status = request.GET.get("status", "")

    if status == "active":
        classrooms_qs = classrooms_qs.filter(deadline__gte=now)

    elif status == "completed":
        classrooms_qs = classrooms_qs.filter(deadline__lt=now)

    # ==================================================
    # SORTING
    # ==================================================
    sort = request.GET.get("sort", "")

    if sort == "deadline":
        classrooms_qs = classrooms_qs.order_by("deadline")

    elif sort == "deadline_desc":
        classrooms_qs = classrooms_qs.order_by("-deadline")

    else:
        classrooms_qs = classrooms_qs.order_by("-created_at")

    # ==================================================
    # COUNTS (Unfiltered)
    # ==================================================
    total_count = base_qs.count()
    active_count = base_qs.filter(deadline__gte=now).count()
    completed_count = base_qs.filter(deadline__lt=now).count()

    # ==================================================
    # PAGINATION
    # ==================================================
    paginator = Paginator(classrooms_qs, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "teacher/classrooms_page.html", {
        "classrooms": page_obj,
        "page_obj": page_obj,
        "search": search,
        "status": status,
        "sort": sort,
        "total_count": total_count,
        "active_count": active_count,
        "completed_count": completed_count,
        "now": now,
    })





# ======================================================
# CLASSROOM DETAIL (Workspace)
# ======================================================

@login_required
@teacher_required
def classroom_detail(request, pk):

    assigned_batches = get_assigned_batches(request.user)

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user,
        batch__in=assigned_batches
    )
    # ---------------------------------------------
    # AUTO FINALIZE AFTER DEADLINE
    # ---------------------------------------------
    if classroom.deadline and timezone.now() > classroom.deadline:
        ClassroomFinalizer.finalize(classroom)
    # ---------------------------------------------
    # All students in this batch
    # ---------------------------------------------
    all_students = classroom.batch.students.select_related("user")

    total_students = all_students.count()

    # ---------------------------------------------
    # Students who submitted (distinct)
    # ---------------------------------------------
    submissions = Submission.objects.filter(
        classroom=classroom
    ).select_related("student", "student__user").order_by("-submitted_at")

    submitted_students = all_students.filter(
        id__in=submissions.values_list("student_id", flat=True)
    ).distinct()

    submitted_count = submitted_students.count()

    # ---------------------------------------------
    # Joined students (same as submitted for now)
    # ---------------------------------------------
    joined_students = submitted_students
    joined_count = joined_students.count()

    # ---------------------------------------------
    # Unjoined students
    # ---------------------------------------------
    unjoined_students = all_students.exclude(
        id__in=joined_students.values_list("id", flat=True)
    )

    unjoined_count = unjoined_students.count()

    # ---------------------------------------------
    # Unlock requests
    # ---------------------------------------------
    unlock_requests = UnlockRequest.objects.filter(
        classroom=classroom,
        status=UnlockRequest.Status.PENDING
    ).select_related("student", "student__user")

    # --------------------------------------------------
    # Latest Report Per Student
    # --------------------------------------------------

    student_reports = []

    for student in all_students:

        student_submissions = submissions.filter(student=student)

        latest = student_submissions.first()  # already ordered desc

        if latest:
            student_reports.append({
                "student": student,
                "attempts": student_submissions.count(),
                "compliance": latest.compliance_percent,
                "plagiarism": latest.plagiarism_percent,
                "final_score": getattr(latest, "final_score", None),
                "status": latest.status,
                "submitted_at": latest.submitted_at,
                "submission_id": latest.id,
            })
        else:
            student_reports.append({
                "student": student,
                "attempts": 0,
                "compliance": None,
                "plagiarism": None,
                "final_score": None,
                "status": "Not Submitted",
                "submitted_at": None,
                "submission_id": None,
            })
    # ---------------------------------------------
    return render(request, "teacher/classroom_detail.html", {
        "classroom": classroom,
        "submissions": submissions,
        "joined_students": joined_students,
        "submitted_students": submitted_students,
        "unjoined_students": unjoined_students,
        "joined_count": joined_count,
        "submitted_count": submitted_count,
        "unjoined_count": unjoined_count,
        "total_students": total_students,
        "unlock_requests": unlock_requests,
         "student_reports": student_reports,
    })


from django.utils import timezone
from teacher.services.finalize_classroom_marks import ClassroomFinalizer
# ======================================================
# BULK ACTIONS
# ======================================================
@login_required
@teacher_required
@require_POST
def bulk_actions(request, pk):

    assigned_batches = get_assigned_batches(request.user)

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user,
        batch__in=assigned_batches
    )

    ids = request.POST.getlist("selected")
    action = request.POST.get("action")

    subs = Submission.objects.filter(
        id__in=ids,
        classroom=classroom
    )

    if action == "download":
        buffer = BytesIO()
        zf = zipfile.ZipFile(buffer, "w")

        for s in subs:
            zf.write(s.file.path, s.file.name.split("/")[-1])

        zf.close()

        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=submissions.zip"
        return response

    if action == "csv":
        response = HttpResponse(content_type="text/csv")
        writer = csv.writer(response)

        writer.writerow(["Student", "Attempt", "Score", "Submitted At"])

        for s in subs:
            writer.writerow([
                s.student.user.username,
                s.attempt_no,
                s.final_score,
                s.submitted_at,
            ])

        return response

    return redirect("teacher:classroom_detail", pk=pk)


# ======================================================
# APPROVE / REJECT UNLOCK
# ======================================================


@login_required
@teacher_required
@require_POST
def approve_unlock(request, pk):

    unlock_req = get_object_or_404(
        UnlockRequest,
        pk=pk,
        classroom__teacher=request.user
    )

    # --------------------------------------
    # Mark request approved
    # --------------------------------------
    unlock_req.status = UnlockRequest.Status.APPROVED
    unlock_req.decided_by = request.user
    unlock_req.decided_at = timezone.now()
    unlock_req.save()

    # --------------------------------------
    # 🔥 ACTUAL UNLOCK LOGIC
    # --------------------------------------
    membership = ClassroomMembership.objects.get(
        student=unlock_req.student,
        classroom=unlock_req.classroom
    )

    membership.is_locked = False

    # give temporary unlock window (24 hrs)
    membership.unlock_until = timezone.now() + timedelta(hours=24)
    membership.unlocked_by = request.user
    membership.unlock_note = "Approved for 24-hour deadline override"

    membership.save()

    return JsonResponse({
        "success": True,
        "unlock_until": membership.unlock_until.strftime("%d %b %Y %I:%M %p")
    })

@login_required
@teacher_required
@require_POST
def reject_unlock(request, pk):

    req = get_object_or_404(
        UnlockRequest,
        pk=pk,
        classroom__teacher=request.user
    )

    req.status = UnlockRequest.Status.REJECTED
    req.save()

    return JsonResponse({"success": True})


# ======================================================
# DELETE CLASSROOM
# ======================================================
@login_required
@teacher_required
@require_POST
def delete_classroom(request, pk):

    assigned_batches = get_assigned_batches(request.user)

    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user,
        batch__in=assigned_batches
    )

    classroom.delete()
    return redirect("teacher:classrooms_page")

# ======================================================
# BATCH STUDENT LIST (Teacher Scoped)
# ======================================================
@login_required
@teacher_required
def batch_students(request, batch_id):

    assigned_batches = get_assigned_batches(request.user)

    # 🔒 Strict batch access control
    batch = get_object_or_404(
        Batch,
        id=batch_id,
        id__in=assigned_batches.values_list("id", flat=True)
    )

    students = batch.students.select_related("user")

    # ======================
    # SEARCH
    # ======================
    query = request.GET.get("q")

    if query:
        students = students.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) 
            
        )

    students = students.order_by("user__username")

    # ======================
    # COUNTS
    # ======================
    total_count = students.count()

    # Using login activity as engagement indicator
    joined_count = students.filter(
        user__last_login__isnull=False
    ).count()

    not_joined_count = students.filter(
        user__last_login__isnull=True
    ).count()

    return render(request, "teacher/batch_students.html", {
        "batch": batch,
        "students": students,
        "sidebar_batches": assigned_batches,
        "search_query": query or "",
        "total_count": total_count,
        "joined_count": joined_count,
        "not_joined_count": not_joined_count,
    })
# ======================================================
# EDIT CLASSROOM (Batch Scoped + Secure)
# ======================================================
@login_required
@teacher_required
def edit_classroom(request, pk):

    assigned_batches = get_assigned_batches(request.user)

    # 🔒 Strict object-level access
    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user,
        batch__in=assigned_batches
    )

    form = ClassroomForm(request.POST or None, instance=classroom)

    # 🔒 Restrict batch dropdown
    form.fields["batch"].queryset = assigned_batches

    if request.method == "POST":

        if form.is_valid():

            updated_classroom = form.save(commit=False)

            # 🔒 Security guard against tampered POST
            if updated_classroom.batch not in assigned_batches:
                raise PermissionDenied("Unauthorized batch selection.")

            updated_classroom.teacher = request.user
            updated_classroom.save()

            messages.success(request, "Classroom updated successfully.")

            return redirect("teacher:classroom_detail", pk=pk)

    return render(
        request,
        "teacher/create_classroom.html",  # reuse same template
        {
            "form": form,
            "classroom": classroom
        }
    )
# ======================================================
# SAVE GUIDELINE RULES (FINAL – SECURE + VERSIONED)
# ======================================================
@login_required
@teacher_required
@require_POST
def save_guideline_rules(request, classroom_id):

    assigned_batches = get_assigned_batches(request.user)

    # --------------------------------------------------
    # 🔒 Strict object-level security
    # --------------------------------------------------
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user,
        batch__in=assigned_batches
    )

    # --------------------------------------------------
    # 🔒 Prevent modification if locked
    # --------------------------------------------------
    if classroom.rules_locked:
        messages.error(request, "Rules are locked and cannot be modified.")
        return redirect("teacher:classroom_detail", pk=classroom.id)

    # --------------------------------------------------
    # Retrieve parsed rules from session
    # --------------------------------------------------
    rules = request.session.get("temp_rules")

    if not rules:
        messages.error(request, "No extracted rules found. Please re-upload guideline.")
        return redirect("teacher:classroom_detail", pk=classroom.id)

    # --------------------------------------------------
    # Version increment (classroom-level versioning)
    # --------------------------------------------------
    next_version = (classroom.rules_version or 0) + 1

    # --------------------------------------------------
    # Save structured JSON rules directly
    # --------------------------------------------------
    classroom.rules_json = rules
    classroom.rules_version = next_version
    classroom.save()



    # --------------------------------------------------
    # Clean session safely
    # --------------------------------------------------
    if "temp_rules" in request.session:
        del request.session["temp_rules"]

    messages.success(
        request,
        f"Rules saved successfully (v{next_version})."
    )

    return redirect("teacher:classroom_detail", pk=classroom.id)

# ======================================================
# SETUP RULES
# Manual rule editing (Text → Structured JSON)
# URL: /teacher/classroom/<pk>/rules/
# ======================================================
@login_required
@teacher_required
def setup_rules(request, pk):

    assigned_batches = get_assigned_batches(request.user)

    # --------------------------------------------------
    # 🔒 Strict object-level security
    # --------------------------------------------------
    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        teacher=request.user,
        batch__in=assigned_batches
    )

    # --------------------------------------------------
    # 🔒 Prevent editing if locked
    # --------------------------------------------------
    if classroom.rules_locked:
        messages.error(request, "Rules are locked and cannot be modified.")
        return redirect("teacher:classroom_detail", pk=pk)

    # --------------------------------------------------
    # Fetch latest guideline (for display/reference)
    # --------------------------------------------------


    # ==================================================
    # SAVE RULES (POST)
    # ==================================================
    if request.method == "POST":

        rules_text = request.POST.get("rules_text", "").strip()

        if not rules_text:
            messages.error(request, "Rules cannot be empty.")
            return redirect("teacher:setup_rules", pk=pk)

        # --------------------------------------------------
        # Prepare version increment
        # --------------------------------------------------


        # --------------------------------------------------
        # Convert raw text → structured JSON
        # --------------------------------------------------
        # Convert raw text → structured JSON
 

        parsed_rules = [
            line.strip()
            for line in rules_text.splitlines()
            if line.strip()
        ]

        structured_config = build_rule_config(parsed_rules)
        next_version = (classroom.rules_version or 0) + 1

        classroom.rules_json = structured_config
        classroom.rules_version = next_version
        classroom.save()

        messages.success(
            request,
            f"Rules saved successfully (v{next_version})."
        )


        return redirect("teacher:classroom_detail", pk=pk)


    # ==================================================
    # LOAD PAGE (GET)
    # ==================================================
    return render(
        request,
        "teacher/setup_rules.html",
        {
            "classroom": classroom,
            "latest_guideline": classroom.rules_json,
            "has_guideline": bool(classroom.rules_json),
        }
    )

# ======================================================
# PREVIEW GUIDELINE RULES (TEMPLATE BASED)
# Upload → Parse → Preview → Confirm
# URL: /teacher/classroom/<classroom_id>/preview-rules/
# ======================================================
@login_required
@teacher_required
def preview_guideline_rules(request, classroom_id):

    assigned_batches = get_assigned_batches(request.user)

    # --------------------------------------------------
    # 🔒 Strict classroom ownership + batch security
    # --------------------------------------------------
    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user,
        batch__in=assigned_batches
    )

    # --------------------------------------------------
    # Prevent rule modification if locked
    # --------------------------------------------------
    if classroom.rules_locked:
        messages.error(request, "Rules are locked and cannot be modified.")
        return redirect("teacher:classroom_detail", pk=classroom.id)

    # --------------------------------------------------
    # Only allow POST with file
    # --------------------------------------------------
    if request.method == "POST":

        guideline_file = request.FILES.get("guideline_file")

        if not guideline_file:
            messages.error(request, "No file uploaded.")
            return redirect("teacher:classroom_detail", pk=classroom.id)

        # --------------------------------------------------
        # Validate extension
        # --------------------------------------------------
        if not guideline_file.name.lower().endswith(".pdf"):
            messages.error(request, "Only PDF template files are allowed.")
            return redirect("teacher:classroom_detail", pk=classroom.id)

        # --------------------------------------------------
        # Save temporarily for parsing
        # --------------------------------------------------


        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                for chunk in guideline_file.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name

            # --------------------------------------------------
            # Parse template → structured JSON
            # --------------------------------------------------
            rules = parse_template_rules(temp_path)

            # --------------------------------------------------
            # Store temporarily in session
            # (Will be finalized in save_guideline_rules)
            # --------------------------------------------------
            request.session["temp_rules"] = rules

        finally:
            # cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return render(
            request,
            "teacher/rules_preview.html",
            {
                "rules": rules,
                "classroom": classroom
            }
        )

    # --------------------------------------------------
    # Fallback
    # --------------------------------------------------
    return redirect("teacher:classroom_detail", pk=classroom.id)

# ======================================================
# ADD GUIDELINES (Manual + Auto Detect Prefill)
# ======================================================

@login_required
@teacher_required
def add_guidelines(request, classroom_id):

    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    # --------------------------------------------------
    # Prevent editing if rules locked
    # --------------------------------------------------
    if classroom.rules_locked:
        messages.error(request, "Guidelines are locked.")
        return redirect("teacher:classroom_detail", pk=classroom.id)

    auto_detected = False

    # ==================================================
    # POST → SAVE MANUAL RULES
    # ==================================================
    if request.method == "POST":

        form = ManualComplianceForm(request.POST)

        if form.is_valid():

            # -------------------------
            # Margin Normalization
            # -------------------------
            margin_unit = form.cleaned_data.get("margin_unit")

            top = form.cleaned_data.get("margin_top") or 0
            bottom = form.cleaned_data.get("margin_bottom") or 0
            left = form.cleaned_data.get("margin_left") or 0
            right = form.cleaned_data.get("margin_right") or 0

            # Convert CM → Inches safely
            if margin_unit == "cm":
                top = round(top / 2.54, 2)
                bottom = round(bottom / 2.54, 2)
                left = round(left / 2.54, 2)
                right = round(right / 2.54, 2)

            # -------------------------
            # Structured Rule JSON
            # -------------------------
            structured_rules = {

                "page_rules": {
                    "min_pages": form.cleaned_data["min_pages"],
                    "max_pages": form.cleaned_data["max_pages"],
                    "paper_size": form.cleaned_data["paper_size"],
                },

                "margins": {
                    "unit": margin_unit,
                    "top": top,
                    "bottom": bottom,
                    "left": left,
                    "right": right,
                },

                "font_rules": {
                    "font_name": form.cleaned_data["font_name"],
                    "font_color": form.cleaned_data["font_color"],
                    "uniform": form.cleaned_data["enforce_uniform_font"],
                },

                "spacing_rules": {
                    "main": form.cleaned_data["main_line_spacing"],
                    "reference": form.cleaned_data["reference_spacing"],
                    "certificate": form.cleaned_data["certificate_spacing"],
                    "acknowledgement": form.cleaned_data["acknowledgement_spacing"],
                },

                "sections": [
                    s.strip()
                    for s in form.cleaned_data["required_sections"].split(",")
                    if s.strip()
                ],

                "chapters": [
                    c.strip()
                    for c in form.cleaned_data["required_chapters"].split(",")
                    if c.strip()
                ],

                "numbering": {
                    "enabled": form.cleaned_data.get("page_number_required"),
                    "position": form.cleaned_data.get("page_number_position"),
                    "style": form.cleaned_data.get("page_number_style"),
                },

                "reference_rules": {
                    "alphabetical":
                        form.cleaned_data["enforce_reference_alphabetical"],
                    "author_year":
                        form.cleaned_data["enforce_author_year_format"],
                },

                "figure_table_rules": {
                    "chapter_based":
                        form.cleaned_data["chapter_based_numbering"],
                    "appendix_prefix":
                        form.cleaned_data["appendix_prefix"],
                },
                "header": {
    "enabled": form.cleaned_data.get("header_required"),
    "position": form.cleaned_data.get("header_position"),
    "text": form.cleaned_data.get("header_text"),
},

"footer": {
    "enabled": form.cleaned_data.get("footer_required"),
    "position": form.cleaned_data.get("footer_position"),
    "text": form.cleaned_data.get("footer_text"),
},

"page_number": {
    "enabled": form.cleaned_data.get("page_number_required"),
    "position": form.cleaned_data.get("page_number_position"),
    "style": form.cleaned_data.get("page_number_style"),
},

"layout_rules": {
    "header": {
        "required": form.cleaned_data.get("header_required"),
        "position": form.cleaned_data.get("header_position"),
        "text": form.cleaned_data.get("header_text"),
    },
    "footer": {
        "required": form.cleaned_data.get("footer_required"),
        "position": form.cleaned_data.get("footer_position"),
        "text": form.cleaned_data.get("footer_text"),
    },
    "page_number": {
        "required": form.cleaned_data.get("page_number_required"),
        "position": form.cleaned_data.get("page_number_position"),
        "style": form.cleaned_data.get("page_number_style"),
    },
    "border_required": form.cleaned_data.get("border_required"),
},

                "font_size_rules": {
    "content": form.cleaned_data.get("content_font_size") or None,
    "heading": form.cleaned_data.get("heading_font_size") or None,
    "subheading": form.cleaned_data.get("subheading_font_size") or None,
},
                "chapter_numbering": {
                    "enabled": form.cleaned_data.get("chapter_numbering_enabled"),
                    "start_from": form.cleaned_data.get("chapter_start_number") or 1,
                },

                "subheading_numbering": {
                    "enabled": form.cleaned_data.get("subheading_numbering_enabled"),
                },

                "grammar_rules": {
                    "enabled": form.cleaned_data.get("grammar_check_enabled"),
                },
            }

            classroom.rules_json = structured_rules
            classroom.rules_version = (classroom.rules_version or 0) + 1
            classroom.save()

            messages.success(request, "Strict Manual Compliance Rules Saved.")
            return redirect("teacher:classroom_detail", pk=classroom.id)

    # ==================================================
    # GET → LOAD FORM
    # ==================================================
    else:

        # ---------------------------------------------
        # AUTO DETECT PREFILL (ONE TIME SESSION LOAD)
        # ---------------------------------------------
        detected = request.session.pop("auto_detect_rules", None)

        if detected:

            initial_data = {
                # ---------- PAGE ----------
                "min_pages": detected.get("min_pages"),
                "max_pages": detected.get("max_pages"),

                # ---------- FONT ----------
                "font_name": detected.get("font_name"),

                # ---------- SPACING ----------
                "main_line_spacing": detected.get("line_spacing"),

                # ---------- MARGINS ----------
                "margin_top": detected.get("margin_value"),
                "margin_bottom": detected.get("margin_value"),
                "margin_left": detected.get("margin_value"),
                "margin_right": detected.get("margin_value"),
                "margin_unit": detected.get("margin_unit", "inch"),
            }

            form = ManualComplianceForm(initial=initial_data)
            auto_detected = True

        else:
            form = ManualComplianceForm()

    # ==================================================
    # RENDER
    # ==================================================
    return render(
        request,
        "teacher/add_guidelines.html",
        {
            "form": form,
            "classroom": classroom,
            "auto_detected": auto_detected,
        },
    )



@login_required
@teacher_required
def export_rules_pdf(request, classroom_id):

    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    if not classroom.rules_json:
        return HttpResponse("No rules configured.", status=404)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()

    title_style = styles["Heading1"]
    section_style = styles["Heading2"]
    normal_style = styles["Normal"]

    # =============================
    # Title
    # =============================
    elements.append(Paragraph("EduDOC Compliance Rules", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(
        f"Classroom: {classroom.name}",
        normal_style
    ))

    elements.append(Paragraph(
        f"Version: v{classroom.rules_version}",
        normal_style
    ))

    elements.append(Spacer(1, 0.3 * inch))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.3 * inch))

    rules = classroom.rules_json

    # =============================
    # PAGE RULES
    # =============================
    page_rules = rules.get("page_rules", {})
    if page_rules:
        elements.append(Paragraph("Page Rules", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        elements.append(Paragraph(
            f"Minimum Pages: {page_rules.get('min_pages')}",
            normal_style
        ))
        elements.append(Paragraph(
            f"Maximum Pages: {page_rules.get('max_pages')}",
            normal_style
        ))

        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # MARGINS
    # =============================
    margins = rules.get("margins", {})
    if margins:
        elements.append(Paragraph("Margin Requirements (in inches)", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        for k, v in margins.items():
            elements.append(Paragraph(f"{k.capitalize()}: {v}", normal_style))

        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # FONT RULES
    # =============================
    font_rules = rules.get("font_rules", {})
    if font_rules:
        elements.append(Paragraph("Font Rules", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        elements.append(Paragraph(
            f"Font Name: {font_rules.get('font_name')}",
            normal_style
        ))
        elements.append(Paragraph(
            f"Font Color: {font_rules.get('font_color')}",
            normal_style
        ))
        elements.append(Paragraph(
            f"Uniform Font Required: {font_rules.get('uniform')}",
            normal_style
        ))

        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # SECTION ORDER
    # =============================
    sections = rules.get("sections", [])
    if sections:
        elements.append(Paragraph("Required Section Order", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        section_list = [
            ListItem(Paragraph(s, normal_style))
            for s in sections
        ]

        elements.append(ListFlowable(section_list, bulletType="bullet"))
        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # CHAPTERS
    # =============================
    chapters = rules.get("chapters", [])
    if chapters:
        elements.append(Paragraph("Required Chapters", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        chapter_list = [
            ListItem(Paragraph(c, normal_style))
            for c in chapters
        ]

        elements.append(ListFlowable(chapter_list, bulletType="bullet"))
        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # REFERENCE RULES
    # =============================
    reference_rules = rules.get("reference_rules", {})
    if reference_rules:
        elements.append(Paragraph("Reference Rules", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        for k, v in reference_rules.items():
            elements.append(Paragraph(f"{k}: {v}", normal_style))

        elements.append(Spacer(1, 0.3 * inch))

    # =============================
    # NUMBERING RULES
    # =============================
    numbering = rules.get("numbering", {})
    if numbering:
        elements.append(Paragraph("Page Numbering Rules", section_style))
        elements.append(Spacer(1, 0.2 * inch))

        for k, v in numbering.items():
            elements.append(Paragraph(f"{k}: {v}", normal_style))

        elements.append(Spacer(1, 0.3 * inch))

    doc.build(elements)

    buffer.seek(0)

    filename = f"{classroom.name}_Rules_v{classroom.rules_version}.pdf"

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response



# =========================================================
# AUTO DETECT RULES
# =========================================================





from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from django.utils.text import slugify

def download_guidelines_pdf(request, classroom_id):

    classroom = get_object_or_404(
        Classroom,
        id=classroom_id,
        teacher=request.user
    )

    rules = classroom.rules_json or {}

    response = HttpResponse(content_type="application/pdf")
    safe_name = slugify(classroom.name)

    response["Content-Disposition"] = (
        f'attachment; filename="{safe_name}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    story = []

    # =====================================================
    # HEADER
    # =====================================================

    story.append(
        Paragraph(
            "EduDOC Academic Document Guidelines",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            "Automated Academic Compliance Framework",
            styles["Italic"]
        )
    )

    story.append(Spacer(1, 25))

    # =====================================================
    # CLASSROOM INFO
    # =====================================================

    meta_table = Table([
        ["Classroom", classroom.name],
        ["Deadline", classroom.deadline.strftime("%d %b %Y %H:%M") if classroom.deadline else "Not Set"],
        ["Max Marks", str(classroom.max_marks)],
    ], colWidths=[150, 350])

    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.lightgrey),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
    ]))

    story.append(meta_table)

    story.append(Spacer(1, 25))

    # =====================================================
    # RULE SECTIONS
    # =====================================================

    for section, values in rules.items():

        story.append(
            Paragraph(
                section.replace("_", " ").title(),
                styles["Heading2"]
            )
        )

        story.append(Spacer(1, 10))

        rows = [["Rule", "Expected Value"]]

        if isinstance(values, dict):

            for key, value in values.items():

                rows.append([
                    key.replace("_", " ").title(),
                    str(value)
                ])

        table = Table(rows, colWidths=[260, 260])

        table.setStyle(TableStyle([

            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4f46e5")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),

        ]))

        story.append(table)

        story.append(Spacer(1, 20))

    # =====================================================
    # FOOTER
    # =====================================================

    story.append(Spacer(1, 30))

    story.append(
        Paragraph(
            "Generated automatically by EduDOC — Academic Document Compliance System",
            styles["Italic"]
        )
    )

    # =====================================================
    # BUILD PDF
    # =====================================================

    doc.build(story)

    return response
# ======================================================
# SUBMISSION REPORT (Teacher Scoped + Secure)
# ======================================================
@login_required
@teacher_required
def submission_report(request, submission_id):

    assigned_batches = get_assigned_batches(request.user)

    submission = get_object_or_404(
        Submission.objects.select_related(
            "student",
            "student__user",
            "classroom",
            "classroom__batch"
        ),
        id=submission_id,
        classroom__teacher=request.user,
        classroom__batch__in=assigned_batches
    )

    return render(
        request,
        "teacher/submission_report.html",
        {
            "submission": submission,
            "classroom": submission.classroom,
            "student": submission.student,
            "breakdown": submission.breakdown_json or {},
        }
    )