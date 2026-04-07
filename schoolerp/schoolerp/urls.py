from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard import views as dashboard_views
from students import views as student_views

urlpatterns = [
    path('', dashboard_views.landing_page, name='landing_page'),
    path('login/', dashboard_views.login_view, name='login'),
    path('account/logout/', dashboard_views.logout_view, name='logout'),
    path('account/admin/', dashboard_views.account_view, name='account'),
    path('account/change-password/', dashboard_views.change_password_view, name='change_password'),
    path('admin/', admin.site.urls),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
    path('master/', include(('students.urls', 'students_master'), namespace='students_master')),
    path('student/', include(('students.urls', 'students'), namespace='students')),
    path('fee/', include('fee.urls')),
    path('fee-master/', include('fee.urls')),
    path('transport/', include('transport.urls')),

    # Real modules (implemented)
    path('academic/notice/', student_views.academic_notice, name='academic_notice'),
    path('attendance/mark/', student_views.attendance_mark, name='attendance_mark'),
    path('attendance/report/', student_views.attendance_report, name='attendance_report'),
    path('attendance/daily-report/', student_views.attendance_daily_report, name='attendance_daily_report'),
    path('certificate/appreciation/', student_views.certificate_designed, {'certificate_type': 'appreciation'}, name='certificate_appreciation'),
    path('certificate/participation/', student_views.certificate_designed, {'certificate_type': 'participation'}, name='certificate_participation'),
    path('certificate/achievement/', student_views.certificate_designed, {'certificate_type': 'achievement'}, name='certificate_achievement'),
    path('certificate/readymade/', student_views.readymade_certificate, name='readymade_certificate'),
    path('certificate/api/students/', student_views.readymade_certificate_students, name='readymade_certificate_students'),

    # Remaining sidebar modules (professional placeholder pages)
    path('certificate/<slug:feature_name>/', student_views.feature_placeholder, {'section_name': 'Certificate'}, name='certificate_placeholder'),
    path('attendance/<slug:feature_name>/', student_views.feature_placeholder, {'section_name': 'Student Attendance'}, name='attendance_placeholder'),
    path('academic/time-table-upload/', student_views.academic_time_table_upload, name='academic_time_table_upload'),
    path('academic/time-table-create/', student_views.academic_time_table_create, name='academic_time_table_create'),
    path('academic/course-schedule/', student_views.academic_course_schedule, name='academic_course_schedule'),
    path('academic/syllabus/', student_views.academic_syllabus, name='academic_syllabus'),
    path('academic/datesheet-create/', student_views.academic_datesheet_create, name='academic_datesheet_create'),
    path('academic/holiday-list/', student_views.academic_holiday_list, name='academic_holiday_list'),
    path('academic/homework-setup/', student_views.academic_homework_setup, name='academic_homework_setup'),
    path('academic/<slug:feature_name>/', student_views.feature_placeholder, {'section_name': 'Academic'}, name='academic_placeholder'),
    path('staff/', student_views.staff_module, {'feature_name': 'view'}, name='staff_home'),
    path('staff/<slug:feature_name>/', student_views.staff_module, name='staff_module'),
    path('exam/<slug:feature_name>/', student_views.feature_placeholder, {'section_name': 'Exam Management'}, name='exam_placeholder'),
    path('settings/', student_views.settings_module, {'feature_name': 'user'}, name='settings_home'),
    path('settings/<slug:feature_name>/', student_views.settings_module, name='settings_module'),
    path('api/mobile/config/', student_views.mobile_app_config_api, name='mobile_app_config_api'),
    path('api/mobile/login/', student_views.mobile_app_login_api, name='mobile_app_login_api'),
    path('api/mobile/device/register/', student_views.mobile_app_device_register_api, name='mobile_app_device_register_api'),
    path('account/<slug:feature_name>/', student_views.feature_placeholder, {'section_name': 'Account'}, name='account_placeholder'),

    # Additional fee module placeholders not yet implemented
    path('fee/report/', student_views.feature_placeholder, {'section_name': 'Fee Management', 'feature_name': 'fee-report'}, name='fee_report_placeholder'),
    path('fee/due-report/', student_views.feature_placeholder, {'section_name': 'Fee Management', 'feature_name': 'fee-due-report'}, name='fee_due_report_placeholder'),
    path('fee/demand-bill/', student_views.feature_placeholder, {'section_name': 'Fee Management', 'feature_name': 'fee-demand-bill'}, name='fee_demand_bill_placeholder'),

    # Additional account management placeholders from sidebar
    path('account/expense/', student_views.feature_placeholder, {'section_name': 'Account Management', 'feature_name': 'expense'}, name='expense_placeholder'),
    path('account/expense-receipt/', student_views.feature_placeholder, {'section_name': 'Account Management', 'feature_name': 'expense-receipt-print'}, name='expense_receipt_placeholder'),
    path('account/income/', student_views.feature_placeholder, {'section_name': 'Account Management', 'feature_name': 'income'}, name='income_placeholder'),
    path('account/income-expense/', student_views.feature_placeholder, {'section_name': 'Account Management', 'feature_name': 'expense-income'}, name='income_expense_placeholder'),
    
    # Settings Routes (Placeholder)
    path('setting/', student_views.feature_placeholder, {'section_name': 'Settings', 'feature_name': 'setting'}, name='setting'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)