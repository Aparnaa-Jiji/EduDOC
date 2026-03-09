# =====================================================
# ACCOUNTS VIEWS – EduDOC
# Central admin authority
# =====================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from student.forms import BatchForm
from .forms import TeacherRegisterForm
from .models import TeacherProfile, User, TeacherBatch
import teacher
from .forms import TeacherRegisterForm
from .models import User, TeacherBatch
from student.models import Batch

User = get_user_model()


# =====================================================
# HOME ROUTING
# =====================================================
# =====================================================
# HOME ROUTING (Public Landing Architecture)
# =====================================================
def home(request):

    # If user is logged in → role-based redirect
    if request.user.is_authenticated:

        if request.user.is_superuser:
            return redirect("accounts:admin_dashboard")

        if request.user.role == User.Role.TEACHER:
            return redirect("teacher:teacher_dashboard")

        return redirect("student:student_dashboard")

    # If not logged in → render public landing page
    return render(request, "accounts/home.html")



# =====================================================
# REGISTER (Teacher only)
# =====================================================
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import TeacherRegisterForm

from django.db.models import ProtectedError
from django.contrib import messages
from django.contrib import messages
from django.shortcuts import render
from .forms import TeacherRegisterForm


def teacher_register(request):

    if request.method == "POST":
        form = TeacherRegisterForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Registration successful. You can login after admin approval."
            )

            # 🔥 Reset form (important)
            form = TeacherRegisterForm()

            return render(
                request,
                "accounts/teacher_register.html",
                {"form": form}
            )

    else:
        form = TeacherRegisterForm()

    return render(
        request,
        "accounts/teacher_register.html",
        {"form": form}
    )



# =====================================================
# LOGIN
# =====================================================
def login_view(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if not user:
            return render(request, "accounts/login.html", {
                "error": "Invalid username or password"
            })

        if not user.is_active:
            return render(request, "accounts/login.html", {
                "error": "Account is deactivated. Contact admin."
            })

        if user.role == User.Role.TEACHER and not user.is_approved:
            return render(request, "accounts/login.html", {
                "error": "Teacher account awaiting admin approval."
            })

        login(request, user)

        if user.first_login:
            return redirect("accounts:force_password_change")

        if user.is_superuser:
            return redirect("accounts:admin_dashboard")

        if user.role == User.Role.TEACHER:
            return redirect("teacher:teacher_dashboard")

        return redirect("student:student_dashboard")

    return render(request, "accounts/login.html")


# =====================================================
# LOGOUT
# =====================================================
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# =====================================================
# ADMIN DASHBOARD
# =====================================================
@login_required
def admin_dashboard(request):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    from student.models import Batch
    from .models import TeacherBatch

    pending_teachers_qs = User.objects.filter(
        role=User.Role.TEACHER,
        is_approved=False
    )



    assigned_batch_ids = TeacherBatch.objects.values_list("batch_id", flat=True)
    unassigned_batches = Batch.objects.exclude(id__in=assigned_batch_ids)
    total_batches = Batch.objects.count()

    context = {
        
        "total_teachers": User.objects.filter(role=User.Role.TEACHER).count(),
        "total_students": User.objects.filter(role=User.Role.STUDENT).count(),
        "total_batches": total_batches,
        # Approval queue (ONLY pending)
        "pending_teachers": pending_teachers_qs.count(),
        "pending_teacher_list": pending_teachers_qs,

        # Insights
        "unassigned_batches_count": unassigned_batches.count(),
    }

    return render(request, "accounts/admin_dashboard.html", context)

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
@login_required
def force_password_change(request):

    if request.method == "POST":

        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            return render(request,
                          "accounts/force_password_change.html",
                          {"error": "Passwords do not match"})

        user = request.user
        user.set_password(password)
        user.first_login = False
        user.save()

        update_session_auth_hash(request, user)

        return redirect("student:student_dashboard")

    return render(request,"accounts/force_password_change.html")

from django.db.models import Count

from django.db.models import Count, Q
from django.db.models import Count
from student.models import Batch
from .models import TeacherBatch
import json

from django.db.models import Count, Prefetch
from student.models import Batch
from .models import TeacherBatch


import json
from django.shortcuts import render, redirect
from django.db.models import Count, Prefetch
from django.core.serializers.json import DjangoJSONEncoder

def teacher_list(request):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    filter_type = request.GET.get("filter", "all")

    teachers = (
    User.objects
    .filter(role=User.Role.TEACHER)
    .select_related("profile")   # IMPORTANT
    .annotate(batch_count=Count("assigned_batches"))
    .prefetch_related(
        Prefetch(
            "assigned_batches",
            queryset=TeacherBatch.objects.select_related("batch")
        )
    )
    .order_by("first_name")
)

    # ---------------------------
    # FILTERING
    # ---------------------------
    if filter_type == "active":
        teachers = teachers.filter(is_active=True)
    elif filter_type == "inactive":
        teachers = teachers.filter(is_active=False)
    elif filter_type == "unassigned":
        teachers = teachers.filter(batch_count=0)

    batches = Batch.objects.all().order_by("name")

    # ---------------------------
    # TEACHER → BATCH MAP
    # ---------------------------
    teacher_batch_map = {}
    for tb in TeacherBatch.objects.all():
        teacher_batch_map.setdefault(tb.teacher_id, []).append(tb.batch_id)

    # ---------------------------
    # TEACHER PROFILE MAP (NEW)
    # ---------------------------
    # ---------------------------
    # TEACHER PROFESSIONAL PROFILE MAP
    # ---------------------------
    teacher_profile_map = {}

    for teacher in teachers:

        profile = getattr(teacher, "profile", None)

        teacher_profile_map[teacher.id] = {
            "full_name": f"{teacher.first_name} {teacher.last_name}",
            "username": teacher.username,
            "email": teacher.email,
            "is_active": teacher.is_active,
            "date_joined": teacher.date_joined.strftime("%d %B %Y"),

            # Profile Fields
            "department": profile.department if profile and profile.department else "Not specified",

            "designation": (
                profile.get_designation_display()
                if profile and profile.designation
                else "Not specified"
            ),

            "highest_qualification": (
                profile.highest_qualification
                if profile and profile.highest_qualification
                else "Not specified"
            ),

            "specialization": (
                profile.specialization
                if profile and profile.specialization
                else "Not specified"
            ),

            "qualification_institution": (
                profile.qualification_institution
                if profile and profile.qualification_institution
                else "Not specified"
            ),

            "experience_years": (
                f"{profile.experience_years} Years"
                if profile and profile.experience_years
                else "Not specified"
            ),

            "phone": profile.phone if profile and profile.phone else "Not provided",

            "linkedin_url": profile.linkedin_url if profile and profile.linkedin_url else "",
            "website_url": profile.website_url if profile and profile.website_url else "",

            "profile_image": (
                profile.profile_image.url
                if profile and profile.profile_image
                else ""
            ),

            "profile_completion": (
                profile.profile_completion()
                if profile else 0
            ),
        }

    # ---------------------------
    # CONTEXT
    # ---------------------------
    context = {
        "teachers": teachers,
        "batches": batches,
        "teacher_batch_json": json.dumps(teacher_batch_map),
        "teacher_profile_json": json.dumps(
            teacher_profile_map,
            cls=DjangoJSONEncoder
        ),
        "filter_type": filter_type,
        "total_teachers": User.objects.filter(
            role=User.Role.TEACHER
        ).count(),
        "active_count": User.objects.filter(
            role=User.Role.TEACHER,
            is_active=True
        ).count(),
        "inactive_count": User.objects.filter(
            role=User.Role.TEACHER,
            is_active=False
        ).count(),
        "unassigned_count": User.objects.filter(
            role=User.Role.TEACHER
        )
        .annotate(batch_count=Count("assigned_batches"))
        .filter(batch_count=0)
        .count(),
    }

    return render(request, "accounts/teacher_list.html", context)

# =====================================================
# APPROVE TEACHER
# =====================================================
@login_required
@require_POST
def approve_teacher(request, user_id):

    if not request.user.is_superuser:
        return redirect("login")

    teacher = get_object_or_404(User, id=user_id)

    teacher.is_approved = True
    teacher.is_active = True
    teacher.save()

    # Send approval email
    send_mail(
    subject="EduDOC Teacher Account Approved ✅",
    message=f"""
Dear {teacher.first_name or teacher.username},

Your EduDOC teacher account has been approved by the administrator.

--------------------------------------------------
LOGIN DETAILS
--------------------------------------------------
Username : {teacher.username}
Email    : {teacher.email}

Login Page:
http://127.0.0.1:8000/login/

--------------------------------------------------
IMPORTANT
--------------------------------------------------
• Keep your username confidential.
• Change your password after first login if required.
• Contact admin if you face login issues.

Welcome to EduDOC Faculty Workspace.

Regards,
EduDOC Administration
""",
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[teacher.email],
    fail_silently=False,
)

    messages.success(request, "Teacher approved and notified via email.")

    return redirect("accounts:admin_dashboard")



# =====================================================
# TOGGLE USER STATUS
# =====================================================
@login_required
@require_POST
def toggle_user_status(request, user_id):

    if not request.user.is_superuser:
        return redirect("login")

    user = get_object_or_404(User, id=user_id)

    if user == request.user:
        return redirect("accounts:teacher_list")

    user.is_active = not user.is_active
    user.save()

    return redirect("accounts:teacher_list")


# =====================================================
# =====================================================
# 🔥 NEW — TEACHER → BATCH ASSIGNMENT (ADMIN ONLY)
# =====================================================
# =====================================================


# -----------------------------------------------------
# Assign page
# -----------------------------------------------------
@login_required
def teacher_batch_assign(request, teacher_id):

    if not request.user.is_superuser:
        return redirect("login")

    teacher = get_object_or_404(
        User,
        id=teacher_id,
        role=User.Role.TEACHER
    )

    batches = Batch.objects.all().order_by("name")

    assigned_ids = TeacherBatch.objects.filter(
        teacher=teacher
    ).values_list("batch_id", flat=True)

    return render(request, "accounts/teacher_batch_assign.html", {
        "teacher": teacher,
        "batches": batches,
        "assigned_ids": list(assigned_ids),
    })


# -----------------------------------------------------
# Save assignments
# -----------------------------------------------------
@login_required
@require_POST
@transaction.atomic
def save_teacher_batches(request, teacher_id):

    if not request.user.is_superuser:
        return redirect("login")

    teacher = get_object_or_404(
        User,
        id=teacher_id,
        role=User.Role.TEACHER
    )

    batch_ids = request.POST.getlist("batches")

    # clear old
    TeacherBatch.objects.filter(teacher=teacher).delete()

    # create new
    for bid in batch_ids:
        TeacherBatch.objects.create(
            teacher=teacher,
            batch_id=bid
        )

    messages.success(request, "Batch assignment updated.")

    return redirect("accounts:teacher_list")


# =====================================================
# ADMIN — BATCH MANAGEMENT (Accounts App)
# =====================================================

from student.models import Batch
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


# =====================================================
# ADMIN — BATCH MANAGEMENT (Enhanced)
# =====================================================

from django.db.models import Count, Prefetch
from student.models import Batch
from .models import TeacherBatch
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.db.models import Count, Prefetch
from student.models import Batch
from .models import TeacherBatch

from django.db.models import Count, Prefetch
from student.models import Batch
from .models import TeacherBatch


@login_required
def admin_batch_list(request):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    batches = (
        Batch.objects
        .annotate(student_count=Count("students"))
        .prefetch_related(
            Prefetch(
                "assigned_teachers",
                queryset=TeacherBatch.objects.select_related("teacher")
            )
        )
        .order_by("-id")
    )

    total_batches = batches.count()

    unassigned_batches = (
        batches.filter(assigned_teachers__isnull=True).count()
    )

    large_batches = (
        batches.filter(student_count__gte=50).count()
    )

    context = {
        "batches": batches,
        "total_batches": total_batches,
        "unassigned_batches": unassigned_batches,
        "large_batches": large_batches,
    }

    return render(
        request,
        "accounts/batches/batch_list.html",
        context
    )


@login_required
def admin_batch_edit(request, id):

    if request.user.role != User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")

    batch = get_object_or_404(Batch, id=id)

    form = BatchForm(request.POST or None, instance=batch)

    if form.is_valid():
        form.save()
        messages.success(request, "Batch updated successfully.")
        return redirect("accounts:admin_batch_list")

    return render(
        request,
        "accounts/batches/batch_edit.html",
        {"form": form}
    )

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import ProtectedError
from accounts.models import Batch


def admin_batch_delete(request, id):

    if not request.user.is_superuser:
        return redirect("accounts:login")

    batch = get_object_or_404(Batch, id=id)

    if request.method == "POST":

        try:
            batch_name = batch.name
            student_count = batch.students.count()

            batch.delete()

            messages.success(
                request,
                f'Batch "{batch_name}" deleted successfully.'
            )

        except ProtectedError:

            messages.error(
                request,
                f'Cannot delete batch "{batch.name}". '
                f'{student_count} students are currently assigned. '
                'Reassign or remove students before deletion.'
            )

        return redirect("accounts:admin_batch_list")

    return redirect("accounts:admin_batch_list")
# ---------------------------------------------------------
# Batch List
# ---------------------------------------------------------

# ---------------------------------------------------------
# Batch Create
# ---------------------------------------------------------
@login_required
def admin_batch_create(request):

    if request.user.role != User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")

    form = BatchForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Batch created successfully.")
        return redirect("accounts:admin_batch_list")

    return render(
        request,
        "accounts/batches/batch_create.html",
        {
            "form": form
        }
    )
# ---------------------------------------------------------
# Batch Detail
# ---------------------------------------------------------
from django.db.models import Q
@login_required
def admin_batch_detail(request, id):

    if request.user.role != User.Role.ADMIN:
        return redirect("accounts:admin_dashboard")

    batch = get_object_or_404(Batch, id=id)

    query = request.GET.get("q", "")

    students = batch.students.select_related("user")



    if query:
        students = students.filter(
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(register_no__icontains=query)
        )


    return render(
        request,
        "accounts/batches/batch_detail.html",
        {
            "batch": batch,
            "students": students,
            "query": query,
            "total_count": students.count(),
        }
    )

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def teacher_profile(request):
    return render(request, "accounts/teacher_profile.html", {
        "teacher": request.user
    })

from .forms import TeacherProfileForm
@login_required
@login_required
def edit_teacher_profile(request):

    profile = request.user.profile

    if request.method == "POST":
        form = TeacherProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:teacher_profile")
    else:
        form = TeacherProfileForm(instance=profile)

    return render(request, "accounts/edit_teacher_profile.html", {
        "form": form
    })

from django.http import JsonResponse
from django.views.decorators.http import require_POST


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def update_teacher_profile_section(request):

    profile, _ = TeacherProfile.objects.get_or_create(
    user=request.user
)

    section = request.POST.get("section")

    # ===============================
    # IMAGE UPLOAD
    # ===============================
    if request.FILES.get("profile_image"):
        profile.profile_image = request.FILES["profile_image"]
        profile.save()

        return JsonResponse({
            "success": True,
            "completion": profile.profile_completion()
        })

    # ===============================
    # INSTITUTIONAL
    # ===============================
    if section == "institutional":
        profile.department = request.POST.get("department", "")
        profile.designation = request.POST.get("designation", "")

    # ===============================
    # ACADEMIC
    # ===============================
    elif section == "academic":
        profile.highest_qualification = request.POST.get("highest_qualification", "")
        profile.specialization = request.POST.get("specialization", "")
        profile.qualification_institution = request.POST.get("qualification_institution", "")

        experience = request.POST.get("experience_years")
        profile.experience_years = int(experience) if experience else None

    # ===============================
    # METADATA
    # ===============================
    elif section == "metadata":
        profile.phone = request.POST.get("phone", "")
        profile.linkedin_url = request.POST.get("linkedin_url", "")
        profile.website_url = request.POST.get("website_url", "")

    profile.save()

    return JsonResponse({
        "success": True,
        "completion": profile.profile_completion()
    })