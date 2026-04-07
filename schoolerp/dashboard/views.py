from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils.http import url_has_allowed_host_and_scheme
from students.models import AcademicSession, Student, Fee


DEFAULT_SUPERADMIN_USERNAME = 'admin'
DEFAULT_SUPERADMIN_PASSWORD = 'Admin@123'


def ensure_default_super_admin():
    if not settings.DEBUG:
        return False

    user_model = get_user_model()
    if user_model.objects.exists():
        return False

    user_model.objects.create_superuser(
        username=DEFAULT_SUPERADMIN_USERNAME,
        email='admin@rlcs.local',
        password=DEFAULT_SUPERADMIN_PASSWORD,
    )
    return True


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def login_view(request):
    created_default_user = ensure_default_super_admin()

    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or '/dashboard/'
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = '/dashboard/'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(next_url)

        messages.error(request, 'Invalid username or password. Please try again.')

    context = {
        'next_url': next_url,
        'show_default_credentials': settings.DEBUG,
        'default_username': DEFAULT_SUPERADMIN_USERNAME,
        'default_password': DEFAULT_SUPERADMIN_PASSWORD,
        'created_default_user': created_default_user,
    }
    return render(request, 'login.html', context)


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def account_view(request):
    return render(request, 'account.html')


@login_required
def change_password_view(request):
    if request.method == 'POST':
        new_password = request.POST.get('password', '').strip()

        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password updated successfully.')
            return redirect('change_password')

    return render(request, 'change_password.html')


@login_required
def dashboard(request):
    selected_session_id = request.GET.get('session')
    sessions = AcademicSession.objects.filter(is_active=True).order_by('-id')

    student_qs = Student.objects.all()
    fee_qs = Fee.objects.all()
    selected_session = None

    if selected_session_id:
        try:
            selected_session = AcademicSession.objects.get(id=selected_session_id)
            student_qs = student_qs.filter(session=selected_session)
            fee_qs = fee_qs.filter(session=selected_session)
        except AcademicSession.DoesNotExist:
            selected_session = None

    total_students = student_qs.count()
    total_fee = fee_qs.aggregate(Sum('total_fee'))['total_fee__sum'] or 0
    due_fee = fee_qs.aggregate(Sum('due_fee'))['due_fee__sum'] or 0
    paid_fee = total_fee - due_fee if total_fee else 0

    monthly_agg = (
        fee_qs.exclude(date__isnull=True)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(total=Sum('total_fee'), paid=Sum('paid_fee'))
        .order_by('month')
    )

    monthly_labels = [entry['month'].strftime('%b %Y') for entry in monthly_agg]
    monthly_total_values = [float(entry['total'] or 0) for entry in monthly_agg]
    monthly_paid_values = [float(entry['paid'] or 0) for entry in monthly_agg]

    class_agg = (
        student_qs.values('student_class')
        .annotate(total=Count('id'))
        .order_by('student_class')
    )
    class_labels = []
    class_counts = []
    for entry in class_agg:
        class_name = entry['student_class'] or 'N/A'
        class_labels.append(class_name)
        class_counts.append(entry['total'])

    recent_fees = fee_qs.select_related('student').order_by('-date', '-id')[:5]

    context = {
        'total_students': total_students,
        'total_fee': total_fee,
        'paid_fee': paid_fee,
        'due_fee': due_fee,
        'sessions': sessions,
        'selected_session_id': int(selected_session_id) if selected_session_id and selected_session_id.isdigit() else '',
        'selected_session': selected_session,
        'monthly_labels': monthly_labels,
        'monthly_total_values': monthly_total_values,
        'monthly_paid_values': monthly_paid_values,
        'fee_status_labels': ['Paid Fee', 'Due Fee'],
        'fee_status_values': [float(paid_fee), float(due_fee)],
        'class_labels': class_labels,
        'class_counts': class_counts,
        'recent_fees': recent_fees,
    }

    return render(request, 'students/dashboard.html', context)
