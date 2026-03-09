from django.shortcuts import redirect
from functools import wraps


def student_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = request.user

        if not user.is_authenticated:
            return redirect("accounts:login")

        if getattr(user, "role", None) != "STUDENT":
            return redirect("accounts:login")

        return view_func(request, *args, **kwargs)

    return wrapper