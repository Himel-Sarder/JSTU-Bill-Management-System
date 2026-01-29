from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Basic URLs
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),

    # Bill Management (User)
    path('bill/create/', views.bill_create, name='bill_create'),
    path('my-bills/', views.my_bills, name='my_bills'),
    path('bill/delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('bill/download/<int:bill_id>/', views.download_bill_pdf, name='download_bill'),
    path('bill/view/<int:bill_id>/', views.view_bill_pdf, name='view_bill_pdf'),

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
]

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)