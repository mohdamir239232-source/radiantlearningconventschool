from schoolerp.access import build_module_access, resolve_role_key
from students.models import PaymentOptionSetting, SchoolSetting, SystemOptionSetting


def user_access_context(request):
    user_obj = getattr(request, 'user', None)
    module_access = build_module_access(user_obj)
    role_key = resolve_role_key(user_obj)

    role_label_map = {
        'superadmin': 'Super Admin',
        'principal': 'Principal',
        'viceprincipal': 'Vice Principal',
        'accountant': 'Accountant',
        'teacher': 'Teacher',
        'reception': 'Reception',
        'staff': 'Staff Admin',
        'anonymous': 'Guest',
    }

    school_setting = SchoolSetting.objects.first()
    option_setting = SystemOptionSetting.objects.first()
    payment_setting = PaymentOptionSetting.objects.first()

    return {
        'module_access': module_access,
        'current_role_key': role_key,
        'current_role_label': role_label_map.get(role_key, role_key.title()),
        'school_setting': school_setting,
        'option_setting_global': option_setting,
        'payment_setting_global': payment_setting,
    }
