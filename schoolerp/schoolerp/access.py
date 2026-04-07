from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from students.models import RoleModulePermission


MODULE_KEYS = [
    'students',
    'fee',
    'attendance',
    'academic',
    'staff',
    'exam',
    'transport',
    'settings',
    'reports',
]

MODULE_FIELD_MAP = {
    'students': 'can_access_students',
    'fee': 'can_access_fee',
    'attendance': 'can_access_attendance',
    'academic': 'can_access_academic',
    'staff': 'can_access_staff',
    'exam': 'can_access_exam',
    'transport': 'can_access_transport',
    'settings': 'can_access_settings',
    'reports': 'can_access_reports',
}

ROLE_GROUP_TO_KEY = {
    'super admin': 'superadmin',
    'principal': 'principal',
    'vice principal': 'viceprincipal',
    'accountant': 'accountant',
    'teacher': 'teacher',
    'reception': 'reception',
    'staff admin': 'staff',
}


def resolve_role_key(user_obj):
    if not user_obj or not user_obj.is_authenticated:
        return 'anonymous'

    if user_obj.is_superuser:
        return 'superadmin'

    group = user_obj.groups.order_by('name').first()
    if not group:
        return 'staff'

    normalized = group.name.strip().lower()
    return ROLE_GROUP_TO_KEY.get(normalized, normalized.replace(' ', ''))


def build_module_access(user_obj):
    access = {key: False for key in MODULE_KEYS}

    if not user_obj or not user_obj.is_authenticated:
        return access

    if user_obj.is_superuser:
        return {key: True for key in MODULE_KEYS}

    role_key = resolve_role_key(user_obj)
    permission_row = RoleModulePermission.objects.filter(role_key=role_key).first()

    if permission_row is None:
        return access

    for module_key, field_name in MODULE_FIELD_MAP.items():
        access[module_key] = bool(getattr(permission_row, field_name, False))

    return access


def can_access_module(user_obj, module_key):
    if not module_key:
        return True

    return build_module_access(user_obj).get(module_key, False)


def require_module_access(module_key):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user_obj = getattr(request, 'user', None)

            if not user_obj or not user_obj.is_authenticated:
                return redirect(f'/login/?next={request.get_full_path()}')

            if can_access_module(user_obj, module_key):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to access that module.')
            return redirect('/dashboard/')

        return _wrapped

    return decorator


def module_required_for_path(path):
    if not path:
        return None

    prefix_map = [
        ('/student/', 'students'),
        ('/master/', 'students'),
        ('/certificate/', 'academic'),
        ('/attendance/', 'attendance'),
        ('/academic/', 'academic'),
        ('/staff/', 'staff'),
        ('/fee-master/', 'fee'),
        ('/fee/', 'fee'),
        ('/exam/', 'exam'),
        ('/transport/', 'transport'),
        ('/settings/', 'settings'),
        ('/account/expense', 'reports'),
        ('/account/income', 'reports'),
    ]

    for prefix, module_key in prefix_map:
        if path.startswith(prefix):
            return module_key

    return None
