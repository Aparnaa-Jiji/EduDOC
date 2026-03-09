from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


# ======================================================
# Custom Admin for extended User model (EduDOC)
# ======================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    # ---------------------------------
    # Edit page layout
    # ---------------------------------
    fieldsets = UserAdmin.fieldsets + (
        (
            "EduDOC Role Info",
            {
                "fields": (
                    "role",
                    "is_approved",
                )
            },
        ),
    )

    # ---------------------------------
    # Create page layout
    # ---------------------------------
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "EduDOC Role Info",
            {
                "fields": (
                    "role",
                    "is_approved",
                )
            },
        ),
    )

    # ---------------------------------
    # List page
    # ---------------------------------
    list_display = (
        "username",
        "get_full_name",   # NEW
        "email",
        "role",
        "is_approved",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "role",
        "is_approved",
        "is_staff",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "first_name",      # NEW
        "last_name",       # NEW
    )

    ordering = ("-date_joined",)
    readonly_fields = ("last_login", "date_joined")

    actions = ["approve_users"]

    # ---------------------------------
    # Display full name
    # ---------------------------------
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = "Name"

    # ---------------------------------
    # Bulk approval action (FIXED)
    # ---------------------------------
    @admin.action(description="Approve selected users")
    def approve_users(self, request, queryset):
        queryset.update(
            is_approved=True,
            is_active=True   # CRITICAL FIX
        )
