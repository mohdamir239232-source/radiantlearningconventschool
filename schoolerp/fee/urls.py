from django.urls import path
from fee import views

urlpatterns = [
    # Fee Particular URLs
    path('particular/', views.fee_particular_list, name='fee_particular_list'),
    path('particular/add/', views.fee_particular_add, name='fee_particular_add'),
    path('particular/<int:particular_id>/data/', views.fee_particular_get_data, name='fee_particular_get_data'),
    path('particular/<int:particular_id>/edit/', views.fee_particular_edit, name='fee_particular_edit'),
    path('particular/<int:particular_id>/delete/', views.fee_particular_delete, name='fee_particular_delete'),
    
    # Fee Amount Slab URLs
    path('amount-slab/', views.fee_amount_slab_list, name='fee_amount_slab_list'),
    path('amount-slab/add/', views.fee_amount_slab_add, name='fee_amount_slab_add'),
    path('amount-slab/<int:slab_id>/data/', views.fee_amount_slab_get_data, name='fee_amount_slab_get_data'),
    path('amount-slab/<int:slab_id>/edit/', views.fee_amount_slab_edit, name='fee_amount_slab_edit'),
    path('amount-slab/<int:slab_id>/delete/', views.fee_amount_slab_delete, name='fee_amount_slab_delete'),
    
    # Fee Discount URLs
    path('discount/', views.fee_discount_list, name='fee_discount_list'),
    path('discount/apply/', views.apply_fee_discount, name='apply_fee_discount'),
    path('discount/save/', views.save_fee_discount, name='save_fee_discount'),
    path('discount/add/', views.fee_discount_add, name='fee_discount_add'),
    path('discount/<int:discount_id>/data/', views.fee_discount_get_data, name='fee_discount_get_data'),
    path('discount/<int:discount_id>/edit/', views.fee_discount_edit, name='fee_discount_edit'),
    path('discount/<int:discount_id>/delete/', views.fee_discount_delete, name='fee_discount_delete'),
    
    # API Endpoints
    path('api/particulars-by-class/', views.get_particulars_by_class, name='get_particulars_by_class'),
    path('api/search-students/', views.search_students, name='search_students'),
    path('api/students-by-class/', views.api_students_by_class, name='api_students_by_class'),
    path('api/student-fee-months/', views.api_student_fee_months, name='api_student_fee_months'),
    path('api/student-particulars/', views.get_student_particulars, name='get_student_particulars'),
    path('api/calculate-student-fees/', views.calculate_student_fees, name='calculate_student_fees'),
    path('api/search-receipts/', views.search_fee_receipts, name='search_fee_receipts'),
    
    # Other URLs
    path('deposit/', views.fee_deposit, name='fee_deposit'),
    path('deposit-final/', views.fee_deposit_final, name='fee_deposit_final'),
    path('deposit/save/', views.save_fee_deposit, name='save_fee_deposit'),
    path('receipt/', views.fee_receipt, name='fee_receipt'),
    path('receipt/pdf/<int:fee_id>/', views.fee_receipt_pdf, name='fee_receipt_pdf'),
    path('receipt/delete/<int:fee_id>/', views.delete_fee_receipt, name='delete_fee_receipt'),
]
