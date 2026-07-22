from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser and 'Administrator' in roles:
                return view_func(request, *args, **kwargs)
            if request.user.groups.filter(name__in=roles).exists():
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Anda tidak memiliki hak akses ke halaman tersebut.')
            return redirect('role_redirect')
        return wrapped
    return decorator
