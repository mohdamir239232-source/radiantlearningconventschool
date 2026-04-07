from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('session/', views.session_list, name='session_list'),
    path('session/add/', views.session_add, name='session_add'),
    path('session/<int:session_id>/data/', views.session_get_data, name='session_get_data'),
    path('session/<int:session_id>/edit/', views.session_edit, name='session_edit'),
    path('session/<int:session_id>/delete/', views.session_delete, name='session_delete'),

    path('class/', views.class_list, name='class_list'),
    path('class/add/', views.class_add, name='class_add'),
    path('class/<int:class_id>/data/', views.class_get_data, name='class_get_data'),
    path('class/<int:class_id>/edit/', views.class_edit, name='class_edit'),
    path('class/<int:class_id>/delete/', views.class_delete, name='class_delete'),

    path('designation/', views.designation_list, name='designation_list'),
    path('designation/add/', views.designation_add, name='designation_add'),
    path('designation/<int:designation_id>/data/', views.designation_get_data, name='designation_get_data'),
    path('designation/<int:designation_id>/edit/', views.designation_edit, name='designation_edit'),
    path('designation/<int:designation_id>/delete/', views.designation_delete, name='designation_delete'),

    path('subject/', views.subject_list, name='subject_list'),
    path('subject/add/', views.subject_add, name='subject_add'),
    path('subject/<int:subject_id>/data/', views.subject_get_data, name='subject_get_data'),
    path('subject/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('subject/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),

    path('', views.student_list, name='student_list'),
    path('admission/', views.student_admission, name='student_admission'),
    path('list/', views.student_list, name='student_list_page'),
    path('assign-subject/', views.assign_subject_select, name='assign_subject_select'),
    path('assign-subject/bulk/', views.assign_subject_bulk, name='assign_subject_bulk'),
    path('promote/', views.promote_student_select, name='promote_student_select'),
    path('promote/bulk/', views.promote_student_bulk, name='promote_student_bulk'),
    path('<int:student_id>/', views.student_detail, name='student_detail'),
    path('<int:student_id>/update/', views.student_update, name='student_update'),
    path('<int:student_id>/delete/', views.student_delete, name='student_delete'),
    path('<int:student_id>/assign-subject/', views.assign_subject, name='assign_subject'),
    path('<int:student_id>/promote/', views.promote_student, name='promote_student'),
]
