# ======================================================
# TEACHER FORMS – EduDOC
# Classroom = Assignment Entity
# Manual Rule Configuration Only (PDF workflow removed)
# ======================================================

from django import forms
from django.utils import timezone
from .models import Classroom
from accounts.models import TeacherBatch


# ======================================================
# CLASSROOM CREATION FORM
# ======================================================

class ClassroomForm(forms.ModelForm):
    """
    Classroom Creation Form.

    Responsibilities
    ----------------
    • Teacher-scoped batch selection
    • Assignment metadata
    • Submission configuration
    • Deadline validation

    NOTE:
    Classroom acts as Activity/Assignment.
    Guideline PDF system permanently removed.
    """

    # --------------------------------------------------
    # Custom datetime picker (AM/PM supported)
    # --------------------------------------------------
    deadline = forms.DateTimeField(
        input_formats=["%Y-%m-%d %I:%M %p"],
        widget=forms.TextInput(
            attrs={
                "id": "deadlinePicker",
                "class": "form-control",
            }
        ),
    )

    class Meta:
        model = Classroom
        fields = [
            "batch",
            "name",
            "deadline",
            "max_marks",
        ]

        widgets = {
            "batch": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "max_marks": forms.NumberInput(attrs={"class": "form-control"}),
        }

    # --------------------------------------------------
    # Restrict batches using TeacherBatch mapping
    # --------------------------------------------------
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop("teacher", None)
        super().__init__(*args, **kwargs)

        if teacher:
            allowed_batches = TeacherBatch.objects.filter(
                teacher=teacher
            ).values_list("batch_id", flat=True)

            self.fields["batch"].queryset = (
                self.fields["batch"].queryset.filter(id__in=allowed_batches)
            )

    # --------------------------------------------------
    # VALIDATIONS
    # --------------------------------------------------

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]

        if deadline <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")

        return deadline

    def clean_max_marks(self):
        value = self.cleaned_data["max_marks"]

        if value <= 0:
            raise forms.ValidationError("Max marks must be positive.")

        return value


# ======================================================
# MANUAL COMPLIANCE RULE FORM
# ======================================================

class ManualComplianceForm(forms.Form):
    """
    Primary rule definition interface.

    Teachers manually configure document
    compliance rules which are later stored
    as JSON inside Classroom.rules_json.

    Browser required validation disabled
    because rules are configured via tab UI.
    """

    input_attrs = {"class": "form-input"}
    select_attrs = {"class": "form-input"}

    # =====================================================
    # PAGE RULES
    # =====================================================

    min_pages = forms.IntegerField(widget=forms.NumberInput(attrs=input_attrs))
    max_pages = forms.IntegerField(widget=forms.NumberInput(attrs=input_attrs))

    paper_size = forms.ChoiceField(
        choices=[
            ("A4", "A4"),
            ("LETTER", "Letter"),
            ("LEGAL", "Legal"),
        ],
        widget=forms.Select(attrs=select_attrs),
    )

    # =====================================================
    # MARGIN UNIT
    # =====================================================

    margin_unit = forms.ChoiceField(
        choices=[("inch", "Inches"), ("cm", "Centimeters")],
        initial="inch",
        widget=forms.Select(attrs=select_attrs),
    )

    # =====================================================
    # MARGINS
    # =====================================================

    margin_top = forms.FloatField(widget=forms.NumberInput(attrs=input_attrs))
    margin_bottom = forms.FloatField(widget=forms.NumberInput(attrs=input_attrs))
    margin_left = forms.FloatField(widget=forms.NumberInput(attrs=input_attrs))
    margin_right = forms.FloatField(widget=forms.NumberInput(attrs=input_attrs))

    # =====================================================
    # FONT RULES
    # =====================================================

    font_name = forms.ChoiceField(
        choices=[
            ("Times New Roman", "Times New Roman"),
            ("Arial", "Arial"),
            ("Calibri", "Calibri"),
            ("Cambria", "Cambria"),
        ],
        widget=forms.Select(attrs=select_attrs),
    )

    font_color = forms.ChoiceField(
        choices=[("black", "Black"), ("dark_blue", "Dark Blue")],
        widget=forms.Select(attrs=select_attrs),
    )

    enforce_uniform_font = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "toggle-checkbox"}),
    )

    # =====================================================
    # LINE SPACING
    # =====================================================

    SPACING_CHOICES = [
        (1, "Single"),
        (1.15, "1.15"),
        (1.5, "One and Half"),
        (2, "Double"),
    ]

    main_line_spacing = forms.ChoiceField(choices=SPACING_CHOICES)
    reference_spacing = forms.ChoiceField(choices=SPACING_CHOICES)
    certificate_spacing = forms.ChoiceField(choices=SPACING_CHOICES)
    acknowledgement_spacing = forms.ChoiceField(choices=SPACING_CHOICES)

    # =====================================================
    # STRUCTURE RULES
    # =====================================================

    required_sections = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 4})
    )

    required_chapters = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 4})
    )

    # =====================================================
    # REFERENCES
    # =====================================================

    enforce_reference_alphabetical = forms.BooleanField(required=False)
    enforce_author_year_format = forms.BooleanField(required=False)

    # =====================================================
    # FIGURES
    # =====================================================

    chapter_based_numbering = forms.BooleanField(required=False)

    appendix_prefix = forms.ChoiceField(
        choices=[("A", "A"), ("APPENDIX", "Appendix"), ("NONE", "None")]
    )

    # =====================================================
    # HEADER RULE
    # =====================================================

    HEADER_POSITIONS = [
        ("left", "Left"),
        ("center", "Center"),
        ("right", "Right"),
    ]

    header_required = forms.BooleanField(required=False)
    header_position = forms.ChoiceField(
        choices=HEADER_POSITIONS, required=False
    )
    header_text = forms.CharField(required=False)

    # =====================================================
    # FOOTER RULE
    # =====================================================

    footer_required = forms.BooleanField(required=False)
    footer_position = forms.ChoiceField(
        choices=HEADER_POSITIONS, required=False
    )
    footer_text = forms.CharField(required=False)

    # =====================================================
    # PAGE NUMBER RULE
    # =====================================================

    page_number_required = forms.BooleanField(required=False)

    PAGE_NUMBER_POSITIONS = [
        ("top_left", "Top Left"),
        ("top_center", "Top Center"),
        ("top_right", "Top Right"),
        ("bottom_left", "Bottom Left"),
        ("bottom_center", "Bottom Center"),
        ("bottom_right", "Bottom Right"),
    ]

    PAGE_NUMBER_STYLE = [
        ("1,2,3", "1,2,3"),
        ("i,ii,iii", "i,ii,iii"),
        ("I,II,III", "I,II,III"),
    ]

    page_number_position = forms.ChoiceField(
        choices=PAGE_NUMBER_POSITIONS,
        required=False,
    )

    page_number_style = forms.ChoiceField(
        choices=PAGE_NUMBER_STYLE,
        required=False,
    )
    # =====================================================
        # FONT SIZE RULES
        # =====================================================

    content_font_size = forms.IntegerField(required=False)
    heading_font_size = forms.IntegerField(required=False)
    subheading_font_size = forms.IntegerField(required=False)

        # =====================================================
        # CHAPTER NUMBERING
        # =====================================================

    chapter_numbering_enabled = forms.BooleanField(required=False)
    chapter_start_number = forms.IntegerField(required=False)

        # =====================================================
        # SUBHEADING NUMBERING
        # =====================================================

    subheading_numbering_enabled = forms.BooleanField(required=False)

        # =====================================================
        # GRAMMAR
        # =====================================================

    grammar_check_enabled = forms.BooleanField(required=False)

        # =====================================================
        # BORDER
        # =====================================================

    border_required = forms.BooleanField(required=False)

    # =====================================================
    # INIT — Disable browser required validation
    # =====================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.required = False

    # =====================================================
    # GLOBAL VALIDATION
    # =====================================================

    def clean(self):
        cleaned = super().clean()

        # ---------- PAGE LIMIT VALIDATION ----------
        min_pages = cleaned.get("min_pages")
        max_pages = cleaned.get("max_pages")

        if min_pages and max_pages:
            if min_pages > max_pages:
                raise forms.ValidationError(
                    "Minimum pages cannot exceed maximum pages."
                )

        # ---------- MARGIN VALIDATION ----------
        for field in [
            "margin_top",
            "margin_bottom",
            "margin_left",
            "margin_right",
        ]:
            value = cleaned.get(field)
            if value is not None and value < 0:
                self.add_error(field, "Margin cannot be negative.")

        # ---------- HEADER CONDITIONAL ----------
        if cleaned.get("header_required"):
            if not cleaned.get("header_text"):
                self.add_error(
                    "header_text",
                    "Header text required when header is enabled.",
                )

        # ---------- FOOTER CONDITIONAL ----------
        if cleaned.get("footer_required"):
            if not cleaned.get("footer_text"):
                self.add_error(
                    "footer_text",
                    "Footer text required when footer is enabled.",
                )

        # ---------- PAGE NUMBER CONDITIONAL ----------
        if cleaned.get("page_number_required"):
            if not cleaned.get("page_number_position"):
                self.add_error(
                    "page_number_position",
                    "Select page number position.",
                )
            if not cleaned.get("page_number_style"):
                self.add_error(
                    "page_number_style",
                    "Select page number style.",
                )
        if cleaned.get("chapter_numbering_enabled"):
            if cleaned.get("chapter_start_number") is None:
                self.add_error("chapter_start_number", "Start number required.")
        

        return cleaned