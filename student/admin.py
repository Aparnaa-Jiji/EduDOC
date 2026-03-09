# =========================================================
# EduDOC – Student Admin (Production Ready)
# Batch-based provisioning + secure account creation
# =========================================================

from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from django.utils.crypto import get_random_string
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Batch, Student, ClassroomMembership, UnlockRequest

User = get_user_model()


# =========================================================
# Student Creation Form (Admin Provisioning)
# =========================================================
class StudentCreateForm(forms.ModelForm):
    """
    Admin creates students.
    This automatically:
      - generates username
      - generates strong password
      - creates User(role=STUDENT)
      - creates Student profile
      - sends credentials email
    """

    name = forms.CharField(label="Student Name")
    email = forms.EmailField()

    class Meta:
        model = Student
        fields = ["name", "email", "batch"]

    # -----------------------------------------------------
    # Validate unique institutional email
    # -----------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already registered.")

        return email

    # -----------------------------------------------------
    # Atomic provisioning (critical for data integrity)
    # -----------------------------------------------------
    @transaction.atomic
    def save(self, commit=True):

        name = self.cleaned_data["name"].strip()
        email = self.cleaned_data["email"].lower()
        batch = self.cleaned_data["batch"]

        # =================================================
        # Username generation
        # =================================================
        base_username = email.split("@")[0]
        username = base_username
        counter = 1

        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # =================================================
        # Strong random password
        # =================================================
        password = get_random_string(12)

        # =================================================
        # Create User explicitly as STUDENT
        # =================================================
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=User.Role.STUDENT,
        )

        # Split full name into first/last
        parts = name.split(" ", 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.save()


        # =================================================
        # Create Student profile
        # =================================================
        student = Student.objects.create(
            user=user,
            register_no=register_no,
            batch=batch
        )

        # =================================================
        # Send credentials email (fail-safe)
        # =================================================
        send_mail(
            subject="EduDOC Account Created",
            message=(
                f"Hello {name},\n\n"
                f"Your EduDOC account has been created.\n\n"
                f"Username: {username}\n"
                f"Password: {password}\n\n"
                f"Please login and change your password immediately."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,  # prevents admin crash
        )

        return student


# =========================================================
# Batch Admin
# =========================================================
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):

    list_display = ("name", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


# =========================================================
# Student Admin
# =========================================================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    form = StudentCreateForm

    list_display = (
        "get_full_name",
        "batch",
        "created_at",
    )


    list_filter = ("batch",)
    search_fields = (
        "user__username",
        "user__email",
    )

    ordering = ("-created_at",)
    def get_full_name(self, obj):
        return obj.user.get_full_name()

    get_full_name.short_description = "Name"


# =========================================================
# Classroom Membership Admin
# =========================================================
@admin.register(ClassroomMembership)
class ClassroomMembershipAdmin(admin.ModelAdmin):

    list_display = ("student", "classroom", "joined_at")
    search_fields = ("student__user__username", "classroom__name")
    ordering = ("-joined_at",)


# =========================================================
# Unlock Request Admin
# =========================================================
@admin.register(UnlockRequest)
class UnlockRequestAdmin(admin.ModelAdmin):

    list_display = ("student", "classroom", "status", "created_at")
    list_filter = ("status",)
    ordering = ("-created_at",)
