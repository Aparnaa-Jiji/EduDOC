# ======================================================
# STUDENT FORMS – Production Safe Version
# Students are provisioned ONLY by Admin (no registration)
# ======================================================

import os
from django import forms
from teacher.models import Submission


# ======================================================
# JOIN CLASSROOM FORM
# ======================================================
class JoinClassroomForm(forms.Form):
    """
    Students join a classroom using teacher-provided passkey.
    """

    passkey = forms.CharField(
        max_length=20,
        strip=True,
        label="Classroom Passkey",
        
        widget=forms.TextInput(attrs={
            "placeholder": "Enter passkey",
            "class": "form-control",
            "autocomplete": "off",
        })
    )


# ======================================================
# SUBMISSION FORM
# ======================================================
class SubmissionForm(forms.ModelForm):
    """
    Secure document upload (.docx only).

    Protections:
    - extension check
    - MIME type check
    - size limit
    """

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


    class Meta:
        model = Submission
        fields = ["file"]

        widgets = {
            "file": forms.FileInput(attrs={
                "accept": ".docx",
                "class": "form-control",
            })
        }

    # --------------------------------------------------
    # Secure file validation
    # --------------------------------------------------
    def clean_file(self):
        f = self.cleaned_data.get("file")

        if not f:
            raise forms.ValidationError("Please select a file.")

        # extension
        if not f.name.lower().endswith(".docx"):
            raise forms.ValidationError("Only .docx files are allowed.")

        # MIME type
        allowed_types = [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        ]

        if f.content_type not in allowed_types:
            raise forms.ValidationError("Invalid file type.")

        # size
        if f.size > self.MAX_FILE_SIZE_BYTES:
            raise forms.ValidationError("File must be under 10 MB.")

        f.name = os.path.basename(f.name)

        return f

# =========================================================
# Batch Forms – EduDOC
# =========================================================



from datetime import date
from .models import Batch


class BatchForm(forms.ModelForm):
    """
    Batch creation/edit form with dynamic academic year dropdown.
    """

    academic_year = forms.ChoiceField()

    class Meta:
        model = Batch
        fields = ["name", "academic_year"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Example: S1 MCA"
            }),
        }

    # -----------------------------------------------------
    # Dynamic year choices
    # -----------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        start_year = 2025
        current_year = date.today().year

        choices = []

        for year in range(start_year, current_year + 1):
            next_short = str(year + 1)[-2:]
            label = f"{year}-{next_short}"
            choices.append((label, label))

        self.fields["academic_year"].choices = choices

        # preselect current academic year
        if not self.instance.pk:
            self.fields["academic_year"].initial = choices[-1][0]

# =========================================================
# Manual Student Create Form
# =========================================================
class ManualStudentCreateForm(forms.Form):
    """
    Simple admin form for manual provisioning.
    """

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Full name"
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "class": "form-input",
            "placeholder": "student@email.com"
        })
    )

# =========================================================
# CSV Upload Form
# =========================================================
class StudentCSVUploadForm(forms.Form):
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            "accept": ".csv",
            "class": "form-input"
        })
    )
