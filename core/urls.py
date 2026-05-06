from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Basic URLs
    path('', views.home, name='home'),
    # Use custom login view instead of default
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    # Bill Management (User)
    path('bill/create/', views.bill_create, name='bill_create'),
    path('my-bills/', views.my_bills, name='my_bills'),
    path('bill/delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('bill/download/<int:bill_id>/', views.download_bill_pdf, name='download_bill'),
    path('bill/view/<int:bill_id>/', views.view_bill_pdf, name='view_bill_pdf'),
    
    # Signature Upload (General User)
    path('signature-upload/general/', views.signature_upload_general, name='signature_upload_general'),
    path('delete-signature/general/', views.delete_signature_general, name='delete_signature_general'),
    
    # Signature Upload (Chairman 1)
    path('signature-upload/chairman1/', views.signature_upload_chairman1, name='signature_upload_chairman1'),
    path('delete-signature/chairman1/', views.delete_signature_chairman1, name='delete_signature_chairman1'),
    
    # Signature Upload (Chairman 2)
    path('signature-upload/chairman2/', views.signature_upload_chairman2, name='signature_upload_chairman2'),
    path('delete-signature/chairman2/', views.delete_signature_chairman2, name='delete_signature_chairman2'),
    
    # Signature Upload (Chairman 3)
    path('signature-upload/chairman3/', views.signature_upload_chairman3, name='signature_upload_chairman3'),
    path('delete-signature/chairman3/', views.delete_signature_chairman3, name='delete_signature_chairman3'),
    
    # Signature Upload (Chairman 4)
    path('signature-upload/chairman4/', views.signature_upload_chairman4, name='signature_upload_chairman4'),
    path('delete-signature/chairman4/', views.delete_signature_chairman4, name='delete_signature_chairman4'),
    
    # Signature Upload (General Chairman - Legacy)
    path('signature-upload/', views.signature_upload, name='signature_upload'),
    path('delete-signature/', views.delete_signature, name='delete_signature'),

    # Admin Features
    path('dashboard/', views.dashboard, name='dashboard'),
    path('all-bills/', views.all_bills, name='all_bills'),
    path('bill/update-status/<int:bill_id>/', views.update_bill_status, name='update_bill_status'),
    path('user-management/', views.user_management, name='user_management'),
    path('dashboard/work-types/', views.work_type_management, name='work_type_management'),
    path('dashboard/benefits/', views.benefit_management, name='benefit_management'),

    # API Endpoints (New System)
    path('get-work-types/', views.get_work_types, name='get_work_types'),
    path('get-work-type-details/', views.get_work_type_details, name='get_work_type_details'),
    path('get-work-type-amount/', views.get_work_type_amount, name='get_work_type_amount'),
    path('get-benefit-choices/', views.get_benefit_choices, name='get_benefit_choices'),
    path('get-benefit-details/', views.get_benefit_details, name='get_benefit_details'),

    # API Endpoints (Old System - for compatibility)
    path('get-benefit-choices-old/', views.get_benefit_choices_old, name='get_benefit_choices_old'),
    path('get-amount-old/', views.get_amount_old, name='get_amount_old'),

    # Degree-based API Endpoints
    path('get-work-types-by-degree/', views.get_work_types_by_degree, name='get_work_types_by_degree'),
    path('get-benefit-choices-by-degree/', views.get_benefit_choices_by_degree, name='get_benefit_choices_by_degree'),

    # Bill Status URLs
    path('bill-status/', views.bill_status, name='bill_status'),
    path('send-bill/<int:bill_id>/', views.send_bill, name='send_bill'),
    path('send-bill-with-year/<int:bill_id>/', views.send_bill_with_year, name='send_bill_with_year'),
    
    # Signature Addition to Bill
    path('add-user-signature/<int:bill_id>/', views.add_user_signature_to_bill, name='add_user_signature_to_bill'),
    path('add-signature-to-bill/<int:bill_id>/', views.add_signature_to_bill_chairman, name='add_signature_to_bill_chairman'),
    path('bill/add-signature/<int:bill_id>/', views.add_signature_to_bill, name='add_signature_to_bill'),

    path('debug-bill/<int:bill_id>/', views.debug_bill_signature, name='debug_bill_signature'),
]

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)