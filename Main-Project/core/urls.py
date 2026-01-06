from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # Bill Management
    path('bill/create/', views.bill_create, name='bill_create'),
    path('my-bills/', views.my_bills, name='my_bills'),
    path('update-bill-status/<int:bill_id>/', views.update_bill_status, name='update_bill_status'),
    path('bill/view/<int:bill_id>/', views.view_bill_pdf, name='view_bill_pdf'),
    path('bill/delete/<int:bill_id>/', views.delete_bill, name='delete_bill'),
    path('bill/download/<int:bill_id>/', views.download_bill_pdf, name='download_bill'),
    # path('bill/view/<int:bill_id>/', views.view_bill_pdf, name='view_bill'),
    
    # Admin Features
    path('dashboard/', views.dashboard, name='dashboard'),
    path('all-bills/', views.all_bills, name='all_bills'),
    path('bill/update-status/<int:bill_id>/', views.update_bill_status, name='update_bill_status'),
    path('user-management/', views.user_management, name='user_management'),
    
    # API Endpoints
    path('get-benefit-choices/', views.get_benefit_choices, name='get_benefit_choices'),
    path('get-amount/', views.get_amount, name='get_amount'),
]

# Error handlers
handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
