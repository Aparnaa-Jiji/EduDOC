from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

# ======================================================
# TEACHER REGISTRATION FORM
# ======================================================

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
import uuid

User = get_user_model()


class TeacherRegisterForm(forms.ModelForm):

    # --------------------------------------------------
    # Custom name field (instead of username)
    # --------------------------------------------------
    full_name = forms.CharField(
        label="Full Name",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Full Name"
        })
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Password"
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Confirm Password"
        })
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "email",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "Email Address"
            })
        }

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------
    def clean(self):
        cleaned = super().clean()

        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error("password1", e)

        return cleaned

    # --------------------------------------------------
    # Save logic
    # --------------------------------------------------
    def save(self, commit=True):
        user = super().save(commit=False)

        # Normalize email
        user.email = user.email.lower()

        # Split full name
        name = self.cleaned_data["full_name"].strip().split(" ", 1)

        user.first_name = name[0]
        user.last_name = name[1] if len(name) > 1 else ""

        # Auto-generate unique username
        base_username = slugify(self.cleaned_data["full_name"])
        unique_suffix = uuid.uuid4().hex[:6]
        user.username = f"{base_username}-{unique_suffix}"

        # Set password
        user.set_password(self.cleaned_data["password1"])

        # Force role
        user.role = User.Role.TEACHER
        user.is_active = True      # allow account to exist normally
        user.is_approved = False   # block login via approval check

        if commit:
            user.save()

        return user

from .models import TeacherProfile


class TeacherProfileForm(forms.ModelForm):

    class Meta:
        model = TeacherProfile
        fields = [
            "profile_image",
            "department",
            "designation",
            "highest_qualification",
            "specialization",
            "qualification_institution",
            "experience_years",
            "phone",
            "linkedin_url",
            "website_url",
        ]