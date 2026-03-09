from django.shortcuts import redirect
from django.urls import reverse
from accounts.models import User


class ForcePasswordChangeMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:

            # allow static and media resources
            if request.path.startswith("/static/") or request.path.startswith("/media/"):
                return self.get_response(request)

            # allow password change page and logout
            allowed_paths = [
                reverse("accounts:force_password_change"),
                reverse("accounts:logout"),
            ]

            # enforce ONLY for students
            if (
                request.user.role == User.Role.STUDENT
                and request.user.first_login
                and request.path not in allowed_paths
            ):
                return redirect("accounts:force_password_change")

        return self.get_response(request)