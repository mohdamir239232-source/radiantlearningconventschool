from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from decimal import Decimal, InvalidOperation
import csv
import io
import json
import secrets
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt

from .forms import ALL_DISTRICTS, STATE_DISTRICT_MAP, StudentAdmissionForm, StudentProfileUpdateForm
from .models import (
    AcademicNotice,
    AcademicSession,
    ClassModel,
    Designation,
    PaymentOptionSetting,
    MobileAppControlSetting,
    MobileAppDevice,
    MobileAppRelease,
    RoleModulePermission,
    SchoolSetting,
    StaffProfile,
    Student,
    StudentAttendance,
    Subject,
    SystemOptionSetting,
    TimeTableEntry,
    HomeworkSetup,
    CourseSchedule,
    Syllabus,
    DateSheet,
    HolidayList,
    WhatsAppApiSetting,
)
from schoolerp.access import build_module_access, can_access_module, require_module_access
from transport.models import VehicleRoute


SETTINGS_MODULES = {
    'user': {
        'title': 'User Management',
        'description': 'Create and maintain user accounts for administrative and operational teams.',
        'items': ['Create User', 'Edit User Profile', 'Assign Role', 'Reset User Access'],
    },
    'permissions': {
        'title': 'User Permissions',
        'description': 'Control module-level permissions and access boundaries for each role.',
        'items': ['Role Matrix', 'Module Access Rules', 'Data Visibility Rules', 'Approval Authority'],
    },
    'school': {
        'title': 'School Settings',
        'description': 'Configure institution-wide profile information and academic defaults.',
        'items': ['School Profile', 'Session Defaults', 'Identity Branding', 'Contact and Address'],
    },
    'option': {
        'title': 'Option Settings',
        'description': 'Set behavior toggles and operation preferences for day-to-day workflows.',
        'items': ['Admission Options', 'Receipt Options', 'Notification Flags', 'Document Preferences'],
    },
    'payment': {
        'title': 'Payment Option Settings',
        'description': 'Configure fee payment channels, policies, and transaction controls.',
        'items': ['Payment Modes', 'Online Gateway Rules', 'Late Fee Policy', 'Receipt Format'],
    },
    'whatsapp': {
        'title': 'WhatsApp API Settings',
        'description': 'Connect WhatsApp API credentials and configure automated ERP notifications.',
        'items': ['Cloud API Credentials', 'Webhook Verification', 'Message Templates', 'Event Alerts'],
    },
    'mobileapp': {
        'title': 'Mobile App Control Center',
        'description': 'Control school app version policy, maintenance state, and module availability from ERP.',
        'items': ['App Version Control', 'Maintenance Mode', 'Audience Access Flags', 'App Configuration API'],
    },
}

STAFF_MODULES = {
    'view': {
        'title': 'Staff Directory',
        'description': 'Search and review all active staff profiles with role visibility and account state.',
        'items': ['Staff Directory', 'Role Visibility', 'Account Status', 'Quick Lookup'],
    },
    'add': {
        'title': 'Add Staff Profile',
        'description': 'Create staff user accounts with role mapping and secure onboarding defaults.',
        'items': ['User Provisioning', 'Role Assignment', 'Secure Password Rules', 'Activation Control'],
    },
    'idcard': {
        'title': 'Staff ID Cards',
        'description': 'Prepare structured identity card generation flow for staff records and print layout.',
        'items': ['Profile Snapshot', 'Template Layout', 'Batch Print Queue', 'Card Verification'],
    },
    'attendance': {
        'title': 'Staff Attendance',
        'description': 'Track daily in-out attendance markers for teaching and non-teaching staff.',
        'items': ['Daily Marking', 'Shift Mapping', 'Late Entry Flags', 'Leave Reconciliation'],
    },
    'attendance-report': {
        'title': 'Staff Attendance Report',
        'description': 'Generate attendance summaries by date range, role, and compliance status.',
        'items': ['Date Filters', 'Role-wise Summary', 'Presence Ratio', 'Export Ready'],
    },
    'permission': {
        'title': 'Teacher Permissions',
        'description': 'Manage temporary permissions and approval controls for teacher requests.',
        'items': ['Permission Requests', 'Approval Actions', 'Duration Tracking', 'Audit Notes'],
    },
    'experience-certificate': {
        'title': 'Experience Certificate',
        'description': 'Prepare formal service certificate workflow with standard content and signatory info.',
        'items': ['Template Builder', 'Service Period', 'Authorized Signatory', 'Print Output'],
    },
    'daily-performance': {
        'title': 'Daily Performance Report',
        'description': 'Capture staff daily performance logs with clear review structure.',
        'items': ['Daily Logs', 'Department Notes', 'Supervisor Remarks', 'Follow-up Tasks'],
    },
    'monthly-performance': {
        'title': 'Monthly Performance Report',
        'description': 'Consolidate monthly staff performance KPIs for administration review.',
        'items': ['Monthly KPI Rollup', 'Attendance Correlation', 'Department Comparison', 'Review Summary'],
    },
}

CERTIFICATE_TYPE_CONFIG = {
    'appreciation': {
        'title': 'Appreciation Certificate',
        'headline': 'Certificate Of Appreciation',
        'subtitle': 'For exemplary attitude, discipline, and positive contribution.',
    },
    'participation': {
        'title': 'Participation Certificate',
        'headline': 'Certificate Of Participation',
        'subtitle': 'For active participation and dedicated involvement.',
    },
    'achievement': {
        'title': 'Achievement Certificate',
        'headline': 'Certificate Of Achievement',
        'subtitle': 'For outstanding performance and achievement.',
    },
}

ROLE_OPTIONS = [
    ('superadmin', 'Super Admin'),
    ('principal', 'Principal'),
    ('viceprincipal', 'Vice Principal'),
    ('accountant', 'Accountant'),
    ('teacher', 'Teacher'),
    ('reception', 'Reception'),
    ('staff', 'Staff Admin'),
]

ROLE_LABEL_MAP = {key: label for key, label in ROLE_OPTIONS}

PERMISSION_FIELDS = [
    ('can_access_students', 'Students'),
    ('can_access_fee', 'Fee'),
    ('can_access_attendance', 'Attendance'),
    ('can_access_academic', 'Academic'),
    ('can_access_staff', 'Staff'),
    ('can_access_exam', 'Exam'),
    ('can_access_transport', 'Transport'),
    ('can_access_settings', 'Settings'),
    ('can_access_reports', 'Reports'),
]


def _split_modules_csv(raw_value):
    return [item.strip() for item in (raw_value or '').split(',') if item.strip()]


VALID_MONTH_CODES = (
    'apr', 'may', 'jun', 'jul', 'aug', 'sep',
    'oct', 'nov', 'dec', 'jan', 'feb', 'mar',
)


def _normalize_month_csv(raw_value, default_value, allow_multiple=True):
    raw_tokens = [token.strip().lower() for token in (raw_value or '').split(',') if token.strip()]
    selected = set(token for token in raw_tokens if token in VALID_MONTH_CODES)

    if not selected:
        return default_value

    ordered = [month for month in VALID_MONTH_CODES if month in selected]
    if allow_multiple:
        return ','.join(ordered)
    return ordered[0]


def resolve_role_from_user(user_obj):
    if user_obj.is_superuser:
        return 'Super Admin'

    first_group = user_obj.groups.order_by('name').first()
    if first_group:
        return first_group.name

    return 'Staff Admin'


def session_list(request):
    sessions = AcademicSession.objects.order_by('-id')
    return render(request, 'students/session.html', {'sessions': sessions})


@require_http_methods(['POST'])
def session_add(request):
    try:
        name = request.POST.get('name', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()

        if not all([name, start_date, end_date]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if AcademicSession.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'Session name already exists'})

        AcademicSession.objects.create(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
        )
        return JsonResponse({'success': True, 'message': 'Session added successfully'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['GET'])
def session_get_data(request, session_id):
    try:
        session = AcademicSession.objects.get(id=session_id)
        return JsonResponse({
            'success': True,
            'session': {
                'id': session.id,
                'name': session.name,
                'start_date': str(session.start_date),
                'end_date': str(session.end_date),
            }
        })
    except AcademicSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})


@require_http_methods(['POST'])
def session_edit(request, session_id):
    try:
        session = AcademicSession.objects.get(id=session_id)
        name = request.POST.get('name', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()

        if not all([name, start_date, end_date]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if AcademicSession.objects.filter(name=name).exclude(id=session_id).exists():
            return JsonResponse({'success': False, 'error': 'Session name already exists'})

        session.name = name
        session.start_date = start_date
        session.end_date = end_date
        session.save()
        return JsonResponse({'success': True, 'message': 'Session updated successfully'})
    except AcademicSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['POST'])
def session_delete(request, session_id):
    try:
        session = AcademicSession.objects.get(id=session_id)
        session.delete()
        return JsonResponse({'success': True, 'message': 'Session deleted successfully'})
    except AcademicSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session not found'})


def class_list(request):
    classes = ClassModel.objects.order_by('name', 'section')
    return render(request, 'students/class_list.html', {'classes': classes})


@require_http_methods(['POST'])
def class_add(request):
    try:
        name = request.POST.get('name', '').strip()
        section = request.POST.get('section', '').strip()
        description = request.POST.get('description', '').strip()

        if not all([name, section]):
            return JsonResponse({'success': False, 'error': 'Name and section are required'})

        if ClassModel.objects.filter(name=name, section=section).exists():
            return JsonResponse({'success': False, 'error': 'Class with this section already exists'})

        ClassModel.objects.create(name=name, section=section, description=description, is_active=True)
        return JsonResponse({'success': True, 'message': 'Class added successfully'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['GET'])
def class_get_data(request, class_id):
    try:
        class_obj = ClassModel.objects.get(id=class_id)
        return JsonResponse({
            'success': True,
            'class': {
                'id': class_obj.id,
                'name': class_obj.name,
                'section': class_obj.section or '',
                'description': class_obj.description or '',
            },
        })
    except ClassModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'})


@require_http_methods(['POST'])
def class_edit(request, class_id):
    try:
        class_obj = ClassModel.objects.get(id=class_id)
        name = request.POST.get('name', '').strip()
        section = request.POST.get('section', '').strip()
        description = request.POST.get('description', '').strip()

        if not all([name, section]):
            return JsonResponse({'success': False, 'error': 'Name and section are required'})

        if ClassModel.objects.filter(name=name, section=section).exclude(id=class_id).exists():
            return JsonResponse({'success': False, 'error': 'Class with this section already exists'})

        class_obj.name = name
        class_obj.section = section
        class_obj.description = description
        class_obj.save()
        return JsonResponse({'success': True, 'message': 'Class updated successfully'})
    except ClassModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['POST'])
def class_delete(request, class_id):
    try:
        class_obj = ClassModel.objects.get(id=class_id)
        class_obj.delete()
        return JsonResponse({'success': True, 'message': 'Class deleted successfully'})
    except ClassModel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Class not found'})


def designation_list(request):
    designations = Designation.objects.order_by('name')
    return render(request, 'students/designation_list.html', {'designations': designations})


@require_http_methods(['POST'])
def designation_add(request):
    try:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            return JsonResponse({'success': False, 'error': 'Designation name is required'})

        if Designation.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'Designation already exists'})

        Designation.objects.create(name=name, description=description, is_active=True)
        return JsonResponse({'success': True, 'message': 'Designation added successfully'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['GET'])
def designation_get_data(request, designation_id):
    try:
        designation = Designation.objects.get(id=designation_id)
        return JsonResponse({
            'success': True,
            'designation': {
                'id': designation.id,
                'name': designation.name,
                'description': designation.description or '',
            },
        })
    except Designation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Designation not found'})


@require_http_methods(['POST'])
def designation_edit(request, designation_id):
    try:
        designation = Designation.objects.get(id=designation_id)
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        if not name:
            return JsonResponse({'success': False, 'error': 'Designation name is required'})

        if Designation.objects.filter(name=name).exclude(id=designation_id).exists():
            return JsonResponse({'success': False, 'error': 'Designation already exists'})

        designation.name = name
        designation.description = description
        designation.save()
        return JsonResponse({'success': True, 'message': 'Designation updated successfully'})
    except Designation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Designation not found'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['POST'])
def designation_delete(request, designation_id):
    try:
        designation = Designation.objects.get(id=designation_id)
        designation.delete()
        return JsonResponse({'success': True, 'message': 'Designation deleted successfully'})
    except Designation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Designation not found'})


def subject_list(request):
    subjects = Subject.objects.order_by('name')
    return render(request, 'students/subject_list.html', {'subjects': subjects})


@require_http_methods(['POST'])
def subject_add(request):
    try:
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()

        if not all([name, code]):
            return JsonResponse({'success': False, 'error': 'Subject name and code are required'})

        if Subject.objects.filter(code=code).exists():
            return JsonResponse({'success': False, 'error': 'Subject code already exists'})

        Subject.objects.create(name=name, code=code, description=description, is_active=True)
        return JsonResponse({'success': True, 'message': 'Subject added successfully'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['GET'])
def subject_get_data(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id)
        return JsonResponse({
            'success': True,
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'description': subject.description or '',
            },
        })
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found'})


@require_http_methods(['POST'])
def subject_edit(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id)
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()

        if not all([name, code]):
            return JsonResponse({'success': False, 'error': 'Subject name and code are required'})

        if Subject.objects.filter(code=code).exclude(id=subject_id).exists():
            return JsonResponse({'success': False, 'error': 'Subject code already exists'})

        subject.name = name
        subject.code = code
        subject.description = description
        subject.save()
        return JsonResponse({'success': True, 'message': 'Subject updated successfully'})
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found'})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)})


@require_http_methods(['POST'])
def subject_delete(request, subject_id):
    try:
        subject = Subject.objects.get(id=subject_id)
        subject.delete()
        return JsonResponse({'success': True, 'message': 'Subject deleted successfully'})
    except Subject.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subject not found'})


def student_admission(request):
    if request.method == 'POST':
        form = StudentAdmissionForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'Student admitted successfully with admission no. {student.admission_number}.')
            return redirect('students:student_detail', student_id=student.id)
    else:
        form = StudentAdmissionForm(initial={'admission_date': timezone.localdate()})

    route_fare_map = {
        route.id: float(route.fare_amount)
        for route in VehicleRoute.objects.filter(is_active=True)
    }

    route_village_map = {
        route.id: route.get_stops_list()
        for route in VehicleRoute.objects.filter(is_active=True)
    }

    route_village_fare_map = {
        route.id: route.get_village_fare_list()
        for route in VehicleRoute.objects.filter(is_active=True)
    }

    class_section_map = {}
    for class_item in ClassModel.objects.filter(is_active=True).order_by('name', 'section'):
        class_section_map.setdefault(class_item.name, [])
        if class_item.section and class_item.section not in class_section_map[class_item.name]:
            class_section_map[class_item.name].append(class_item.section)

    return render(request, 'students/admission_form.html', {
        'form': form,
        'next_admission_number': Student.get_next_admission_number(),
        'route_fare_map': route_fare_map,
        'route_village_map': route_village_map,
        'route_village_fare_map': route_village_fare_map,
        'class_section_map': class_section_map,
        'state_district_map': STATE_DISTRICT_MAP,
        'all_districts': ALL_DISTRICTS,
    })


def student_list(request):
    students = Student.objects.select_related('session', 'transport_route').order_by('name')
    return render(request, 'students/student_list.html', {'students': students})


def student_detail(request, student_id):
    student = get_object_or_404(Student.objects.prefetch_related('subjects'), pk=student_id)
    return render(request, 'students/student_detail.html', {'student': student})


def student_update(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        form = StudentProfileUpdateForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student profile updated successfully.')
            return redirect('students:student_detail', student_id=student.id)
    else:
        form = StudentProfileUpdateForm(instance=student)

    return render(request, 'students/student_update.html', {
        'form': form,
        'student': student,
    })


@require_POST
def student_delete(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    student_name = student.name
    student.delete()
    messages.success(request, f'Student {student_name} deleted successfully.')
    return redirect('students:student_list_page')


def assign_subject_select(request):
    students = Student.objects.order_by('name')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    class_rows = ClassModel.objects.filter(is_active=True).order_by('name', 'section')
    class_section_map = {}
    for row in class_rows:
        class_section_map.setdefault(row.name, [])
        if row.section and row.section not in class_section_map[row.name]:
            class_section_map[row.name].append(row.section)

    class_names = list(class_section_map.keys())
    if not class_names:
        class_names = [str(i) for i in range(1, 13)]

    return render(request, 'students/assign_subject_select.html', {
        'students': students,
        'subjects': subjects,
        'class_names': class_names,
        'class_section_map': class_section_map,
    })


def assign_subject(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    subjects = Subject.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        subject_ids = request.POST.getlist('subjects')
        selected = subjects.filter(id__in=subject_ids)
        student.subjects.set(selected)
        messages.success(request, 'Subjects assigned successfully.')
        return redirect('students:student_detail', student_id=student.id)

    return render(request, 'students/assign_subject.html', {
        'student': student,
        'subjects': subjects,
        'assigned_ids': set(student.subjects.values_list('id', flat=True)),
    })


@require_POST
def assign_subject_bulk(request):
    student_class = request.POST.get('student_class', '').strip()
    section = request.POST.get('section', '').strip()
    subject_ids = request.POST.getlist('subjects')

    if not student_class:
        messages.error(request, 'Please select class for bulk subject assignment.')
        return redirect('students:assign_subject_select')

    selected_subjects = Subject.objects.filter(is_active=True, id__in=subject_ids)
    if not selected_subjects.exists():
        messages.error(request, 'Please select at least one subject.')
        return redirect('students:assign_subject_select')

    students = Student.objects.filter(student_class=student_class)
    if section and section != 'ALL':
        students = students.filter(section=section)

    count = students.count()
    if count == 0:
        messages.warning(request, 'No students found for selected class/section.')
        return redirect('students:assign_subject_select')

    for student in students:
        student.subjects.set(selected_subjects)

    section_label = section if section and section != 'ALL' else 'All Sections'
    messages.success(
        request,
        f'Subjects assigned to {count} students in class {student_class} ({section_label}).'
    )
    return redirect('students:assign_subject_select')


def promote_student_select(request):
    students = Student.objects.order_by('name')
    class_rows = ClassModel.objects.filter(is_active=True).order_by('name', 'section')
    class_section_map = {}
    for row in class_rows:
        class_section_map.setdefault(row.name, [])
        if row.section and row.section not in class_section_map[row.name]:
            class_section_map[row.name].append(row.section)

    class_names = list(class_section_map.keys())
    if not class_names:
        class_names = [str(i) for i in range(1, 13)]

    return render(request, 'students/promote_student_select.html', {
        'students': students,
        'class_names': class_names,
        'class_section_map': class_section_map,
    })


def promote_student(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    class_names = list(ClassModel.objects.filter(is_active=True).values_list('name', flat=True))
    if not class_names:
        class_names = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

    if request.method == 'POST':
        next_class = request.POST.get('next_class')
        if next_class in class_names:
            student.student_class = next_class
            student.save(update_fields=['student_class'])
            messages.success(request, 'Student promoted successfully.')
            return redirect('students:student_detail', student_id=student.id)

    return render(request, 'students/promote_student.html', {
        'student': student,
        'class_names': class_names,
    })


@require_POST
def promote_student_bulk(request):
    from_class = request.POST.get('from_class', '').strip()
    from_section = request.POST.get('from_section', '').strip()
    to_class = request.POST.get('to_class', '').strip()
    to_section = request.POST.get('to_section', '').strip()

    if not from_class or not to_class:
        messages.error(request, 'Please select both current class and promote-to class.')
        return redirect('students:promote_student_select')

    students = Student.objects.filter(student_class=from_class)
    if from_section and from_section != 'ALL':
        students = students.filter(section=from_section)

    student_list = list(students)
    if not student_list:
        messages.warning(request, 'No students found for selected class/section.')
        return redirect('students:promote_student_select')

    target_section = to_section.strip() if to_section else ''
    for student in student_list:
        student.student_class = to_class
        if target_section:
            student.section = target_section
        student.roll_no = None
        student.save()

    source_label = f'{from_class} ({from_section})' if from_section and from_section != 'ALL' else f'{from_class} (All Sections)'
    destination_label = f'{to_class} ({target_section})' if target_section else f'{to_class} (same section)'
    messages.success(
        request,
        f'{len(student_list)} students promoted from {source_label} to {destination_label}.'
    )
    return redirect('students:promote_student_select')


def academic_notice(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        publish_date = request.POST.get('publish_date', '').strip()
        if not all([title, description, publish_date]):
            messages.error(request, 'Please fill all required fields for notice.')
        else:
            AcademicNotice.objects.create(
                title=title,
                description=description,
                publish_date=publish_date,
                is_active=True,
            )
            messages.success(request, 'Notice published successfully.')
            return redirect('/academic/notice/')

    notices = AcademicNotice.objects.filter(is_active=True)
    return render(request, 'students/academic_notice.html', {'notices': notices})


def attendance_mark(request):
    selected_class = request.GET.get('class', '').strip()
    selected_section = request.GET.get('section', '').strip()
    selected_date = request.GET.get('date', '') or str(timezone.localdate())

    class_rows = ClassModel.objects.filter(is_active=True).order_by('name', 'section')
    class_section_map = {}
    for row in class_rows:
        class_section_map.setdefault(row.name, [])
        if row.section and row.section not in class_section_map[row.name]:
            class_section_map[row.name].append(row.section)

    class_names = list(class_section_map.keys())
    if not class_names:
        class_names = [str(i) for i in range(1, 13)]

    students = Student.objects.none()
    if selected_class:
        students = Student.objects.filter(student_class=selected_class).order_by('roll_no', 'name')
        if selected_section and selected_section != 'ALL':
            students = students.filter(section=selected_section)

    if request.method == 'POST':
        selected_class = request.POST.get('selected_class', '').strip()
        selected_section = request.POST.get('selected_section', '').strip()
        selected_date = request.POST.get('selected_date', '').strip() or str(timezone.localdate())

        students = Student.objects.filter(student_class=selected_class).order_by('roll_no', 'name')
        if selected_section and selected_section != 'ALL':
            students = students.filter(section=selected_section)

        count = 0
        for student in students:
            status = request.POST.get(f'status_{student.id}', StudentAttendance.STATUS_PRESENT)
            remarks = request.POST.get(f'remarks_{student.id}', '').strip()
            StudentAttendance.objects.update_or_create(
                student=student,
                attendance_date=selected_date,
                defaults={'status': status, 'remarks': remarks},
            )
            count += 1

        messages.success(request, f'Attendance saved for {count} students.')
        return redirect(f'/attendance/mark/?class={selected_class}&section={selected_section}&date={selected_date}')

    existing_map = {
        item.student_id: item
        for item in StudentAttendance.objects.filter(
            attendance_date=selected_date,
            student__in=students,
        )
    } if students else {}

    attendance_rows = []
    for student in students:
        existing = existing_map.get(student.id)
        attendance_rows.append({
            'student': student,
            'status': existing.status if existing else StudentAttendance.STATUS_PRESENT,
            'remarks': existing.remarks if existing and existing.remarks else '',
        })

    return render(request, 'students/attendance_mark.html', {
        'class_names': class_names,
        'class_section_map': class_section_map,
        'students': students,
        'attendance_rows': attendance_rows,
        'selected_class': selected_class,
        'selected_section': selected_section,
        'selected_date': selected_date,
    })


def attendance_report(request):
    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')
    selected_class = request.GET.get('class', '').strip()

    records = StudentAttendance.objects.select_related('student').all()
    if from_date:
        records = records.filter(attendance_date__gte=from_date)
    if to_date:
        records = records.filter(attendance_date__lte=to_date)
    if selected_class:
        records = records.filter(student__student_class=selected_class)

    summary = records.values('student__student_class').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status=StudentAttendance.STATUS_PRESENT)),
        absent=Count('id', filter=Q(status=StudentAttendance.STATUS_ABSENT)),
    ).order_by('student__student_class')

    class_names = list(
        ClassModel.objects.filter(is_active=True).order_by('name').values_list('name', flat=True).distinct()
    )
    return render(request, 'students/attendance_report.html', {
        'records': records[:500],
        'summary': summary,
        'from_date': from_date,
        'to_date': to_date,
        'selected_class': selected_class,
        'class_names': class_names,
    })


@login_required
def academic_time_table_create(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        class_name = request.POST.get('class_name', '').strip()
        section = request.POST.get('section', '').strip()
        day_of_week = request.POST.get('day_of_week', '').strip().lower()
        period_label = request.POST.get('period_label', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        teacher_name = request.POST.get('teacher_name', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        end_time = request.POST.get('end_time', '').strip()
        room_number = request.POST.get('room_number', '').strip()

        if not all([class_name, section, day_of_week, period_label, subject_name]):
            messages.error(request, 'Please fill class, section, day, period and subject.')
        else:
            TimeTableEntry.objects.update_or_create(
                class_name=class_name,
                section=section,
                day_of_week=day_of_week,
                period_label=period_label,
                defaults={
                    'subject_name': subject_name,
                    'teacher_name': teacher_name,
                    'start_time': start_time or None,
                    'end_time': end_time or None,
                    'room_number': room_number,
                    'source': 'manual',
                }
            )
            messages.success(request, 'Time table entry saved successfully.')
            return redirect('/academic/time-table-create/')

    selected_class = request.GET.get('class', '').strip()
    selected_section = request.GET.get('section', '').strip()

    class_names = list(
        Student.objects.exclude(student_class__isnull=True)
        .exclude(student_class__exact='')
        .order_by('student_class')
        .values_list('student_class', flat=True)
        .distinct()
    )

    sections = []
    if selected_class:
        sections = list(
            Student.objects.filter(student_class=selected_class)
            .exclude(section__isnull=True)
            .exclude(section__exact='')
            .order_by('section')
            .values_list('section', flat=True)
            .distinct()
        )

    entries = TimeTableEntry.objects.all().order_by('class_name', 'section', 'day_of_week', 'period_label')
    if selected_class:
        entries = entries.filter(class_name=selected_class)
    if selected_section:
        entries = entries.filter(section=selected_section)

    return render(request, 'students/academic_time_table_create.html', {
        'class_names': class_names,
        'sections': sections,
        'selected_class': selected_class,
        'selected_section': selected_section,
        'entries': entries[:300],
        'day_choices': TimeTableEntry.DAY_CHOICES,
    })


@login_required
def academic_time_table_upload(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        upload_file = request.FILES.get('csv_file')
        if not upload_file:
            messages.error(request, 'Please choose a CSV file first.')
            return redirect('/academic/time-table-upload/')

        try:
            content = upload_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            required_columns = {'class_name', 'section', 'day_of_week', 'period_label', 'subject_name'}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                messages.error(request, 'CSV must include: class_name, section, day_of_week, period_label, subject_name')
                return redirect('/academic/time-table-upload/')

            count = 0
            for row in reader:
                class_name = (row.get('class_name') or '').strip()
                section = (row.get('section') or '').strip()
                day_of_week = (row.get('day_of_week') or '').strip().lower()
                period_label = (row.get('period_label') or '').strip()
                subject_name = (row.get('subject_name') or '').strip()

                if not all([class_name, section, day_of_week, period_label, subject_name]):
                    continue

                TimeTableEntry.objects.update_or_create(
                    class_name=class_name,
                    section=section,
                    day_of_week=day_of_week,
                    period_label=period_label,
                    defaults={
                        'subject_name': subject_name,
                        'teacher_name': (row.get('teacher_name') or '').strip(),
                        'start_time': ((row.get('start_time') or '').strip() or None),
                        'end_time': ((row.get('end_time') or '').strip() or None),
                        'room_number': (row.get('room_number') or '').strip(),
                        'source': 'upload',
                    },
                )
                count += 1

            messages.success(request, f'{count} time table rows uploaded successfully.')
            return redirect('/academic/time-table-upload/')
        except Exception as exc:
            messages.error(request, f'Upload failed: {exc}')
            return redirect('/academic/time-table-upload/')

    latest_entries = TimeTableEntry.objects.order_by('-id')[:50]
    return render(request, 'students/academic_time_table_upload.html', {
        'latest_entries': latest_entries,
    })


@login_required
def academic_homework_setup(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        class_name = request.POST.get('class_name', '').strip()
        section = request.POST.get('section', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        assigned_date = request.POST.get('assigned_date', '').strip()
        due_date = request.POST.get('due_date', '').strip()
        attachment = request.FILES.get('attachment')

        if not all([class_name, section, subject_name, title, description, assigned_date, due_date]):
            messages.error(request, 'Please fill all required homework fields.')
        else:
            HomeworkSetup.objects.create(
                class_name=class_name,
                section=section,
                subject_name=subject_name,
                title=title,
                description=description,
                assigned_date=assigned_date,
                due_date=due_date,
                attachment=attachment,
                created_by=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, 'Homework saved successfully.')
            return redirect('/academic/homework-setup/')

    class_names = list(
        Student.objects.exclude(student_class__isnull=True)
        .exclude(student_class__exact='')
        .order_by('student_class')
        .values_list('student_class', flat=True)
        .distinct()
    )
    homework_rows = HomeworkSetup.objects.select_related('created_by').order_by('-id')[:200]

    return render(request, 'students/academic_homework_setup.html', {
        'class_names': class_names,
        'homework_rows': homework_rows,
    })


def academic_course_schedule(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'delete':
            record_id = request.POST.get('record_id')
            CourseSchedule.objects.filter(pk=record_id).delete()
            messages.success(request, 'Schedule deleted.')
            return redirect('/academic/course-schedule/')

        class_name = request.POST.get('class_name', '').strip()
        section = request.POST.get('section', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        teacher_name = request.POST.get('teacher_name', '').strip()
        term = request.POST.get('term', 'full_year')
        periods_per_week = request.POST.get('periods_per_week', 1)
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        description = request.POST.get('description', '').strip()

        if not all([class_name, section, subject_name, start_date, end_date]):
            messages.error(request, 'Please fill all required fields.')
        else:
            record_id = request.POST.get('record_id')
            if record_id:
                CourseSchedule.objects.filter(pk=record_id).update(
                    class_name=class_name, section=section, subject_name=subject_name,
                    teacher_name=teacher_name, term=term, periods_per_week=periods_per_week,
                    start_date=start_date, end_date=end_date, description=description,
                )
                messages.success(request, 'Schedule updated successfully.')
            else:
                CourseSchedule.objects.create(
                    class_name=class_name, section=section, subject_name=subject_name,
                    teacher_name=teacher_name, term=term, periods_per_week=periods_per_week,
                    start_date=start_date, end_date=end_date, description=description,
                )
                messages.success(request, 'Schedule saved successfully.')
            return redirect('/academic/course-schedule/')

    class_names = list(
        Student.objects.exclude(student_class__isnull=True).exclude(student_class__exact='')
        .order_by('student_class').values_list('student_class', flat=True).distinct()
    )
    filter_class = request.GET.get('class_name', '')
    filter_section = request.GET.get('section', '')
    schedules = CourseSchedule.objects.all()
    if filter_class:
        schedules = schedules.filter(class_name=filter_class)
    if filter_section:
        schedules = schedules.filter(section=filter_section)
    edit_obj = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_obj = CourseSchedule.objects.get(pk=edit_id)
        except CourseSchedule.DoesNotExist:
            pass

    return render(request, 'students/academic_course_schedule.html', {
        'class_names': class_names,
        'schedules': schedules[:200],
        'filter_class': filter_class,
        'filter_section': filter_section,
        'edit_obj': edit_obj,
        'term_choices': CourseSchedule.TERM_CHOICES,
    })


def academic_syllabus(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'delete':
            record_id = request.POST.get('record_id')
            Syllabus.objects.filter(pk=record_id).delete()
            messages.success(request, 'Syllabus unit deleted.')
            return redirect('/academic/syllabus/')

        class_name = request.POST.get('class_name', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        unit_number = request.POST.get('unit_number', '').strip()
        unit_title = request.POST.get('unit_title', '').strip()
        topics = request.POST.get('topics', '').strip()
        teaching_hours = request.POST.get('teaching_hours', 1)
        academic_year = request.POST.get('academic_year', '2025-26').strip()

        if not all([class_name, subject_name, unit_number, unit_title, topics]):
            messages.error(request, 'Please fill all required fields.')
        else:
            record_id = request.POST.get('record_id')
            if record_id:
                Syllabus.objects.filter(pk=record_id).update(
                    class_name=class_name, subject_name=subject_name, unit_number=unit_number,
                    unit_title=unit_title, topics=topics, teaching_hours=teaching_hours,
                    academic_year=academic_year,
                )
                messages.success(request, 'Syllabus unit updated.')
            else:
                Syllabus.objects.create(
                    class_name=class_name, subject_name=subject_name, unit_number=unit_number,
                    unit_title=unit_title, topics=topics, teaching_hours=teaching_hours,
                    academic_year=academic_year,
                )
                messages.success(request, 'Syllabus unit added successfully.')
            return redirect('/academic/syllabus/')

    class_names = list(
        Student.objects.exclude(student_class__isnull=True).exclude(student_class__exact='')
        .order_by('student_class').values_list('student_class', flat=True).distinct()
    )
    filter_class = request.GET.get('class_name', '')
    filter_subject = request.GET.get('subject_name', '')
    syllabi = Syllabus.objects.all()
    if filter_class:
        syllabi = syllabi.filter(class_name=filter_class)
    if filter_subject:
        syllabi = syllabi.filter(subject_name__icontains=filter_subject)
    edit_obj = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_obj = Syllabus.objects.get(pk=edit_id)
        except Syllabus.DoesNotExist:
            pass

    return render(request, 'students/academic_syllabus.html', {
        'class_names': class_names,
        'syllabi': syllabi[:300],
        'filter_class': filter_class,
        'filter_subject': filter_subject,
        'edit_obj': edit_obj,
    })


def academic_datesheet_create(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'delete':
            record_id = request.POST.get('record_id')
            DateSheet.objects.filter(pk=record_id).delete()
            messages.success(request, 'Exam entry deleted.')
            return redirect('/academic/datesheet-create/')

        class_name = request.POST.get('class_name', '').strip()
        section = request.POST.get('section', '').strip()
        subject_name = request.POST.get('subject_name', '').strip()
        exam_type = request.POST.get('exam_type', 'final')
        exam_date = request.POST.get('exam_date', '').strip()
        start_time = request.POST.get('start_time', '').strip()
        end_time = request.POST.get('end_time', '').strip()
        total_marks = request.POST.get('total_marks', 100)
        venue = request.POST.get('venue', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not all([class_name, subject_name, exam_type, exam_date, start_time, end_time]):
            messages.error(request, 'Please fill all required fields.')
        else:
            record_id = request.POST.get('record_id')
            if record_id:
                DateSheet.objects.filter(pk=record_id).update(
                    class_name=class_name, section=section, subject_name=subject_name,
                    exam_type=exam_type, exam_date=exam_date, start_time=start_time,
                    end_time=end_time, total_marks=total_marks, venue=venue, notes=notes,
                )
                messages.success(request, 'Exam entry updated.')
            else:
                DateSheet.objects.create(
                    class_name=class_name, section=section, subject_name=subject_name,
                    exam_type=exam_type, exam_date=exam_date, start_time=start_time,
                    end_time=end_time, total_marks=total_marks, venue=venue, notes=notes,
                )
                messages.success(request, 'Exam added to date sheet successfully.')
            return redirect('/academic/datesheet-create/')

    class_names = list(
        Student.objects.exclude(student_class__isnull=True).exclude(student_class__exact='')
        .order_by('student_class').values_list('student_class', flat=True).distinct()
    )
    filter_class = request.GET.get('class_name', '')
    filter_exam_type = request.GET.get('exam_type', '')
    datesheets = DateSheet.objects.all()
    if filter_class:
        datesheets = datesheets.filter(class_name=filter_class)
    if filter_exam_type:
        datesheets = datesheets.filter(exam_type=filter_exam_type)
    edit_obj = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_obj = DateSheet.objects.get(pk=edit_id)
        except DateSheet.DoesNotExist:
            pass

    return render(request, 'students/academic_datesheet_create.html', {
        'class_names': class_names,
        'datesheets': datesheets[:300],
        'filter_class': filter_class,
        'filter_exam_type': filter_exam_type,
        'edit_obj': edit_obj,
        'exam_type_choices': DateSheet.EXAM_TYPE_CHOICES,
    })


def academic_holiday_list(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'delete':
            record_id = request.POST.get('record_id')
            HolidayList.objects.filter(pk=record_id).delete()
            messages.success(request, 'Holiday deleted.')
            return redirect('/academic/holiday-list/')

        holiday_name = request.POST.get('holiday_name', '').strip()
        holiday_date = request.POST.get('holiday_date', '').strip()
        holiday_type = request.POST.get('holiday_type', 'school')
        description = request.POST.get('description', '').strip()
        academic_year = request.POST.get('academic_year', '2025-26').strip()

        if not all([holiday_name, holiday_date]):
            messages.error(request, 'Holiday name and date are required.')
        else:
            record_id = request.POST.get('record_id')
            if record_id:
                HolidayList.objects.filter(pk=record_id).update(
                    holiday_name=holiday_name, holiday_date=holiday_date,
                    holiday_type=holiday_type, description=description,
                    academic_year=academic_year,
                )
                messages.success(request, 'Holiday updated.')
            else:
                if HolidayList.objects.filter(holiday_date=holiday_date).exists():
                    messages.error(request, 'A holiday is already added for this date.')
                else:
                    HolidayList.objects.create(
                        holiday_name=holiday_name, holiday_date=holiday_date,
                        holiday_type=holiday_type, description=description,
                        academic_year=academic_year,
                    )
                    messages.success(request, 'Holiday added successfully.')
            return redirect('/academic/holiday-list/')

    filter_year = request.GET.get('academic_year', '')
    filter_type = request.GET.get('holiday_type', '')
    holidays = HolidayList.objects.all()
    if filter_year:
        holidays = holidays.filter(academic_year=filter_year)
    if filter_type:
        holidays = holidays.filter(holiday_type=filter_type)
    edit_obj = None
    edit_id = request.GET.get('edit')
    if edit_id:
        try:
            edit_obj = HolidayList.objects.get(pk=edit_id)
        except HolidayList.DoesNotExist:
            pass

    from datetime import date
    total_holidays = holidays.count()
    upcoming = holidays.filter(holiday_date__gte=date.today()).count()

    return render(request, 'students/academic_holiday_list.html', {
        'holidays': holidays,
        'filter_year': filter_year,
        'filter_type': filter_type,
        'edit_obj': edit_obj,
        'holiday_type_choices': HolidayList.HOLIDAY_TYPE_CHOICES,
        'total_holidays': total_holidays,
        'upcoming': upcoming,
    })


def attendance_daily_report(request):
    selected_date = request.GET.get('date', '') or str(timezone.localdate())
    daily_records = StudentAttendance.objects.filter(attendance_date=selected_date).select_related('student')
    present_count = daily_records.filter(status=StudentAttendance.STATUS_PRESENT).count()
    absent_count = daily_records.filter(status=StudentAttendance.STATUS_ABSENT).count()

    return render(request, 'students/attendance_daily_report.html', {
        'selected_date': selected_date,
        'daily_records': daily_records,
        'present_count': present_count,
        'absent_count': absent_count,
        'total_count': daily_records.count(),
    })


@login_required
def certificate_designed(request, certificate_type):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    cert_key = (certificate_type or '').strip().lower()
    cert_config = CERTIFICATE_TYPE_CONFIG.get(cert_key)
    if cert_config is None:
        return feature_placeholder(request, section_name='Certificate', feature_name=certificate_type)

    class_names = list(
        Student.objects.exclude(student_class__isnull=True)
        .exclude(student_class__exact='')
        .order_by('student_class')
        .values_list('student_class', flat=True)
        .distinct()
    )

    return render(request, 'students/certificate_professional.html', {
        'class_names': class_names,
        'certificate_key': cert_key,
        'certificate_title': cert_config['title'],
        'certificate_headline': cert_config['headline'],
        'certificate_subtitle': cert_config['subtitle'],
    })


@login_required
def readymade_certificate(request):
    if not can_access_module(request.user, 'academic'):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    class_names = list(
        Student.objects.exclude(student_class__isnull=True)
        .exclude(student_class__exact='')
        .order_by('student_class')
        .values_list('student_class', flat=True)
        .distinct()
    )

    return render(request, 'students/readymade_certificate.html', {
        'class_names': class_names,
    })


@login_required
@require_http_methods(['GET'])
def readymade_certificate_students(request):
    if not can_access_module(request.user, 'academic'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    class_name = request.GET.get('class_name', '').strip()
    section = request.GET.get('section', '').strip()

    if not class_name:
        return JsonResponse({'success': False, 'error': 'class_name required'})

    students_qs = Student.objects.filter(student_class=class_name)
    if section:
        students_qs = students_qs.filter(section=section)
    students_qs = students_qs.order_by('name')

    sections = list(
        Student.objects.filter(student_class=class_name)
        .exclude(section__isnull=True)
        .exclude(section__exact='')
        .order_by('section')
        .values_list('section', flat=True)
        .distinct()
    )

    students_data = []
    for student in students_qs:
        students_data.append({
            'id': student.id,
            'name': student.name,
            'father_name': student.father_name or '-',
            'admission_number': student.admission_number or '-',
            'roll_no': student.roll_no if student.roll_no is not None else '-',
            'student_class': student.student_class,
            'section': student.section,
            'dob': student.dob.strftime('%d/%m/%Y') if student.dob else '-',
            'address': student.address or '-',
        })

    return JsonResponse({
        'success': True,
        'sections': sections,
        'students': students_data,
    })


def feature_placeholder(request, section_name='ERP', feature_name='Feature'):
    section_to_module = {
        'certificate': 'academic',
        'student attendance': 'attendance',
        'academic': 'academic',
        'staff management': 'staff',
        'exam management': 'exam',
        'settings': 'settings',
        'account': 'reports',
        'account management': 'reports',
        'fee management': 'fee',
        'transport management': 'transport',
    }

    module_key = section_to_module.get((section_name or '').strip().lower())
    if module_key and not can_access_module(request.user, module_key):
        messages.error(request, 'You do not have permission to access that module.')
        return redirect('/dashboard/')

    pretty_feature = (feature_name or 'Feature').replace('-', ' ').title()
    context = {
        'section_name': section_name,
        'feature_name': pretty_feature,
        'message': f'{pretty_feature} module is being finalized with a professional workflow.',
    }
    return render(request, 'students/feature_unavailable.html', context)


@login_required
def staff_module(request, feature_name='view'):
    normalized_key = (feature_name or 'view').replace('_', '-').strip().lower()
    aliases = {
        'list': 'view',
        'new': 'add',
        'staffidcard': 'idcard',
        'attendancereport': 'attendance-report',
        'teacherpermission': 'permission',
        'experiencecertificate': 'experience-certificate',
        'dailyperformance': 'daily-performance',
        'monthlyperformance': 'monthly-performance',
    }
    resolved_key = aliases.get(normalized_key, normalized_key)
    module = STAFF_MODULES.get(resolved_key)

    if module is None:
        context = {
            'section_name': 'Staff Management',
            'feature_name': (feature_name or 'staff').replace('-', ' ').title(),
            'message': 'Requested staff module is not available yet. Please use available staff panels below.',
        }
        return render(request, 'students/feature_unavailable.html', context)

    allowed_staff_roles = ['principal', 'viceprincipal', 'teacher', 'reception', 'staff']
    allowed_group_names = [ROLE_LABEL_MAP[key] for key in allowed_staff_roles]
    user_model = get_user_model()
    can_view_staff_passwords = request.user.is_superuser or request.user.groups.filter(name=ROLE_LABEL_MAP['superadmin']).exists()
    staff_profiles = StaffProfile.objects.select_related('user', 'designation').prefetch_related('user__groups').order_by('-id')
    designation_rows = Designation.objects.filter(is_active=True).order_by('name')
    editing_profile_id = request.GET.get('edit', '').strip()
    editing_profile = None

    if editing_profile_id.isdigit():
        editing_profile = staff_profiles.filter(id=int(editing_profile_id)).first()

    if request.method == 'POST' and resolved_key == 'view':
        action = request.POST.get('action', '').strip()
        profile_id = request.POST.get('profile_id', '').strip()
        profile_obj = staff_profiles.filter(id=profile_id).first() if profile_id else None

        if profile_obj is None:
            messages.error(request, 'Selected staff record was not found.')
            return redirect('/staff/view/')

        if action == 'view_credentials':
            if not can_view_staff_passwords:
                messages.error(request, 'Only Super Admin can view login passwords.')
                return redirect('/staff/view/')

            if profile_obj.user is None:
                messages.error(request, f'No login account linked for {profile_obj.full_name}.')
            else:
                password_text = profile_obj.login_password_plain or 'Not available. Use reset password to generate a new one.'
                messages.info(
                    request,
                    f'Login ID: {profile_obj.user.username} | Password: {password_text}'
                )
            return redirect('/staff/view/')

        if action == 'reset_password':
            if not can_view_staff_passwords:
                messages.error(request, 'Only Super Admin can reset and view login passwords.')
                return redirect('/staff/view/')

            if profile_obj.user is None:
                messages.error(request, f'No login account linked for {profile_obj.full_name}.')
            else:
                new_password = request.POST.get('new_password', '').strip() or 'ChangeMe@123'
                if len(new_password) < 8:
                    messages.error(request, 'New password must be at least 8 characters long.')
                else:
                    profile_obj.user.set_password(new_password)
                    profile_obj.user.save(update_fields=['password'])
                    profile_obj.login_password_plain = new_password
                    profile_obj.save(update_fields=['login_password_plain', 'updated_at'])
                    messages.success(request, f'Password reset for {profile_obj.full_name}.')
            return redirect('/staff/view/')

        if action == 'delete_staff':
            if profile_obj.user and profile_obj.user.id == request.user.id:
                messages.error(request, 'You cannot delete your own active account.')
                return redirect('/staff/view/')

            linked_user = profile_obj.user
            if profile_obj.photo:
                profile_obj.photo.delete(save=False)
            profile_obj.delete()

            if linked_user:
                linked_user.delete()

            messages.success(request, 'Staff record deleted successfully.')
            return redirect('/staff/view/')

        if action == 'update_staff':
            full_name = request.POST.get('full_name', '').strip()
            father_name = request.POST.get('father_name', '').strip()
            mother_name = request.POST.get('mother_name', '').strip()
            husband_name = request.POST.get('husband_name', '').strip()
            qualification = request.POST.get('qualification', '').strip()
            gender = request.POST.get('gender', '').strip().lower()
            mobile_number = request.POST.get('mobile_number', '').strip()
            email = request.POST.get('email', '').strip()
            pan_number = request.POST.get('pan_number', '').strip().upper()
            experience = request.POST.get('experience', '').strip()
            last_school_name = request.POST.get('last_school_name', '').strip()
            role_key = request.POST.get('role', 'staff').strip().lower()
            username = request.POST.get('username', '').strip()
            new_password = request.POST.get('new_password', '').strip()
            designation_id = request.POST.get('designation_id', '').strip()
            uploaded_photo = request.FILES.get('photo')

            try:
                basic_salary = Decimal(request.POST.get('basic_salary', '').strip() or '0')
            except (InvalidOperation, TypeError):
                basic_salary = Decimal('-1')

            designation_obj = Designation.objects.filter(id=designation_id, is_active=True).first() if designation_id else None

            if not full_name or not mobile_number:
                messages.error(request, 'Name and mobile number are required.')
                return redirect(f'/staff/view/?edit={profile_obj.id}')
            if gender and gender not in {'male', 'female', 'other'}:
                messages.error(request, 'Please select a valid gender.')
                return redirect(f'/staff/view/?edit={profile_obj.id}')
            if basic_salary < 0:
                messages.error(request, 'Basic salary must be a valid non-negative number.')
                return redirect(f'/staff/view/?edit={profile_obj.id}')
            if role_key not in allowed_staff_roles:
                messages.error(request, 'Selected staff role is invalid.')
                return redirect(f'/staff/view/?edit={profile_obj.id}')

            profile_obj.full_name = full_name
            profile_obj.father_name = father_name
            profile_obj.mother_name = mother_name
            profile_obj.husband_name = husband_name
            profile_obj.qualification = qualification
            profile_obj.gender = gender
            profile_obj.mobile_number = mobile_number
            profile_obj.email = email
            profile_obj.pan_number = pan_number
            profile_obj.experience = experience
            profile_obj.last_school_name = last_school_name
            profile_obj.basic_salary = basic_salary
            profile_obj.designation = designation_obj

            if request.POST.get('remove_photo') == 'on' and profile_obj.photo:
                profile_obj.photo.delete(save=False)
                profile_obj.photo = None
            if uploaded_photo:
                profile_obj.photo = uploaded_photo

            if profile_obj.user:
                if username:
                    duplicate_user = user_model.objects.filter(username=username).exclude(id=profile_obj.user.id).exists()
                    if duplicate_user:
                        messages.error(request, 'A user with this username already exists.')
                        return redirect(f'/staff/view/?edit={profile_obj.id}')
                    profile_obj.user.username = username
                profile_obj.user.email = email
                if new_password:
                    if len(new_password) < 8:
                        messages.error(request, 'New password must be at least 8 characters long.')
                        return redirect(f'/staff/view/?edit={profile_obj.id}')
                    profile_obj.user.set_password(new_password)
                    profile_obj.login_password_plain = new_password

                profile_obj.user.is_staff = True
                profile_obj.user.save()

                group_name = ROLE_LABEL_MAP[role_key]
                group_obj, _ = Group.objects.get_or_create(name=group_name)
                profile_obj.user.groups.clear()
                profile_obj.user.groups.add(group_obj)

            profile_obj.save()
            messages.success(request, f'{profile_obj.full_name} updated successfully.')
            return redirect('/staff/view/')

    if request.method == 'POST' and resolved_key == 'add' and request.POST.get('action') == 'create_staff_user':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        role_key = request.POST.get('role', 'teacher').strip().lower()
        full_name = request.POST.get('full_name', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        mother_name = request.POST.get('mother_name', '').strip()
        husband_name = request.POST.get('husband_name', '').strip()
        qualification = request.POST.get('qualification', '').strip()
        gender = request.POST.get('gender', '').strip().lower()
        mobile_number = request.POST.get('mobile_number', '').strip()
        pan_number = request.POST.get('pan_number', '').strip().upper()
        experience = request.POST.get('experience', '').strip()
        last_school_name = request.POST.get('last_school_name', '').strip()
        designation_id = request.POST.get('designation_id', '').strip()
        uploaded_photo = request.FILES.get('photo')

        generated_employee_id = StaffProfile.get_next_employee_id()

        if not username:
            username = generated_employee_id.lower()
            counter = 1
            while user_model.objects.filter(username=username).exists():
                username = f'{generated_employee_id.lower()}{counter}'
                counter += 1

        if not password:
            password = 'ChangeMe@123'

        try:
            basic_salary = Decimal(request.POST.get('basic_salary', '').strip() or '0')
        except (InvalidOperation, TypeError):
            basic_salary = Decimal('-1')

        designation_obj = Designation.objects.filter(id=designation_id, is_active=True).first() if designation_id else None

        if role_key not in allowed_staff_roles:
            messages.error(request, 'Selected staff role is invalid.')
        elif not full_name or not mobile_number:
            messages.error(request, 'Name and mobile number are required.')
        elif gender and gender not in {'male', 'female', 'other'}:
            messages.error(request, 'Please select a valid gender.')
        elif basic_salary < 0:
            messages.error(request, 'Basic salary must be a valid non-negative number.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif user_model.objects.filter(username=username).exists():
            messages.error(request, 'A user with this username already exists.')
        else:
            new_user = user_model.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True,
                is_superuser=False,
            )
            group_name = ROLE_LABEL_MAP[role_key]
            group_obj, _ = Group.objects.get_or_create(name=group_name)
            new_user.groups.clear()
            new_user.groups.add(group_obj)

            StaffProfile.objects.create(
                user=new_user,
                employee_id=generated_employee_id,
                full_name=full_name,
                father_name=father_name,
                mother_name=mother_name,
                husband_name=husband_name,
                qualification=qualification,
                gender=gender,
                mobile_number=mobile_number,
                photo=uploaded_photo,
                designation=designation_obj,
                email=email,
                login_password_plain=password,
                basic_salary=basic_salary,
                pan_number=pan_number,
                experience=experience,
                last_school_name=last_school_name,
            )

            password_note = ''
            if request.POST.get('password', '').strip() == '':
                password_note = ' Default password: ChangeMe@123.'

            messages.success(request, f'Staff created successfully. Employee ID: {generated_employee_id}, Username: {username}.{password_note}')
            return redirect('/staff/view/')

    active_count = staff_profiles.filter(Q(user__isnull=True) | Q(user__is_active=True)).count()
    teacher_count = staff_profiles.filter(user__groups__name=ROLE_LABEL_MAP['teacher']).distinct().count()
    admin_count = staff_profiles.filter(
        Q(user__is_superuser=True) |
        Q(user__groups__name__in=[ROLE_LABEL_MAP['principal'], ROLE_LABEL_MAP['viceprincipal'], ROLE_LABEL_MAP['staff']])
    ).distinct().count()
    idcard_staff_id = ''
    selected_staff_card = None
    selected_staff_cards = []
    if resolved_key == 'idcard':
        idcard_staff_id = request.GET.get('staff_id', '').strip()
        bulk_ids_raw = request.GET.getlist('staff_ids')
        bulk_ids = []
        for item in bulk_ids_raw:
            if item and item.isdigit():
                bulk_ids.append(int(item))

        if bulk_ids:
            selected_map = {
                row.id: row for row in staff_profiles.filter(id__in=bulk_ids)
            }
            selected_staff_cards = [selected_map[idx] for idx in bulk_ids if idx in selected_map][:24]

        if idcard_staff_id.isdigit():
            selected_staff_card = staff_profiles.filter(id=int(idcard_staff_id)).first()
        if selected_staff_card is None and selected_staff_cards:
            selected_staff_card = selected_staff_cards[0]
        if selected_staff_card is None:
            selected_staff_card = staff_profiles.first()
        if not selected_staff_cards and selected_staff_card:
            selected_staff_cards = [selected_staff_card]

    context = {
        'current_key': resolved_key,
        'current_module': module,
        'modules': STAFF_MODULES,
        'staff_profiles': staff_profiles,
        'staff_stats': {
            'total': staff_profiles.count(),
            'active': active_count,
            'teachers': teacher_count,
            'admins': admin_count,
        },
        'staff_role_options': [(key, ROLE_LABEL_MAP[key]) for key in allowed_staff_roles],
        'designation_rows': designation_rows,
        'next_employee_id': StaffProfile.get_next_employee_id(),
        'editing_profile': editing_profile,
        'can_view_staff_passwords': can_view_staff_passwords,
        'idcard_staff_id': idcard_staff_id,
        'selected_staff_card': selected_staff_card,
        'selected_staff_cards': selected_staff_cards,
        'idcard_issue_date': timezone.localdate(),
    }
    return render(request, 'students/staff_module.html', context)


@csrf_exempt
@require_http_methods(['POST'])
def mobile_app_login_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    username = (payload.get('username') or '').strip()
    password = (payload.get('password') or '').strip()

    if not username or not password:
        return JsonResponse({'success': False, 'message': 'Username and password are required.'}, status=400)

    user_obj = authenticate(request, username=username, password=password)
    if user_obj is None:
        return JsonResponse({'success': False, 'message': 'Invalid login credentials.'}, status=401)

    role_label = resolve_role_from_user(user_obj)
    role_key = 'superadmin' if user_obj.is_superuser else role_label.lower().replace(' ', '')
    module_access = {key: bool(value) for key, value in build_module_access(user_obj).items()}
    app_setting = MobileAppControlSetting.objects.first()

    role_home_modules = []
    if app_setting:
        if role_key in {'student', 'students'}:
            role_home_modules = _split_modules_csv(app_setting.student_home_modules)
        elif role_key in {'parent', 'parents', 'reception'}:
            role_home_modules = _split_modules_csv(app_setting.parent_home_modules)
        else:
            role_home_modules = _split_modules_csv(app_setting.staff_home_modules)

    return JsonResponse({
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user_obj.id,
            'username': user_obj.username,
            'role_label': role_label,
            'role_key': role_key,
        },
        'module_access': module_access,
        'role_home_modules': role_home_modules,
    })


@csrf_exempt
@require_http_methods(['POST'])
def mobile_app_device_register_api(request):
    app_setting = MobileAppControlSetting.objects.first()
    if app_setting is None:
        app_setting = MobileAppControlSetting.objects.create()

    supplied_key = request.headers.get('X-App-Key', '') or request.GET.get('api_key', '')
    if supplied_key != app_setting.config_api_key:
        return JsonResponse({'success': False, 'message': 'Invalid app key.'}, status=401)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)

    device_id = (payload.get('device_id') or '').strip()
    platform = (payload.get('platform') or 'android').strip().lower()
    if not device_id:
        return JsonResponse({'success': False, 'message': 'device_id is required.'}, status=400)

    user_obj = None
    user_id = payload.get('user_id')
    if user_id:
        user_obj = get_user_model().objects.filter(id=user_id).first()

    defaults = {
        'user': user_obj,
        'role_key': (payload.get('role_key') or '').strip().lower(),
        'platform': platform if platform in {'android', 'ios', 'web'} else 'android',
        'device_name': (payload.get('device_name') or '').strip(),
        'fcm_token': (payload.get('fcm_token') or '').strip(),
        'app_version': (payload.get('app_version') or '').strip(),
        'is_active': True,
    }

    device, _ = MobileAppDevice.objects.update_or_create(device_id=device_id, defaults=defaults)
    return JsonResponse({'success': True, 'message': 'Device registered successfully.', 'device_id': device.device_id})


@require_http_methods(['GET'])
def mobile_app_config_api(request):
    app_setting = MobileAppControlSetting.objects.first()
    if app_setting is None:
        app_setting = MobileAppControlSetting.objects.create()

    supplied_key = request.headers.get('X-App-Key', '') or request.GET.get('api_key', '')
    if supplied_key != app_setting.config_api_key:
        return JsonResponse({'success': False, 'message': 'Invalid app key.'}, status=401)

    current_release = MobileAppRelease.objects.filter(is_current=True).order_by('-created_at').first()

    response = {
        'success': True,
        'app': {
            'name': app_setting.app_name,
            'android_latest_version': app_setting.android_latest_version,
            'android_min_supported_version': app_setting.android_min_supported_version,
            'force_update': app_setting.force_update,
            'maintenance_mode': app_setting.maintenance_mode,
            'maintenance_message': app_setting.maintenance_message,
            'student_app_enabled': app_setting.student_app_enabled,
            'parent_app_enabled': app_setting.parent_app_enabled,
            'staff_app_enabled': app_setting.staff_app_enabled,
            'push_notifications_enabled': app_setting.push_notifications_enabled,
            'app_notice': app_setting.app_notice,
            'student_home_modules': _split_modules_csv(app_setting.student_home_modules),
            'parent_home_modules': _split_modules_csv(app_setting.parent_home_modules),
            'staff_home_modules': _split_modules_csv(app_setting.staff_home_modules),
            'updated_at': app_setting.updated_at,
        },
        'release': {
            'version_name': current_release.version_name if current_release else app_setting.current_release_version,
            'version_code': current_release.version_code if current_release else None,
            'is_mandatory': current_release.is_mandatory if current_release else app_setting.force_update,
            'notes': current_release.release_notes if current_release else '',
        },
    }
    return JsonResponse(response)


@login_required
def settings_module(request, feature_name='user'):
    normalized_key = (feature_name or 'user').replace('-', '').strip().lower()
    aliases = {
        'users': 'user',
        'permission': 'permissions',
        'schoolsetting': 'school',
        'settingschool': 'school',
        'options': 'option',
        'paymentoption': 'payment',
        'payments': 'payment',
        'whatsappapi': 'whatsapp',
        'whatsapp': 'whatsapp',
        'mobile': 'mobileapp',
        'app': 'mobileapp',
        'mobileapp': 'mobileapp',
    }
    resolved_key = aliases.get(normalized_key, normalized_key)
    module = SETTINGS_MODULES.get(resolved_key)

    if module is None:
        context = {
            'section_name': 'Settings',
            'feature_name': (feature_name or 'settings').replace('-', ' ').title(),
            'message': 'Requested settings module is not available yet. Please use available configuration panels below.',
        }
        return render(request, 'students/feature_unavailable.html', context)

    user_rows = []
    user_entries = []
    default_reset_password = 'ChangeMe@123'
    selected_role_key = request.GET.get('role', 'staff').strip().lower()
    permission_row = None
    school_setting = SchoolSetting.objects.first()
    option_setting = SystemOptionSetting.objects.first()
    payment_setting = PaymentOptionSetting.objects.first()
    whatsapp_setting = WhatsAppApiSetting.objects.first()
    mobile_app_setting = MobileAppControlSetting.objects.first()
    mobile_release_rows = MobileAppRelease.objects.order_by('-created_at')[:15]
    mobile_device_rows = MobileAppDevice.objects.select_related('user').order_by('-last_seen')[:20]

    if resolved_key == 'user':
        user_model = get_user_model()

        if request.method == 'POST':
            action = request.POST.get('action', '').strip()

            if action == 'create_user':
                username = request.POST.get('username', '').strip()
                email = request.POST.get('email', '').strip()
                password = request.POST.get('password', '').strip()
                role = request.POST.get('role', 'staff').strip().lower()

                if not username or not password:
                    messages.error(request, 'Username and password are required.')
                elif len(password) < 8:
                    messages.error(request, 'Password must be at least 8 characters long.')
                elif user_model.objects.filter(username=username).exists():
                    messages.error(request, 'A user with this username already exists.')
                elif role not in ROLE_LABEL_MAP:
                    messages.error(request, 'Selected role is invalid.')
                else:
                    is_superuser = role == 'superadmin'
                    new_user = user_model.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        is_staff=True,
                        is_superuser=is_superuser,
                    )

                    group_name = ROLE_LABEL_MAP[role]
                    group_obj, _ = Group.objects.get_or_create(name=group_name)
                    new_user.groups.clear()
                    new_user.groups.add(group_obj)

                    messages.success(request, f'User "{username}" created successfully.')
                    return redirect('/settings/user/')

            elif action in {'toggle_active', 'reset_password'}:
                user_id = request.POST.get('user_id', '').strip()
                user_obj = user_model.objects.filter(id=user_id).first()

                if user_obj is None:
                    messages.error(request, 'Selected user was not found.')
                elif user_obj.id == request.user.id and action == 'toggle_active':
                    messages.error(request, 'You cannot deactivate your own account.')
                elif action == 'toggle_active':
                    user_obj.is_active = not user_obj.is_active
                    user_obj.save(update_fields=['is_active'])
                    state = 'activated' if user_obj.is_active else 'deactivated'
                    messages.success(request, f'User "{user_obj.username}" {state} successfully.')
                    return redirect('/settings/user/')
                elif action == 'reset_password':
                    user_obj.set_password(default_reset_password)
                    user_obj.save(update_fields=['password'])
                    messages.success(
                        request,
                        f'Password for "{user_obj.username}" reset to default: {default_reset_password}'
                    )
                    return redirect('/settings/user/')

        user_rows = user_model.objects.prefetch_related('groups').order_by('-is_superuser', 'username')
        user_entries = [
            {
                'user': user_obj,
                'role_label': resolve_role_from_user(user_obj),
            }
            for user_obj in user_rows
        ]

    elif resolved_key == 'permissions':
        if selected_role_key not in ROLE_LABEL_MAP:
            selected_role_key = 'staff'

        if request.method == 'POST':
            action = request.POST.get('action', '').strip()
            if action == 'save_permissions':
                posted_role = request.POST.get('role_key', 'staff').strip().lower()
                if posted_role in ROLE_LABEL_MAP:
                    selected_role_key = posted_role
                    permission_values = {
                        field_name: request.POST.get(field_name) == 'on'
                        for field_name, _ in PERMISSION_FIELDS
                    }
                    RoleModulePermission.objects.update_or_create(
                        role_key=selected_role_key,
                        defaults=permission_values,
                    )
                    messages.success(request, f'Permissions saved for {ROLE_LABEL_MAP[selected_role_key]}.')
                    return redirect(f'/settings/permissions/?role={selected_role_key}')
                messages.error(request, 'Invalid role selected for permission update.')

        permission_row, _ = RoleModulePermission.objects.get_or_create(role_key=selected_role_key)

    elif resolved_key == 'school':
        if request.method == 'POST' and request.POST.get('action') == 'save_school_settings':
            defaults = {
                'school_name': request.POST.get('school_name', '').strip(),
                'school_code': request.POST.get('school_code', '').strip(),
                'principal_name': request.POST.get('principal_name', '').strip(),
                'contact_number': request.POST.get('contact_number', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'address': request.POST.get('address', '').strip(),
                'academic_year_label': request.POST.get('academic_year_label', '').strip(),
            }
            if not defaults['school_name']:
                messages.error(request, 'School name is required.')
            else:
                if school_setting is None:
                    school_setting = SchoolSetting.objects.create(**defaults)
                else:
                    for field_name, field_value in defaults.items():
                        setattr(school_setting, field_name, field_value)
                    school_setting.save()

                if request.POST.get('remove_logo') == 'on' and school_setting.logo:
                    school_setting.logo.delete(save=False)
                    school_setting.logo = None

                uploaded_logo = request.FILES.get('logo')
                if uploaded_logo:
                    school_setting.logo = uploaded_logo

                school_setting.save()
                messages.success(request, 'School settings updated successfully.')
                return redirect('/settings/school/')

        if school_setting is None:
            school_setting = SchoolSetting.objects.create()

    elif resolved_key == 'option':
        if request.method == 'POST' and request.POST.get('action') == 'save_option_settings':
            defaults = {
                'admission_open': request.POST.get('admission_open') == 'on',
                'fee_receipt_auto_number': request.POST.get('fee_receipt_auto_number') == 'on',
                'sms_notifications_enabled': request.POST.get('sms_notifications_enabled') == 'on',
                'email_notifications_enabled': request.POST.get('email_notifications_enabled') == 'on',
                'allow_student_portal': request.POST.get('allow_student_portal') == 'on',
                'require_transport_approval': request.POST.get('require_transport_approval') == 'on',
            }
            if option_setting is None:
                option_setting = SystemOptionSetting.objects.create(**defaults)
            else:
                for field_name, field_value in defaults.items():
                    setattr(option_setting, field_name, field_value)
                option_setting.save()
            messages.success(request, 'Option settings updated successfully.')
            return redirect('/settings/option/')

        if option_setting is None:
            option_setting = SystemOptionSetting.objects.create()

    elif resolved_key == 'payment':
        if request.method == 'POST' and request.POST.get('action') == 'save_payment_settings':
            late_fee_amount_raw = request.POST.get('late_fee_amount', '0').strip() or '0'
            try:
                late_fee_amount = float(late_fee_amount_raw)
            except ValueError:
                late_fee_amount = -1

            if late_fee_amount < 0:
                messages.error(request, 'Late fee amount must be a valid non-negative number.')
            else:
                quarterly_fee_months = _normalize_month_csv(
                    request.POST.get('quarterly_fee_months', ''),
                    default_value='apr,jul,oct,jan',
                    allow_multiple=True,
                )
                half_yearly_fee_months = _normalize_month_csv(
                    request.POST.get('half_yearly_fee_months', ''),
                    default_value='apr,oct',
                    allow_multiple=True,
                )
                yearly_fee_month = _normalize_month_csv(
                    request.POST.get('yearly_fee_month', ''),
                    default_value='apr',
                    allow_multiple=False,
                )
                once_fee_month = _normalize_month_csv(
                    request.POST.get('once_fee_month', ''),
                    default_value='apr',
                    allow_multiple=False,
                )

                defaults = {
                    'allow_cash': request.POST.get('allow_cash') == 'on',
                    'allow_cheque': request.POST.get('allow_cheque') == 'on',
                    'allow_card': request.POST.get('allow_card') == 'on',
                    'allow_online_transfer': request.POST.get('allow_online_transfer') == 'on',
                    'allow_upi': request.POST.get('allow_upi') == 'on',
                    'late_fee_enabled': request.POST.get('late_fee_enabled') == 'on',
                    'late_fee_amount': late_fee_amount,
                    'payment_terms_note': request.POST.get('payment_terms_note', '').strip(),
                    'receipt_prefix': request.POST.get('receipt_prefix', 'RCPT').strip() or 'RCPT',
                    'receipt_footer': request.POST.get('receipt_footer', '').strip() or 'Thank you for your payment',
                    'quarterly_fee_months': quarterly_fee_months,
                    'half_yearly_fee_months': half_yearly_fee_months,
                    'yearly_fee_month': yearly_fee_month,
                    'once_fee_month': once_fee_month,
                    'show_school_name_on_receipt': request.POST.get('show_school_name_on_receipt') == 'on',
                    'show_logo_on_receipt': request.POST.get('show_logo_on_receipt') == 'on',
                }
                if payment_setting is None:
                    payment_setting = PaymentOptionSetting.objects.create(**defaults)
                else:
                    for field_name, field_value in defaults.items():
                        setattr(payment_setting, field_name, field_value)
                    payment_setting.save()
                messages.success(request, 'Payment settings updated successfully.')
                return redirect('/settings/payment/')

        if payment_setting is None:
            payment_setting = PaymentOptionSetting.objects.create()

    elif resolved_key == 'whatsapp':
        if request.method == 'POST' and request.POST.get('action') == 'save_whatsapp_settings':
            defaults = {
                'provider_name': request.POST.get('provider_name', '').strip() or 'Meta WhatsApp Cloud API',
                'api_base_url': request.POST.get('api_base_url', '').strip(),
                'access_token': request.POST.get('access_token', '').strip(),
                'phone_number_id': request.POST.get('phone_number_id', '').strip(),
                'business_account_id': request.POST.get('business_account_id', '').strip(),
                'webhook_verify_token': request.POST.get('webhook_verify_token', '').strip(),
                'instance_id': request.POST.get('instance_id', '').strip(),
                'default_country_code': request.POST.get('default_country_code', '').strip() or '+91',
                'fee_receipt_template': request.POST.get('fee_receipt_template', '').strip() or 'fee_receipt_notice',
                'due_fee_template': request.POST.get('due_fee_template', '').strip() or 'due_fee_alert',
                'attendance_template': request.POST.get('attendance_template', '').strip() or 'attendance_alert',
                'enable_admission_alerts': request.POST.get('enable_admission_alerts') == 'on',
                'enable_fee_receipt_alerts': request.POST.get('enable_fee_receipt_alerts') == 'on',
                'enable_attendance_alerts': request.POST.get('enable_attendance_alerts') == 'on',
                'enable_due_fee_alerts': request.POST.get('enable_due_fee_alerts') == 'on',
                'enable_result_alerts': request.POST.get('enable_result_alerts') == 'on',
                'enable_general_broadcasts': request.POST.get('enable_general_broadcasts') == 'on',
                'is_active': request.POST.get('is_active') == 'on',
            }

            if whatsapp_setting is None:
                whatsapp_setting = WhatsAppApiSetting.objects.create(**defaults)
            else:
                for field_name, field_value in defaults.items():
                    setattr(whatsapp_setting, field_name, field_value)
                whatsapp_setting.save()

            messages.success(request, 'WhatsApp API settings updated successfully.')
            return redirect('/settings/whatsapp/')

        if whatsapp_setting is None:
            whatsapp_setting = WhatsAppApiSetting.objects.create()

    elif resolved_key == 'mobileapp':
        if request.method == 'POST':
            action = request.POST.get('action', '').strip()

            if action == 'save_mobile_app_settings':
                defaults = {
                    'app_name': request.POST.get('app_name', '').strip() or 'RLCS School App',
                    'android_latest_version': request.POST.get('android_latest_version', '').strip() or '1.0.0',
                    'android_min_supported_version': request.POST.get('android_min_supported_version', '').strip() or '1.0.0',
                    'force_update': request.POST.get('force_update') == 'on',
                    'maintenance_mode': request.POST.get('maintenance_mode') == 'on',
                    'maintenance_message': request.POST.get('maintenance_message', '').strip() or 'Server maintenance in progress. Please try again later.',
                    'student_app_enabled': request.POST.get('student_app_enabled') == 'on',
                    'parent_app_enabled': request.POST.get('parent_app_enabled') == 'on',
                    'staff_app_enabled': request.POST.get('staff_app_enabled') == 'on',
                    'push_notifications_enabled': request.POST.get('push_notifications_enabled') == 'on',
                    'app_notice': request.POST.get('app_notice', '').strip(),
                }

                if mobile_app_setting is None:
                    mobile_app_setting = MobileAppControlSetting.objects.create(**defaults)
                else:
                    for field_name, field_value in defaults.items():
                        setattr(mobile_app_setting, field_name, field_value)

                if request.POST.get('regenerate_api_key') == 'on':
                    mobile_app_setting.config_api_key = secrets.token_urlsafe(32)

                mobile_app_setting.save()
                messages.success(request, 'Mobile app control settings updated successfully.')
                return redirect('/settings/mobileapp/')

            if action == 'save_mobile_role_home':
                if mobile_app_setting is None:
                    mobile_app_setting = MobileAppControlSetting.objects.create()

                mobile_app_setting.student_home_modules = request.POST.get('student_home_modules', '').strip()
                mobile_app_setting.parent_home_modules = request.POST.get('parent_home_modules', '').strip()
                mobile_app_setting.staff_home_modules = request.POST.get('staff_home_modules', '').strip()
                mobile_app_setting.save()
                messages.success(request, 'Role-wise home modules updated successfully.')
                return redirect('/settings/mobileapp/')

            if action == 'add_mobile_release':
                version_name = request.POST.get('version_name', '').strip()
                release_notes = request.POST.get('release_notes', '').strip()
                is_mandatory = request.POST.get('is_mandatory') == 'on'
                set_current = request.POST.get('set_current') == 'on'
                try:
                    version_code = int(request.POST.get('version_code', '1').strip() or '1')
                except ValueError:
                    version_code = 0

                if not version_name or version_code <= 0:
                    messages.error(request, 'Version name and valid version code are required.')
                elif MobileAppRelease.objects.filter(version_name=version_name).exists():
                    messages.error(request, 'This release version already exists.')
                else:
                    MobileAppRelease.objects.create(
                        version_name=version_name,
                        version_code=version_code,
                        release_notes=release_notes,
                        is_mandatory=is_mandatory,
                        is_current=set_current,
                    )
                    if set_current:
                        if mobile_app_setting is None:
                            mobile_app_setting = MobileAppControlSetting.objects.create()
                        mobile_app_setting.current_release_version = version_name
                        mobile_app_setting.force_update = is_mandatory
                        mobile_app_setting.save()
                    messages.success(request, 'Mobile app release added successfully.')
                return redirect('/settings/mobileapp/')

            if action in {'set_current_release', 'rollback_release'}:
                release_id = request.POST.get('release_id', '').strip()
                release_obj = MobileAppRelease.objects.filter(id=release_id).first()
                if release_obj is None:
                    messages.error(request, 'Selected release was not found.')
                else:
                    MobileAppRelease.objects.update(is_current=False)
                    release_obj.is_current = True
                    release_obj.save(update_fields=['is_current'])
                    if mobile_app_setting is None:
                        mobile_app_setting = MobileAppControlSetting.objects.create()
                    mobile_app_setting.current_release_version = release_obj.version_name
                    mobile_app_setting.force_update = release_obj.is_mandatory
                    mobile_app_setting.save()
                    msg = 'Release rollback completed successfully.' if action == 'rollback_release' else 'Current release updated successfully.'
                    messages.success(request, msg)
                return redirect('/settings/mobileapp/')

            if action == 'toggle_device':
                device_id = request.POST.get('device_id', '').strip()
                device_obj = MobileAppDevice.objects.filter(id=device_id).first()
                if device_obj is None:
                    messages.error(request, 'Selected device record not found.')
                else:
                    device_obj.is_active = not device_obj.is_active
                    device_obj.save(update_fields=['is_active'])
                    messages.success(request, 'Device status updated successfully.')
                return redirect('/settings/mobileapp/')

        if mobile_app_setting is None:
            mobile_app_setting = MobileAppControlSetting.objects.create()

        mobile_release_rows = MobileAppRelease.objects.order_by('-created_at')[:15]
        mobile_device_rows = MobileAppDevice.objects.select_related('user').order_by('-last_seen')[:20]

    context = {
        'current_key': resolved_key,
        'current_module': module,
        'modules': SETTINGS_MODULES,
        'user_rows': user_rows,
        'user_entries': user_entries,
        'default_reset_password': default_reset_password,
        'role_options': ROLE_OPTIONS,
        'permission_fields': PERMISSION_FIELDS,
        'selected_role_key': selected_role_key,
        'permission_row': permission_row,
        'school_setting': school_setting,
        'option_setting': option_setting,
        'payment_setting': payment_setting,
        'whatsapp_setting': whatsapp_setting,
        'mobile_app_setting': mobile_app_setting,
        'mobile_release_rows': mobile_release_rows,
        'mobile_device_rows': mobile_device_rows,
    }
    return render(request, 'students/settings_module.html', context)


for _students_view_name in [
    'session_list',
    'session_add',
    'session_get_data',
    'session_edit',
    'session_delete',
    'class_list',
    'class_add',
    'class_get_data',
    'class_edit',
    'class_delete',
    'designation_list',
    'designation_add',
    'designation_get_data',
    'designation_edit',
    'designation_delete',
    'subject_list',
    'subject_add',
    'subject_get_data',
    'subject_edit',
    'subject_delete',
    'student_admission',
    'student_list',
    'student_detail',
    'student_update',
    'student_delete',
    'assign_subject_select',
    'assign_subject',
    'assign_subject_bulk',
    'promote_student_select',
    'promote_student',
    'promote_student_bulk',
]:
    globals()[_students_view_name] = require_module_access('students')(globals()[_students_view_name])

for _attendance_view_name in [
    'attendance_mark',
    'attendance_report',
    'attendance_daily_report',
]:
    globals()[_attendance_view_name] = require_module_access('attendance')(globals()[_attendance_view_name])

globals()['academic_notice'] = require_module_access('academic')(globals()['academic_notice'])
globals()['settings_module'] = require_module_access('settings')(globals()['settings_module'])
globals()['staff_module'] = require_module_access('staff')(globals()['staff_module'])
