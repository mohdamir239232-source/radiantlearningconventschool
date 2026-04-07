from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from schoolerp.access import build_module_access, module_required_for_path


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_prefixes = (
            '/login/',
            '/admin/',
            '/api/mobile/',
            settings.STATIC_URL,
            settings.MEDIA_URL,
        )

        is_public_path = any(request.path.startswith(prefix) for prefix in public_prefixes if prefix)

        if not request.user.is_authenticated and not is_public_path:
            return redirect(f'/login/?next={request.get_full_path()}')

        if request.user.is_authenticated:
            unrestricted_paths = (
                '/dashboard/',
                '/account/admin/',
                '/account/change-password/',
                '/account/logout/',
            )

            if not any(request.path.startswith(prefix) for prefix in unrestricted_paths):
                required_module = module_required_for_path(request.path)
                if required_module:
                    module_access = build_module_access(request.user)
                    if not module_access.get(required_module, False):
                        messages.error(request, 'You do not have permission to access that module.')
                        return redirect('/dashboard/')

        return self.get_response(request)