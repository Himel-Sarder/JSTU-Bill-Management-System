from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count, Case, When, IntegerField
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import reverse
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime
from .models import SliderImage, Bill, Task, Profile, ActivityLog, SystemSetting, WorkType, Benefit
from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomPasswordChangeForm, BillForm, BillStatusForm
from .utils import (
    generate_bill_pdf, generate_bill_pdf_download, generate_bill_pdf_view, generate_bill_pdf_chairman,
    render_bills_report_pdf, convert_to_bangla_digits, format_bangla_number,
)


# --------------------------
# Helper Functions
# --------------------------

def is_admin(user):
    """Check if user has admin privileges"""
    return user.is_authenticated and user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']


def log_activity(user, action, details='', ip_address=None):
    """Log user activities"""
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address
    )


# --------------------------
# Public Views
# --------------------------

def home(request):
    from django.conf import settings
 
    slider_images = SliderImage.objects.filter(is_active=True).order_by('order')
    total_bills   = Bill.objects.count()
    total_users   = User.objects.count()
    total_amount  = Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0
 
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        user_type = request.user.profile.user_type
 
        if user_type == 'কন্ট্রোলার':
            bills_list = (
                Bill.objects
                .exclude(status='draft')
                .select_related('user', 'user__profile')
                .order_by('-created_at')
            )

            status_filter = request.GET.get('status', '')
            if status_filter:
                bills_list = bills_list.filter(status=status_filter)

            # CORRECTED COUNTS - using controller-specific statuses
            pending_count = Bill.objects.exclude(status='draft').filter(status='pending').count()
            approved_count = Bill.objects.exclude(status='draft').filter(status='approved_by_controller').count()  # Controller approved
            rejected_count = Bill.objects.exclude(status='draft').filter(status='rejected_by_controller').count()  # Controller rejected
            paid_count = Bill.objects.exclude(status='draft').filter(status='paid').count()
            sent_to_controller_count = Bill.objects.exclude(status='draft').filter(status='sent_to_controller').count()
            
            con_total = Bill.objects.exclude(status='draft').count()
            con_amount = Bill.objects.exclude(status='draft').aggregate(
                total=Sum('total_amount')
            )['total'] or 0

            paginator = Paginator(bills_list, 10)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            context = {
                'bills': page_obj,
                'pending_count': pending_count,
                'approved_count': approved_count,  # Now shows controller approved count
                'rejected_count': rejected_count,  # Now shows controller rejected count
                'paid_count': paid_count,
                'total_bills': con_total,
                'total_amount': con_amount,
                'current_filter': status_filter,
                'sent_to_controller_count': sent_to_controller_count,
                'MEDIA_URL': settings.MEDIA_URL,
            }
            return render(request, 'core/home_con.html', context)
 
        # ── Chairman ────────────────────────────────────────────────
        elif user_type == 'চেয়ারম্যান':
            context = {
                'slider_images': slider_images,
                'total_bills':   total_bills,
                'total_users':   total_users,
                'total_amount':  total_amount,
                'MEDIA_URL':     settings.MEDIA_URL,
                'pending_count':  Bill.objects.filter(status='pending').count(),
                'approved_count': Bill.objects.filter(status='approved').count(),
                'rejected_count': Bill.objects.filter(status='rejected').count(),
                'paid_count':     Bill.objects.filter(status='paid').count(),
                'controller_returned_count': Bill.objects.filter(status='controller_returned').count(),
            }
 
            if request.user.username == 'JSTUChairman1':
                context['total_bills_1st_year'] = Bill.objects.filter(
                    Q(semester__icontains='১ম') | Q(semester__icontains='১ম সেমিস্টার') |
                    Q(semester__icontains='২য়') | Q(semester__icontains='২য় সেমিস্টার') |
                    Q(semester__icontains='1st') | Q(semester__icontains='2nd')
                ).count()
                context['pending_bills_1st_year'] = Bill.objects.filter(
                    (Q(semester__icontains='১ম') | Q(semester__icontains='১ম সেমিস্টার') |
                     Q(semester__icontains='২য়') | Q(semester__icontains='২য় সেমিস্টার') |
                     Q(semester__icontains='1st') | Q(semester__icontains='2nd')),
                    status='pending'
                ).count()
                context['approved_bills_1st_year'] = Bill.objects.filter(
                    (Q(semester__icontains='১ম') | Q(semester__icontains='১ম সেমিস্টার') |
                     Q(semester__icontains='২য়') | Q(semester__icontains='২য় সেমিস্টার') |
                     Q(semester__icontains='1st') | Q(semester__icontains='2nd')),
                    status='approved'
                ).count()
                context['rejected_bills_1st_year'] = Bill.objects.filter(
                    (Q(semester__icontains='১ম') | Q(semester__icontains='১ম সেমিস্টার') |
                     Q(semester__icontains='২য়') | Q(semester__icontains='২য় সেমিস্টার') |
                     Q(semester__icontains='1st') | Q(semester__icontains='2nd')),
                    status='rejected'
                ).count()
                context['paid_bills_1st_year'] = Bill.objects.filter(
                    (Q(semester__icontains='১ম') | Q(semester__icontains='১ম সেমিস্টার') |
                     Q(semester__icontains='২য়') | Q(semester__icontains='২য় সেমিস্টার') |
                     Q(semester__icontains='1st') | Q(semester__icontains='2nd')),
                    status='paid'
                ).count()
 
            elif request.user.username == 'JSTUChairman2':
                context['total_bills_2nd_year'] = Bill.objects.filter(
                    Q(semester__icontains='৩য়') | Q(semester__icontains='৩য় সেমিস্টার') |
                    Q(semester__icontains='৪র্থ') | Q(semester__icontains='৪র্থ সেমিস্টার') |
                    Q(semester__icontains='3rd') | Q(semester__icontains='4th')
                ).count()
                context['pending_bills_2nd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৩য়') | Q(semester__icontains='৩য় সেমিস্টার') |
                     Q(semester__icontains='৪র্থ') | Q(semester__icontains='৪র্থ সেমিস্টার') |
                     Q(semester__icontains='3rd') | Q(semester__icontains='4th')),
                    status='pending'
                ).count()
                context['approved_bills_2nd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৩য়') | Q(semester__icontains='৩য় সেমিস্টার') |
                     Q(semester__icontains='৪র্থ') | Q(semester__icontains='৪র্থ সেমিস্টার') |
                     Q(semester__icontains='3rd') | Q(semester__icontains='4th')),
                    status='approved'
                ).count()
                context['rejected_bills_2nd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৩য়') | Q(semester__icontains='৩য় সেমিস্টার') |
                     Q(semester__icontains='৪র্থ') | Q(semester__icontains='৪র্থ সেমিস্টার') |
                     Q(semester__icontains='3rd') | Q(semester__icontains='4th')),
                    status='rejected'
                ).count()
                context['paid_bills_2nd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৩য়') | Q(semester__icontains='৩য় সেমিস্টার') |
                     Q(semester__icontains='৪র্থ') | Q(semester__icontains='৪র্থ সেমিস্টার') |
                     Q(semester__icontains='3rd') | Q(semester__icontains='4th')),
                    status='paid'
                ).count()
 
            elif request.user.username == 'JSTUChairman3':
                context['total_bills_3rd_year'] = Bill.objects.filter(
                    Q(semester__icontains='৫ম') | Q(semester__icontains='৫ম সেমিস্টার') |
                    Q(semester__icontains='৬ষ্ঠ') | Q(semester__icontains='৬ষ্ঠ সেমিস্টার') |
                    Q(semester__icontains='5th') | Q(semester__icontains='6th')
                ).count()
                context['pending_bills_3rd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৫ম') | Q(semester__icontains='৫ম সেমিস্টার') |
                     Q(semester__icontains='৬ষ্ঠ') | Q(semester__icontains='৬ষ্ঠ সেমিস্টার') |
                     Q(semester__icontains='5th') | Q(semester__icontains='6th')),
                    status='pending'
                ).count()
                context['approved_bills_3rd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৫ম') | Q(semester__icontains='৫ম সেমিস্টার') |
                     Q(semester__icontains='৬ষ্ঠ') | Q(semester__icontains='৬ষ্ঠ সেমিস্টার') |
                     Q(semester__icontains='5th') | Q(semester__icontains='6th')),
                    status='approved'
                ).count()
                context['rejected_bills_3rd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৫ম') | Q(semester__icontains='৫ম সেমিস্টার') |
                     Q(semester__icontains='৬ষ্ঠ') | Q(semester__icontains='৬ষ্ঠ সেমিস্টার') |
                     Q(semester__icontains='5th') | Q(semester__icontains='6th')),
                    status='rejected'
                ).count()
                context['paid_bills_3rd_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৫ম') | Q(semester__icontains='৫ম সেমিস্টার') |
                     Q(semester__icontains='৬ষ্ঠ') | Q(semester__icontains='৬ষ্ঠ সেমিস্টার') |
                     Q(semester__icontains='5th') | Q(semester__icontains='6th')),
                    status='paid'
                ).count()
 
            elif request.user.username == 'JSTUChairman4':
                context['total_bills_4th_year'] = Bill.objects.filter(
                    Q(semester__icontains='৭ম') | Q(semester__icontains='৭ম সেমিস্টার') |
                    Q(semester__icontains='৮ম') | Q(semester__icontains='৮ম সেমিস্টার') |
                    Q(semester__icontains='7th') | Q(semester__icontains='8th') |
                    Q(semester__icontains='মাস্টার্স')
                ).count()
                context['pending_bills_4th_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৭ম') | Q(semester__icontains='৭ম সেমিস্টার') |
                     Q(semester__icontains='৮ম') | Q(semester__icontains='৮ম সেমিস্টার') |
                     Q(semester__icontains='7th') | Q(semester__icontains='8th') |
                     Q(semester__icontains='মাস্টার্স')),
                    status='pending'
                ).count()
                context['approved_bills_4th_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৭ম') | Q(semester__icontains='৭ম সেমিস্টার') |
                     Q(semester__icontains='৮ম') | Q(semester__icontains='৮ম সেমিস্টার') |
                     Q(semester__icontains='7th') | Q(semester__icontains='8th') |
                     Q(semester__icontains='মাস্টার্স')),
                    status='approved'
                ).count()
                context['rejected_bills_4th_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৭ম') | Q(semester__icontains='৭ম সেমিস্টার') |
                     Q(semester__icontains='৮ম') | Q(semester__icontains='৮ম সেমিস্টার') |
                     Q(semester__icontains='7th') | Q(semester__icontains='8th') |
                     Q(semester__icontains='মাস্টার্স')),
                    status='rejected'
                ).count()
                context['paid_bills_4th_year'] = Bill.objects.filter(
                    (Q(semester__icontains='৭ম') | Q(semester__icontains='৭ম সেমিস্টার') |
                     Q(semester__icontains='৮ম') | Q(semester__icontains='৮ম সেমিস্টার') |
                     Q(semester__icontains='7th') | Q(semester__icontains='8th') |
                     Q(semester__icontains='মাস্টার্স')),
                    status='paid'
                ).count()
 
            return render(request, 'core/home_c.html', context)
 
    # ── Everyone else (including unauthenticated) ────────────────────
    context = {
        'slider_images': slider_images,
        'total_bills':   total_bills,
        'total_users':   total_users,
        'total_amount':  total_amount,
        'MEDIA_URL':     settings.MEDIA_URL,
    }
    return render(request, 'core/home.html', context)


def register(request):
    """User registration view - only for Assistant Professor, Lecturer, Office Assistant"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            log_activity(user, 'User registered', f'New user {user.username} registered')
            messages.success(request, 'আপনার অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


# --------------------------
# Custom Login View
# --------------------------

class CustomLoginView(LoginView):
    """Custom login view with role-based authentication"""
    template_name = 'core/login.html'
    
    def form_valid(self, form):
        # Get the login type from POST data
        login_type = self.request.POST.get('login_type')
        
        # Get the authenticated user
        user = form.get_user()
        
        # Check if user has a profile
        if hasattr(user, 'profile'):
            user_type = user.profile.user_type
            
            # Validate login type based on user's actual user_type
            if login_type == 'chairman':
                if user_type != 'চেয়ারম্যান':
                    messages.error(self.request, 'আপনি চেয়ারম্যান নন। অনুগ্রহ করে সঠিক লগইন টাইপ নির্বাচন করুন।')
                    return self.form_invalid(form)
            elif login_type == 'controller':
                if user_type != 'কন্ট্রোলার':
                    messages.error(self.request, 'আপনি কন্ট্রোলার নন। অনুগ্রহ করে সঠিক লগইন টাইপ নির্বাচন করুন।')
                    return self.form_invalid(form)
            elif login_type == 'others':
                # Others can login with any non-chairman and non-controller type
                if user_type in ['চেয়ারম্যান', 'কন্ট্রোলার']:
                    messages.error(self.request, f'{user_type} "অন্যান্য" অপশন ব্যবহার করে লগইন করতে পারবেন না। দয়া করে সঠিক অপশন নির্বাচন করুন।')
                    return self.form_invalid(form)
            else:
                messages.error(self.request, 'অনুগ্রহ করে লগইন টাইপ নির্বাচন করুন।')
                return self.form_invalid(form)
        else:
            messages.error(self.request, 'প্রোফাইল তথ্য পাওয়া যায়নি।')
            return self.form_invalid(form)
        
        # Log the login activity
        log_activity(user, 'User logged in', f'User logged in with {login_type} type', 
                    ip_address=self.request.META.get('REMOTE_ADDR'))
        
        return super().form_valid(form)
    
    def get_success_url(self):
        # Redirect based on user type
        user = self.request.user
        if hasattr(user, 'profile'):
            if user.profile.user_type == 'চেয়ারম্যান':
                return reverse('home')
            elif user.profile.user_type == 'কন্ট্রোলার':
                return reverse('home')
            else:
                return reverse('bill_status')
        return reverse('home')


def custom_logout(request):
    """Custom logout view with confirmation"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'আপনি সফলভাবে লগআউট হয়েছেন!')
        return redirect('home')
    else:
        return render(request, 'core/logout_confirm.html')


# --------------------------
# User Profile Views
# --------------------------

@login_required
def profile(request):
    """User profile management view"""
    if request.method == 'POST':
        if 'profile_update' in request.POST:
            # Create form with POST data and FILES
            profile_form = ProfileUpdateForm(
                request.POST,
                request.FILES,  # Important: include FILES for image upload
                instance=request.user.profile
            )
            password_form = CustomPasswordChangeForm(request.user)

            if profile_form.is_valid():
                # Update user fields
                user = request.user
                user.first_name = profile_form.cleaned_data['first_name']
                user.email = profile_form.cleaned_data['email']
                user.save()
                
                # Save profile (this will handle the profile picture)
                profile_form.save()
                
                log_activity(request.user, 'Profile updated', 'User updated their profile')
                messages.success(request, 'আপনার প্রোফাইল সফলভাবে আপডেট করা হয়েছে!')
                return redirect('profile')
            else:
                messages.error(request, 'দয়া করে আপনার তথ্য সঠিকভাবে পূরণ করুন।')

        elif 'password_change' in request.POST:
            profile_form = ProfileUpdateForm(instance=request.user.profile)
            password_form = CustomPasswordChangeForm(request.user, request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                log_activity(request.user, 'Password changed', 'User changed their password')
                messages.success(request, 'আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন করা হয়েছে!')
                return redirect('profile')
            else:
                messages.error(request, 'দয়া করে আপনার তথ্য সঠিকভাবে পূরণ করুন।')
        else:
            profile_form = ProfileUpdateForm(instance=request.user.profile)
            password_form = CustomPasswordChangeForm(request.user)
    else:
        profile_form = ProfileUpdateForm(instance=request.user.profile)
        password_form = CustomPasswordChangeForm(request.user)

    context = {
        'profile_form': profile_form,
        'password_form': password_form
    }
    return render(request, 'core/profile.html', context)


# --------------------------
# Signature Upload Views (Legacy Chairman)
# --------------------------

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def signature_upload(request):
    """View for chairman to upload signature (legacy)"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload')
            
            request.user.profile.signature = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'Chairman uploaded signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload')
    
    return render(request, 'core/signature_upload.html')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def delete_signature(request):
    """View for chairman to delete signature (legacy)"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature:
            request.user.profile.signature.delete(save=False)
            request.user.profile.signature = None
            request.user.profile.save()
            
            log_activity(request.user, 'Signature deleted', 'Chairman deleted signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload')


# --------------------------
# Bill Management Views (Regular Users)
# --------------------------

@login_required
def bill_create(request):
    """Create a new bill"""
    if request.method == 'POST':
        form = BillForm(request.POST)
        action = request.POST.get('action', 'save')

        if form.is_valid():
            bill = form.save(commit=False)
            bill.user = request.user

            if action == 'send':
                bill.status = 'pending'
                bill.sent_at = timezone.now()
                success_message = 'বিল সফলভাবে পাঠানো হয়েছে! স্ট্যাটাস পৃষ্ঠায় দেখুন।'
                redirect_url = 'bill_status'
            else:
                bill.status = 'draft'
                bill.sent_at = None
                success_message = 'বিল সফলভাবে তৈরি হয়েছে!'
                redirect_url = 'my_bills'

            bill.save()

            tasks_data = json.loads(request.POST.get('tasks', '[]'))
            total_amount = 0

            for task_data in tasks_data:
                task = Task(
                    bill=bill,
                    work_type=task_data['work_type'],
                    benefit=task_data['benefit'],
                    quantity=task_data.get('quantity', 1),
                    unit=task_data.get('unit', ''),
                    amount=task_data['amount'],
                    remarks=task_data.get('remarks', '')  # NEW: Save remarks
                )
                task.save()
                total_amount += float(task_data['amount'])

            bill.total_amount = total_amount
            bill.save()

            log_activity(request.user, 'Bill created', f'Bill {bill.bill_number} created with {len(tasks_data)} tasks')
            messages.success(request, success_message)
            return redirect(redirect_url)
    else:
        form = BillForm()

    return render(request, 'core/bill_create.html', {'form': form})


@login_required
def my_bills(request):
    """View user's own bills (drafts and all). Bills the chairman has rolled back
    (rejected by controller, then returned by chairman) are shown separately under
    'ফেরত বিল' so the creator can fix and resend them."""
    returned_bills = Bill.objects.filter(
        user=request.user, status='returned_to_user'
    ).order_by('-returned_to_user_at')

    bills_list = Bill.objects.filter(user=request.user).exclude(
        status='returned_to_user'
    ).order_by('-created_at')

    paginator = Paginator(bills_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get tab parameter - default to 'niomitobill'
    tab = request.GET.get('tab', 'niomitobill')

    return render(request, 'core/my_bills.html', {
        'bills': page_obj,
        'returned_bills': returned_bills,
        'active_tab': tab,  # Pass to template
    })


@login_required
@require_POST
def delete_bill(request, bill_id):
    """Delete a bill with different rules based on user type"""
    bill = get_object_or_404(Bill, id=bill_id)

    is_chairman = request.user.is_authenticated and request.user.profile.user_type == 'চেয়ারম্যান'

    if is_chairman:
        # ── Chairman: permanently delete any bill, any status, no restrictions ──
        bill_number = bill.bill_number
        bill_status = bill.status
        bill.delete()

        log_activity(
            request.user,
            'Bill permanently deleted by chairman',
            f'Bill {bill_number} (status: {bill_status}) permanently deleted by chairman'
        )
        messages.success(request, f'বিল {bill_number} স্থায়ীভাবে ডিলিট করা হয়েছে!')
        return redirect('all_bills')

    else:
        # ── Regular user: must own the bill ──
        if bill.user != request.user:
            messages.error(request, 'আপনার এই বিল ডিলিট করার অনুমতি নেই।')
            return redirect('my_bills')

        # Cannot delete pending or paid bills
        if bill.status == 'pending':
            messages.error(request, 'অপেক্ষমান বিল ডিলিট করা যাবে না।')
            return redirect('bill_status')
        elif bill.status == 'paid':
            messages.error(request, 'পরিশোধিত বিল ডিলিট করা যাবে না।')
            return redirect('bill_status')

        # draft, rejected, approved — allowed
        was_draft = bill.status == 'draft'
        bill_number = bill.bill_number
        bill.delete()

        log_activity(request.user, 'Bill deleted', f'Bill {bill_number} permanently deleted')
        messages.success(request, f'বিল {bill_number} স্থায়ীভাবে ডিলিট করা হয়েছে!')

        return redirect('my_bills' if was_draft else 'bill_status')


@login_required
def download_bill_pdf(request, bill_id):
    """Download bill as PDF"""
    try:
        bill = get_object_or_404(Bill, id=bill_id)
        if bill.user != request.user and not is_admin(request.user):
            messages.error(request, 'আপনার এই বিল ডাউনলোড করার অনুমতি নেই।')
            return redirect('my_bills')

        # Use unified PDF generation
        response = generate_bill_pdf(bill, inline=False)
            
        if response.status_code == 500:
            messages.error(request, 'পিডিএফ জেনারেট করতে সমস্যা হচ্ছে।')
            return redirect('my_bills')

        log_activity(request.user, 'Bill downloaded', f'Bill {bill.bill_number} downloaded as PDF')
        return response

    except Exception as e:
        messages.error(request, f'পিডিএফ ডাউনলোড করতে সমস্যা হচ্ছে: {str(e)}')
        return redirect('my_bills')


@login_required
def view_bill_pdf(request, bill_id):
    """View bill PDF in browser"""
    try:
        bill = get_object_or_404(Bill, id=bill_id)
        if bill.user != request.user and not is_admin(request.user):
            messages.error(request, 'আপনার এই বিল দেখার অনুমতি নেই।')
            return redirect('my_bills')

        # Use unified PDF generation
        response = generate_bill_pdf(bill, inline=True)
            
        if response.status_code == 500:
            messages.error(request, 'পিডিএফ দেখাতে সমস্যা হচ্ছে।')
            return redirect('my_bills')

        log_activity(request.user, 'Bill viewed', f'Bill {bill.bill_number} viewed in browser')
        return response

    except Exception as e:
        messages.error(request, f'পিডিএফ দেখাতে সমস্যা হচ্ছে: {str(e)}')
        return redirect('my_bills')
    
    
@login_required
def bill_status(request):
    """View for displaying bill status with filtering"""
    # Get the base queryset based on user type
    if request.user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']:
        base_bills = Bill.objects.exclude(status='draft').exclude(is_hidden_from_chairman=True)
        bills_list = base_bills.order_by('-created_at')
        
        # Admin counts
        pending_count = base_bills.filter(status='pending').count()
        approved_count = base_bills.filter(status='approved').count()
        rejected_count = base_bills.filter(status='rejected').count()
        paid_count = base_bills.filter(status='paid').count()
        approved_by_controller_count = base_bills.filter(status='approved_by_controller').count()
        rejected_by_controller_count = base_bills.filter(status='rejected_by_controller').count()
        controller_returned_count = base_bills.filter(status='controller_returned').count()
        returned_to_user_count = base_bills.filter(status='returned_to_user').count()
        sent_to_controller_count = base_bills.filter(status='sent_to_controller').count()
    else:
        base_bills = Bill.objects.filter(user=request.user).exclude(status='draft')
        bills_list = base_bills.order_by('-created_at')
        
        # Regular user counts
        pending_count = base_bills.filter(status='pending').count()
        approved_count = base_bills.filter(status='approved').count()
        rejected_count = base_bills.filter(status='rejected').count()
        paid_count = base_bills.filter(status='paid').count()
        approved_by_controller_count = base_bills.filter(status='approved_by_controller').count()
        rejected_by_controller_count = base_bills.filter(status='rejected_by_controller').count()
        controller_returned_count = base_bills.filter(status='controller_returned').count()
        returned_to_user_count = base_bills.filter(status='returned_to_user').count()
        sent_to_controller_count = base_bills.filter(status='sent_to_controller').count()

    # Apply status filter if present
    status_filter = request.GET.get('status', '')
    if status_filter:
        bills_list = bills_list.filter(status=status_filter)

    # Pagination
    paginator = Paginator(bills_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'bills': page_obj,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'paid_count': paid_count,
        'approved_by_controller_count': approved_by_controller_count,
        'rejected_by_controller_count': rejected_by_controller_count,
        'controller_returned_count': controller_returned_count,
        'returned_to_user_count': returned_to_user_count,
        'sent_to_controller_count': sent_to_controller_count,
        'current_filter': status_filter,
    }
    return render(request, 'core/status.html', context)


@login_required
@require_POST
def send_bill(request, bill_id):
    """Send a bill to pending status for approval"""
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    
    if bill.status != 'draft':
        messages.error(request, 'শুধুমাত্র খসড়া বিল পাঠানো যাবে।')
        return redirect('my_bills')

    bill.status = 'pending'
    bill.sent_at = timezone.now()
    bill.save()

    log_activity(request.user, 'Bill sent', f'Bill {bill.bill_number} sent for approval')
    messages.success(request, 'বিল সফলভাবে পাঠানো হয়েছে!')
    return redirect('bill_status')


@login_required
@require_POST
def send_bill_with_year(request, bill_id):
    """Send a bill to specific chairman based on year selection"""
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    
    if bill.status != 'draft':
        messages.error(request, 'শুধুমাত্র খসড়া বিল পাঠানো যাবে।')
        return redirect('my_bills')
    
    selected_year = request.POST.get('year')
    
    if not selected_year:
        messages.error(request, 'দয়া করে বর্ষ নির্বাচন করুন।')
        return redirect('my_bills')
    
    chairman_map = {
        '1st': 'JSTUChairman1',
        '2nd': 'JSTUChairman2',
        '3rd': 'JSTUChairman3',
        '4th': 'JSTUChairman4',
    }
    
    chairman_username = chairman_map.get(selected_year)
    
    if not chairman_username:
        messages.error(request, 'অবৈধ বর্ষ নির্বাচন।')
        return redirect('my_bills')
    
    year_text = ''
    if selected_year == '1st':
        year_text = '১ম বর্ষ'
    elif selected_year == '2nd':
        year_text = '২য় বর্ষ'
    elif selected_year == '3rd':
        year_text = '৩য় বর্ষ'
    elif selected_year == '4th':
        year_text = '৪র্থ বর্ষ'
    
    bill.status = 'pending'
    bill.sent_at = timezone.now()
    bill.remarks = f"বর্ষ: {year_text} | চেয়ারম্যান: {chairman_username} | {bill.remarks or ''}"
    bill.save()
    
    log_activity(request.user, 'Bill sent', 
                f'Bill {bill.bill_number} sent to {chairman_username} ({year_text})')
    messages.success(request, f'বিল সফলভাবে {year_text} চেয়ারম্যানের কাছে পাঠানো হয়েছে!')
    
    return redirect('bill_status')


@login_required
@require_POST
def add_user_signature_to_bill(request, bill_id):
    """Add user's signature to bill - For draft and returned_to_user bills"""
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    
    # Allow signature for draft and returned_to_user bills
    if bill.status not in ['draft', 'returned_to_user']:
        messages.error(request, 'শুধুমাত্র খসড়া অথবা ফেরত বিলে স্বাক্ষর যোগ করা যাবে।')
        return redirect('my_bills')
    
    # Check if signature is already added
    if bill.user_signature_added:
        messages.warning(request, 'এই বিলে ইতিমধ্যে আপনার স্বাক্ষর যুক্ত হয়েছে।')
        return redirect('my_bills')
    
    # Check if user has uploaded signature
    if request.user.profile.signature_general:
        # Mark signature as added
        bill.user_signature_added = True
        signature_note = f"\nস্বাক্ষর যুক্ত: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}"
        bill.remarks = (bill.remarks or '') + signature_note
        bill.save()
        
        log_activity(request.user, 'Signature added to bill', 
                    f'User signature added to bill {bill.bill_number}')
        messages.success(request, f'বিল {bill.bill_number} এ আপনার স্বাক্ষর সফলভাবে যুক্ত হয়েছে!')
        return redirect('my_bills')
    else:
        messages.error(request, 'আপনার স্বাক্ষর আপলোড করা হয়নি। দয়া করে প্রথমে স্বাক্ষর আপলোড করুন।')
        return redirect('signature_upload_general')


# --------------------------
# Admin Views
# --------------------------

def _base_admin_bills_queryset(request):
    """Bills queryset scoped to the logged-in admin/chairman, before any user-chosen filters."""
    chairman_username = request.user.username

    year_map = {
        'JSTUChairman1': '১ম বর্ষ',
        'JSTUChairman2': '২য় বর্ষ',
        'JSTUChairman3': '৩য় বর্ষ',
        'JSTUChairman4': '৪র্থ বর্ষ',
    }

    year_text = year_map.get(chairman_username, '')

    if year_text:
        bills = Bill.objects.exclude(status='draft').exclude(
            is_hidden_from_chairman=True
        ).exclude(
            status='returned_to_user'  # Exclude returned_to_user bills
        ).filter(
            remarks__icontains=year_text
        ).select_related('user').order_by('-sent_at', '-created_at')
    else:
        bills = Bill.objects.exclude(status='draft').exclude(
            is_hidden_from_chairman=True
        ).exclude(
            status='returned_to_user'  # Exclude returned_to_user bills
        ).select_related('user').order_by('-sent_at', '-created_at')

    return bills


def apply_bill_filters(request, bills):
    """Apply every admin-dashboard filter (from GET params) to a Bill queryset.

    Returns (filtered_queryset, filters_dict) where filters_dict holds the
    cleaned values so templates can re-populate the filter form / build links.
    """
    status_filter = request.GET.get('status', '').strip()
    user_filter = request.GET.get('user', '').strip()
    semester_filter = request.GET.get('semester', '').strip()
    degree_filter = request.GET.get('degree_type', '').strip()
    department_filter = request.GET.get('department', '').strip()
    bank_filter = request.GET.get('bank_name', '').strip()
    bill_number_filter = request.GET.get('bill_number', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    amount_min = request.GET.get('amount_min', '').strip()
    amount_max = request.GET.get('amount_max', '').strip()

    if status_filter:
        bills = bills.filter(status=status_filter)
    if user_filter:
        bills = bills.filter(user__username__icontains=user_filter)
    if semester_filter:
        bills = bills.filter(semester=semester_filter)
    if degree_filter:
        bills = bills.filter(degree_type=degree_filter)
    if department_filter:
        bills = bills.filter(department__icontains=department_filter)
    if bank_filter:
        bills = bills.filter(bank_name=bank_filter)
    if bill_number_filter:
        bills = bills.filter(
            Q(bill_number__icontains=bill_number_filter) | Q(voucher_number__icontains=bill_number_filter)
        )

    if date_from:
        try:
            parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            bills = bills.filter(created_at__date__gte=parsed)
        except ValueError:
            date_from = ''
    if date_to:
        try:
            parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            bills = bills.filter(created_at__date__lte=parsed)
        except ValueError:
            date_to = ''

    if amount_min:
        try:
            bills = bills.filter(total_amount__gte=Decimal(amount_min))
        except InvalidOperation:
            amount_min = ''
    if amount_max:
        try:
            bills = bills.filter(total_amount__lte=Decimal(amount_max))
        except InvalidOperation:
            amount_max = ''

    filters = {
        'status_filter': status_filter,
        'user_filter': user_filter,
        'semester_filter': semester_filter,
        'degree_filter': degree_filter,
        'department_filter': department_filter,
        'bank_filter': bank_filter,
        'bill_number_filter': bill_number_filter,
        'date_from': date_from,
        'date_to': date_to,
        'amount_min': amount_min,
        'amount_max': amount_max,
    }
    return bills, filters


@login_required
@user_passes_test(is_admin)
def all_bills(request):
    # Get the base queryset for the current chairman
    base_bills = _base_admin_bills_queryset(request)
    
    # Apply filters for display
    bills, filters = apply_bill_filters(request, base_bills)

    paginator = Paginator(bills, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # For the filtered bills display
    filtered_amount = bills.aggregate(total=Sum('total_amount'))['total'] or 0

    # IMPORTANT: Counts for filter buttons should come from the BASE queryset (unfiltered)
    total_bills = base_bills.count()
    pending_count = base_bills.filter(status='pending').count()
    approved_count = base_bills.filter(status='approved').count()
    rejected_count = base_bills.filter(status='rejected').count()
    paid_count = base_bills.filter(status='paid').count()
    sent_to_controller_count = base_bills.filter(status='sent_to_controller').count()
    approved_by_controller_count = base_bills.filter(status='approved_by_controller').count()
    rejected_by_controller_count = base_bills.filter(status='rejected_by_controller').count()
    controller_returned_count = base_bills.filter(status='controller_returned').count()

    # Query string (without 'page') so pagination/PDF links keep the active filters
    querydict = request.GET.copy()
    querydict.pop('page', None)
    filter_querystring = querydict.urlencode()

    context = {
        'bills': page_obj,
        'total_bills': total_bills,  # Now shows total from base queryset
        'filtered_amount': filtered_amount,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'paid_count': paid_count,
        'sent_to_controller_count': sent_to_controller_count,
        'approved_by_controller_count': approved_by_controller_count,
        'rejected_by_controller_count': rejected_by_controller_count,
        'controller_returned_count': controller_returned_count,
        'semester_choices': Bill.SEMESTER_CHOICES,
        'degree_choices': Bill.DEGREE_CHOICES,
        'bank_choices': Bill.BANK_CHOICES,
        'status_choices': Bill.STATUS_CHOICES,
        'filter_querystring': filter_querystring,
        **filters,
    }
    return render(request, 'core/all_bills.html', context)


@login_required
@user_passes_test(is_admin)
def export_bills_pdf(request):
    """Generate a landscape PDF report of the currently filtered bills (admin dashboard)."""
    bills = _base_admin_bills_queryset(request)
    bills, filters = apply_bill_filters(request, bills)

    total_amount = bills.aggregate(total=Sum('total_amount'))['total'] or 0
    total_count = bills.count()

    status_labels = dict(Bill.STATUS_CHOICES)

    context = {
        'bills': bills,
        'filters': filters,
        'status_label': status_labels.get(filters['status_filter'], 'সব স্ট্যাটাস' if not filters['status_filter'] else filters['status_filter']),
        'total_amount': total_amount,
        'total_count': total_count,
        'generated_at': timezone.now(),
        'generated_by': request.user,
        'convert_to_bangla_digits': convert_to_bangla_digits,
        'format_bangla_number': format_bangla_number,
    }

    pdf_content = render_bills_report_pdf(context)

    if not pdf_content:
        messages.error(request, 'পিডিএফ রিপোর্ট তৈরি করতে সমস্যা হয়েছে।')
        return redirect('all_bills')

    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"bills_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    log_activity(request.user, 'Bills report exported', f'{total_count} filtered bills exported as PDF report')
    return response


@login_required
@user_passes_test(is_admin)
def update_bill_status(request, bill_id):
    """Update bill status (admin only)"""
    bill = get_object_or_404(Bill, id=bill_id)

    if request.method == 'POST':
        form = BillStatusForm(request.POST, instance=bill)
        if form.is_valid():
            bill = form.save(commit=False)
            
            if bill.status == 'approved' and not bill.approved_by:
                bill.approved_by = request.user
                bill.approved_at = timezone.now()
            elif bill.status != 'approved':
                bill.approved_by = None
                bill.approved_at = None
                
            bill.save()

            log_activity(request.user, 'Bill status updated',
                         f'Bill {bill.bill_number} status changed to {bill.status}')
            messages.success(request, 'বিলের স্ট্যাটাস সফলভাবে আপডেট করা হয়েছে!')
            return redirect('all_bills')
    else:
        form = BillStatusForm(instance=bill)

    context = {
        'bill': bill,
        'form': form
    }
    return render(request, 'core/update_bill_status.html', context)


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard view"""
    total_bills = Bill.objects.count()
    total_users = User.objects.count()
    total_amount = Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    pending_bills = Bill.objects.filter(status='pending').count()

    status_counts = Bill.objects.values('status').annotate(count=Count('id'))

    recent_activities = ActivityLog.objects.select_related('user').order_by('-created_at')[:10]

    recent_bills = Bill.objects.select_related('user').order_by('-created_at')[:5]

    context = {
        'total_bills': total_bills,
        'total_users': total_users,
        'total_amount': total_amount,
        'pending_bills': pending_bills,
        'status_counts': status_counts,
        'recent_activities': recent_activities,
        'recent_bills': recent_bills,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """User management view (admin only)"""
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    return render(request, 'core/user_management.html', {'users': users})


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username in ['JSTUChairman1', 'JSTUChairman2', 'JSTUChairman3', 'JSTUChairman4'])
def add_signature_to_bill_chairman(request, bill_id):
    """Add chairman's signature to approved bill based on chairman type - PERMANENT"""
    bill = get_object_or_404(Bill, id=bill_id)

    is_rollback_bill = bill.status == 'controller_returned'

    if bill.status not in ['approved', 'controller_returned']:
        messages.error(request, 'শুধুমাত্র অনুমোদিত অথবা কন্ট্রোলার ফেরত বিলে স্বাক্ষর যোগ করা যাবে।')
        return redirect('all_bills')
    
    # Check if signature is already added
    if bill.chairman_signature_added:
        messages.warning(request, 'এই বিলে ইতিমধ্যে চেয়ারম্যানের স্বাক্ষর যুক্ত হয়েছে।')
        if is_rollback_bill:
            return redirect('chairman_returned_bills')
        return redirect('view_bill_pdf', bill_id=bill.id)
    
    if request.method == 'POST':
        chairman_username = request.user.username
        signature_added = False
        
        # Determine which signature field to check
        if chairman_username == 'JSTUChairman1' and request.user.profile.signature_chairman1:
            signature_added = True
        elif chairman_username == 'JSTUChairman2' and request.user.profile.signature_chairman2:
            signature_added = True
        elif chairman_username == 'JSTUChairman3' and request.user.profile.signature_chairman3:
            signature_added = True
        elif chairman_username == 'JSTUChairman4' and request.user.profile.signature_chairman4:
            signature_added = True
        
        if signature_added:
            # Mark signature as added - THIS FLAG MAKES THE SIGNATURE PERMANENT
            bill.chairman_signature_added = True
            
            # Also store the chairman username in a dedicated field for easier lookup
            # (You may want to add a chairman_username field to Bill model)
            # For now, store it clearly in remarks
            year_text = ''
            if chairman_username == 'JSTUChairman1':
                year_text = '১ম বর্ষ'
            elif chairman_username == 'JSTUChairman2':
                year_text = '২য় বর্ষ'
            elif chairman_username == 'JSTUChairman3':
                year_text = '৩য় বর্ষ'
            elif chairman_username == 'JSTUChairman4':
                year_text = '৪র্থ বর্ষ'
            
            signature_note = f"\nচেয়ারম্যানের স্বাক্ষর যুক্ত: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')} ({chairman_username} - {year_text})"
            bill.remarks = (bill.remarks or '') + signature_note
            bill.save()
            
            log_activity(request.user, 'Signature added to bill', 
                        f'Chairman signature added to bill {bill.bill_number}')
            messages.success(request, f'বিল {bill.bill_number} এ আপনার স্বাক্ষর সফলভাবে যুক্ত হয়েছে! এটি স্থায়ীভাবে সংরক্ষিত হবে।')
            
            # After adding signature, show the PDF
            return redirect('view_bill_pdf', bill_id=bill.id)
        else:
            messages.error(request, 'আপনার স্বাক্ষর আপলোড করা হয়নি। দয়া করে প্রথমে স্বাক্ষর আপলোড করুন।')
            if chairman_username == 'JSTUChairman1':
                return redirect('signature_upload_chairman1')
            elif chairman_username == 'JSTUChairman2':
                return redirect('signature_upload_chairman2')
            elif chairman_username == 'JSTUChairman3':
                return redirect('signature_upload_chairman3')
            elif chairman_username == 'JSTUChairman4':
                return redirect('signature_upload_chairman4')

    if is_rollback_bill:
        return redirect('chairman_returned_bills')
    return redirect('update_bill_status', bill_id=bill.id)


# --------------------------
# Work Type Management Views (Admin Only)
# --------------------------

@login_required
@user_passes_test(is_admin)
def work_type_management(request):
    """Manage work types"""
    work_types = WorkType.objects.all()

    if request.method == 'POST':
        if 'add_work_type' in request.POST:
            name = request.POST.get('name')
            description = request.POST.get('description')
            degree_type = request.POST.get('degree_type', 'both')
            needs_benefit = 'needs_benefit' in request.POST
            default_amount = request.POST.get('default_amount', 0)

            if name:
                WorkType.objects.create(
                    name=name,
                    description=description,
                    degree_type=degree_type,
                    needs_benefit=needs_benefit,
                    default_amount=default_amount,
                    order=WorkType.objects.count() + 1
                )
                messages.success(request, 'কাজের ধরণ সফলভাবে যোগ করা হয়েছে!')

        elif 'edit_work_type' in request.POST:
            work_type_id = request.POST.get('work_type_id')
            work_type = get_object_or_404(WorkType, id=work_type_id)
            work_type.name = request.POST.get('name')
            work_type.description = request.POST.get('description')
            work_type.degree_type = request.POST.get('degree_type', 'both')
            work_type.needs_benefit = 'needs_benefit' in request.POST
            work_type.default_amount = request.POST.get('default_amount', 0)
            work_type.is_active = 'is_active' in request.POST
            work_type.save()
            messages.success(request, 'কাজের ধরণ সফলভাবে আপডেট করা হয়েছে!')

        elif 'delete_work_type' in request.POST:
            work_type_id = request.POST.get('work_type_id')
            work_type = get_object_or_404(WorkType, id=work_type_id)
            work_type.delete()
            messages.success(request, 'কাজের ধরণ সফলভাবে ডিলিট করা হয়েছে!')

    return render(request, 'core/work_type_management.html', {'work_types': work_types})


@login_required
@user_passes_test(is_admin)
def benefit_management(request):
    """Manage benefits"""
    work_type_id = request.GET.get('work_type_id')
    benefits = Benefit.objects.all()

    if work_type_id:
        benefits = benefits.filter(work_type_id=work_type_id)

    if request.method == 'POST':
        if 'add_benefit' in request.POST:
            work_type_id = request.POST.get('work_type')
            name = request.POST.get('name')
            calculation_type = request.POST.get('calculation_type')
            base_amount = request.POST.get('base_amount')
            unit_label = request.POST.get('unit_label')

            if work_type_id and name and calculation_type and base_amount:
                work_type = get_object_or_404(WorkType, id=work_type_id)
                Benefit.objects.create(
                    work_type=work_type,
                    name=name,
                    calculation_type=calculation_type,
                    base_amount=base_amount,
                    unit_label=unit_label if calculation_type != 'fixed' else '',
                    min_unit=request.POST.get('min_unit', 1),
                    max_unit=request.POST.get('max_unit', 100),
                    order=Benefit.objects.filter(work_type=work_type).count() + 1
                )
                messages.success(request, 'উপকাজ সফলভাবে যোগ করা হয়েছে!')

        elif 'edit_benefit' in request.POST:
            benefit_id = request.POST.get('benefit_id')
            benefit = get_object_or_404(Benefit, id=benefit_id)
            benefit.name = request.POST.get('name')
            benefit.calculation_type = request.POST.get('calculation_type')
            benefit.base_amount = request.POST.get('base_amount')
            benefit.unit_label = request.POST.get('unit_label') if benefit.calculation_type != 'fixed' else ''
            benefit.min_unit = request.POST.get('min_unit', 1)
            benefit.max_unit = request.POST.get('max_unit', 100)
            benefit.is_active = 'is_active' in request.POST
            benefit.save()
            messages.success(request, 'উপকাজ সফলভাবে আপডেট করা হয়েছে!')

        elif 'delete_benefit' in request.POST:
            benefit_id = request.POST.get('benefit_id')
            benefit = get_object_or_404(Benefit, id=benefit_id)
            benefit.delete()
            messages.success(request, 'উপকাজ সফলভাবে ডিলিট করা হয়েছে!')

    work_types = WorkType.objects.filter(is_active=True)
    return render(request, 'core/benefit_management.html', {
        'benefits': benefits,
        'work_types': work_types,
    })


# --------------------------
# Signature Upload Views (General User)
# --------------------------

@login_required
def signature_upload_general(request):
    """View for general users to upload signature"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload_general')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload_general')
            
            request.user.profile.signature_general = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'User uploaded general signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload_general')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_general')
    
    return render(request, 'core/signature_upload_general.html')


@login_required
def delete_signature_general(request):
    """View for general users to delete signature"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature_general:
            request.user.profile.signature_general.delete(save=False)
            request.user.profile.signature_general = None
            request.user.profile.save()
            
            log_activity(request.user, 'Signature deleted', 'User deleted general signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload_general')


# --------------------------
# Signature Upload Views (Chairman 1)
# --------------------------

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman1')
def signature_upload_chairman1(request):
    """View for chairman 1 to upload signature"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload_chairman1')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload_chairman1')
            
            request.user.profile.signature_chairman1 = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'Chairman 1 uploaded signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload_chairman1')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_chairman1')
    
    return render(request, 'core/signature_upload_chairman1.html')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman1')
def delete_signature_chairman1(request):
    """View for chairman 1 to delete signature"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature_chairman1:
            request.user.profile.signature_chairman1.delete(save=False)
            request.user.profile.signature_chairman1 = None
            request.user.profile.save()
            
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload_chairman1')


# --------------------------
# Signature Upload Views (Chairman 2)
# --------------------------

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman2')
def signature_upload_chairman2(request):
    """View for chairman 2 to upload signature"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload_chairman2')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload_chairman2')
            
            request.user.profile.signature_chairman2 = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'Chairman 2 uploaded signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload_chairman2')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_chairman2')
    
    return render(request, 'core/signature_upload_chairman2.html')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman2')
def delete_signature_chairman2(request):
    """View for chairman 2 to delete signature"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature_chairman2:
            request.user.profile.signature_chairman2.delete(save=False)
            request.user.profile.signature_chairman2 = None
            request.user.profile.save()
            
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload_chairman2')


# --------------------------
# Signature Upload Views (Chairman 3)
# --------------------------

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman3')
def signature_upload_chairman3(request):
    """View for chairman 3 to upload signature"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload_chairman3')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload_chairman3')
            
            request.user.profile.signature_chairman3 = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'Chairman 3 uploaded signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload_chairman3')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_chairman3')
    
    return render(request, 'core/signature_upload_chairman3.html')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman3')
def delete_signature_chairman3(request):
    """View for chairman 3 to delete signature"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature_chairman3:
            request.user.profile.signature_chairman3.delete(save=False)
            request.user.profile.signature_chairman3 = None
            request.user.profile.save()
            
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload_chairman3')


# --------------------------
# Signature Upload Views (Chairman 4)
# --------------------------

@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman4')
def signature_upload_chairman4(request):
    """View for chairman 4 to upload signature"""
    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if signature_file:
            if not signature_file.content_type in ['image/jpeg', 'image/png', 'image/jpg']:
                messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
                return redirect('signature_upload_chairman4')
            
            if signature_file.size > 2 * 1024 * 1024:
                messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
                return redirect('signature_upload_chairman4')
            
            request.user.profile.signature_chairman4 = signature_file
            request.user.profile.save()
            
            log_activity(request.user, 'Signature uploaded', 'Chairman 4 uploaded signature')
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
            return redirect('signature_upload_chairman4')
        else:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_chairman4')
    
    return render(request, 'core/signature_upload_chairman4.html')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.username == 'JSTUChairman4')
def delete_signature_chairman4(request):
    """View for chairman 4 to delete signature"""
    if request.method == 'POST' or request.method == 'GET':
        if request.user.profile.signature_chairman4:
            request.user.profile.signature_chairman4.delete(save=False)
            request.user.profile.signature_chairman4 = None
            request.user.profile.save()
            
            messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
        else:
            messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
        
        return redirect('signature_upload_chairman4')


# --------------------------
# API Endpoints
# --------------------------

def get_work_types(request):
    """API: Get all work types"""
    work_types = WorkType.objects.filter(is_active=True).order_by('order')
    work_type_list = [(wt.name, wt.name) for wt in work_types]
    return JsonResponse({'work_types': work_type_list})


def get_work_type_details(request):
    """API: Get work type details"""
    work_type_name = request.GET.get('work_type')
    if work_type_name:
        try:
            work_type = WorkType.objects.get(name=work_type_name, is_active=True)
            return JsonResponse({
                'needs_benefit': work_type.needs_benefit,
                'default_amount': float(work_type.default_amount) if work_type.default_amount else 0,
                'description': work_type.description
            })
        except WorkType.DoesNotExist:
            pass
    return JsonResponse({'needs_benefit': True, 'default_amount': 0, 'description': ''})


def get_benefit_choices(request):
    """API: Get benefit choices for a work type"""
    work_type_name = request.GET.get('work_type')
    if work_type_name:
        try:
            work_type = WorkType.objects.get(name=work_type_name, is_active=True)

            if not work_type.needs_benefit:
                dummy_benefit = {
                    'id': 'no_benefit',
                    'name': f'{work_type.name} (স্বয়ংক্রিয়)'
                }
                return JsonResponse({
                    'benefits': [[dummy_benefit['id'], dummy_benefit['name']]],
                    'needs_benefit': False,
                    'default_amount': float(work_type.default_amount)
                })

            benefits = Benefit.objects.filter(work_type=work_type, is_active=True)
            benefit_list = [(benefit.id, benefit.name) for benefit in benefits]
            return JsonResponse({
                'benefits': benefit_list,
                'needs_benefit': True,
                'default_amount': 0
            })
        except WorkType.DoesNotExist:
            pass
    return JsonResponse({'benefits': [], 'needs_benefit': True, 'default_amount': 0})


def get_benefit_details(request):
    """API: Get calculation details for a benefit"""
    benefit_id = request.GET.get('benefit_id')
    try:
        benefit = Benefit.objects.get(id=benefit_id, is_active=True)
        return JsonResponse({
            'calculation_type': benefit.calculation_type,
            'base_amount': str(benefit.base_amount),
            'unit_label': benefit.unit_label,
            'min_unit': benefit.min_unit,
            'max_unit': benefit.max_unit
        })
    except Benefit.DoesNotExist:
        return JsonResponse({
            'calculation_type': 'fixed',
            'base_amount': '0',
            'unit_label': '',
            'min_unit': 1,
            'max_unit': 100
        })


def get_work_types_by_degree(request):
    """API: Get work types filtered by degree type"""
    degree_type = request.GET.get('degree_type', 'honors')

    if degree_type == 'honors':
        work_types = WorkType.objects.filter(
            Q(degree_type='honors') | Q(degree_type='both'),
            is_active=True
        ).order_by('order')
    elif degree_type == 'masters':
        work_types = WorkType.objects.filter(
            Q(degree_type='masters') | Q(degree_type='both'),
            is_active=True
        ).order_by('order')
    else:
        work_types = WorkType.objects.filter(is_active=True).order_by('order')

    work_type_list = []
    for wt in work_types:
        work_type_list.append({
            'value': wt.name,
            'display': str(wt),
            'degree_type': wt.degree_type,
            'id': wt.id
        })

    return JsonResponse({'work_types': work_type_list})


def get_benefit_choices_by_degree(request):
    """API: Get benefit choices filtered by work type and degree"""
    work_type_name = request.GET.get('work_type')
    degree_type = request.GET.get('degree_type', 'honors')

    if work_type_name:
        try:
            work_type = WorkType.objects.filter(
                Q(name=work_type_name),
                Q(degree_type=degree_type) | Q(degree_type='both'),
                is_active=True
            ).order_by(
                # exact degree match (honors/masters) first, 'both' as fallback
                Case(
                    When(degree_type=degree_type, then=0),
                    default=1,
                    output_field=IntegerField()
                )
            ).first()

            if not work_type:
                raise WorkType.DoesNotExist

            if not work_type.needs_benefit:
                dummy_benefit = {
                    'id': 'no_benefit',
                    'name': f'{work_type.get_display_name()} (স্বয়ংক্রিয়)'
                }
                return JsonResponse({
                    'benefits': [[dummy_benefit['id'], dummy_benefit['name']]],
                    'needs_benefit': False,
                    'default_amount': float(work_type.default_amount)
                })

            benefits = Benefit.objects.filter(
                work_type=work_type,
                is_active=True
            )
            benefit_list = [(benefit.id, benefit.name) for benefit in benefits]
            return JsonResponse({
                'benefits': benefit_list,
                'needs_benefit': True,
                'default_amount': 0
            })
        except WorkType.DoesNotExist:
            return JsonResponse({
                'error': f'এই ডিগ্রির জন্য "{work_type_name}" কাজের ধরণ পাওয়া যায়নি',
                'benefits': [],
                'needs_benefit': True,
                'default_amount': 0
            })

    return JsonResponse({'benefits': [], 'needs_benefit': True, 'default_amount': 0})


def get_work_type_amount(request):
    """API: Get amount for work type (when no benefit needed)"""
    work_type_name = request.GET.get('work_type')
    degree_type = request.GET.get('degree_type', 'honors')

    try:
        work_type = WorkType.objects.filter(
            Q(name=work_type_name),
            Q(degree_type=degree_type) | Q(degree_type='both'),
            is_active=True
        ).order_by(
            # exact degree match (honors/masters) first, 'both' as fallback
            Case(
                When(degree_type=degree_type, then=0),
                default=1,
                output_field=IntegerField()
            )
        ).first()

        if not work_type:
            return JsonResponse({'amount': 0})

        if not work_type.needs_benefit:
            return JsonResponse({'amount': float(work_type.default_amount)})
        else:
            return JsonResponse({'amount': 0})
    except WorkType.DoesNotExist:
        return JsonResponse({'amount': 0})


def get_benefit_choices_old(request):
    """API: Legacy endpoint for benefit choices"""
    work_type = request.GET.get('work_type')
    benefits = Bill.BENEFIT_CHOICES.get(work_type, [])
    return JsonResponse({'benefits': benefits})


def get_amount_old(request):
    """API: Legacy endpoint for amount calculation"""
    benefit = request.GET.get('benefit')
    amount = Bill.AMOUNT_MAPPING.get(benefit, 0)

    english_to_bangla = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
    bangla_amount = str(int(amount)).translate(english_to_bangla)

    return JsonResponse({'amount': amount, 'bangla_amount': bangla_amount})


# --------------------------
# Legacy Add Signature to Bill
# --------------------------

@login_required
def add_signature_to_bill(request, bill_id):
    """Legacy add signature to bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if bill.status != 'approved':
        messages.error(request, 'শুধুমাত্র অনুমোদিত বিলে স্বাক্ষর যোগ করা যাবে।')
        return redirect('all_bills')
    
    if request.method == 'POST':
        if request.user.profile.signature:
            log_activity(request.user, 'Signature added to bill', 
                        f'Signature added to bill {bill.bill_number}')
            messages.success(request, f'বিল {bill.bill_number} এ স্বাক্ষর সফলভাবে যুক্ত হয়েছে!')
            return redirect('view_bill_pdf', bill_id=bill.id)
        else:
            messages.error(request, 'আপনার স্বাক্ষর আপলোড করা হয়নি।')
            return redirect('signature_upload')
    
    return redirect('update_bill_status', bill_id=bill.id)


# --------------------------
# Debug Views
# --------------------------
import os
@login_required
def debug_bill_signature(request, bill_id):
    """Debug view to check signature for a specific bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    from .utils import get_chairman_signature_for_bill
    signature_url = get_chairman_signature_for_bill(bill)
    
    # Also check the chairman user directly
    chairman_info = {}
    if 'JSTUChairman1' in bill.remarks:
        try:
            chairman = User.objects.get(username='JSTUChairman1')
            chairman_info = {
                'username': chairman.username,
                'has_signature': bool(chairman.profile.signature_chairman1),
                'signature_path': chairman.profile.signature_chairman1.path if chairman.profile.signature_chairman1 else None,
                'file_exists': os.path.exists(chairman.profile.signature_chairman1.path) if chairman.profile.signature_chairman1 else False,
            }
        except:
            chairman_info = {'error': 'Chairman not found'}
    
    debug_data = {
        'bill_id': bill.id,
        'bill_number': bill.bill_number,
        'bill_status': bill.status,
        'bill_remarks': bill.remarks,
        'signature_found': bool(signature_url),
        'signature_length': len(signature_url) if signature_url else 0,
        'chairman_info': chairman_info,
    }
    
    return JsonResponse(debug_data)


# --------------------------
# Error Handlers
# --------------------------

def handler404(request, exception):
    """Custom 404 error handler"""
    return render(request, 'core/404.html', status=404)


def handler500(request):
    """Custom 500 error handler"""
    return render(request, 'core/500.html', status=500)





@login_required
def edit_bill(request, bill_id):
    """Edit an existing bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check permission
    if bill.user != request.user:
        messages.error(request, 'আপনার এই বিল এডিট করার অনুমতি নেই।')
        return redirect('my_bills')
    
    # Only draft, rejected, or returned_to_user bills can be edited
    if bill.status not in ['draft', 'rejected', 'returned_to_user']:
        messages.error(request, 'শুধুমাত্র খসড়া, বাতিলকৃত অথবা ফেরত বিল এডিট করা যাবে।')
        return redirect('my_bills')

    was_returned_bill = bill.status == 'returned_to_user'
    
    if request.method == 'POST':
        form = BillForm(request.POST, instance=bill)
        action = request.POST.get('action', 'save')
        
        if form.is_valid():
            bill = form.save(commit=False)
            
            if action == 'send':
                bill.status = 'pending'
                bill.sent_at = timezone.now()
                
                # IMPORTANT: When user resends a returned bill, make it visible to chairman again
                if was_returned_bill:
                    bill.is_hidden_from_chairman = False  # Show it again in chairman's list
                    bill.resend_count = (bill.resend_count or 0) + 1
                    bill.remarks = (bill.remarks or '') + (
                        f"\nপুনঃপ্রেরণ ({timezone.now().strftime('%d-%m-%Y %H:%M')}): "
                        f"বিল প্রস্তুতকারী সংশোধন করে একই ভাউচার নম্বরে (ভাউচার নং: {bill.voucher_number}) "
                        f"পুনরায় চেয়ারম্যানের কাছে পাঠিয়েছেন।"
                    )
                success_message = (
                    'বিল সফলভাবে সংশোধন করে একই ভাউচার নম্বরে চেয়ারম্যানের কাছে পুনরায় পাঠানো হয়েছে!'
                    if was_returned_bill else 'বিল সফলভাবে আপডেট এবং পাঠানো হয়েছে!'
                )
                redirect_url = 'bill_status'
            else:
                # FIX: Keep returned_to_user status if it was a returned bill
                if was_returned_bill:
                    bill.status = 'returned_to_user'  # Keep it as returned_to_user
                    bill.is_hidden_from_chairman = True  # Keep hidden from chairman
                else:
                    bill.status = 'draft'
                    bill.sent_at = None
                success_message = 'বিল সফলভাবে আপডেট করা হয়েছে!'
                redirect_url = 'my_bills'
            
            bill.save()
            
            # Delete existing tasks
            Task.objects.filter(bill=bill).delete()
            
            # Create new tasks
            tasks_data = json.loads(request.POST.get('tasks', '[]'))
            total_amount = 0
            
            for task_data in tasks_data:
                task = Task(
                    bill=bill,
                    work_type=task_data['work_type'],
                    benefit=task_data['benefit'],
                    quantity=task_data.get('quantity', 1),
                    unit=task_data.get('unit', ''),
                    amount=task_data['amount'],
                    remarks=task_data.get('remarks', '')
                )
                task.save()
                total_amount += float(task_data['amount'])
            
            bill.total_amount = total_amount
            bill.save()
            
            log_activity(request.user, 'Bill edited', f'Bill {bill.bill_number} edited')
            messages.success(request, success_message)
            return redirect(redirect_url)
    else:
        form = BillForm(instance=bill)
        
    # Get existing tasks
    tasks = bill.tasks.all()
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'work_type': task.work_type,
            'benefit': task.benefit,
            'quantity': task.quantity,
            'unit': task.unit,
            'amount': str(task.amount),
            'remarks': task.remarks or ''
        })
    
    context = {
        'form': form,
        'bill': bill,
        'tasks_json': json.dumps(tasks_list, ensure_ascii=False),
        'edit_mode': True
    }
    return render(request, 'core/bill_edit.html', context)



def is_controller(user):
    """Check if user is a Controller"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'কন্ট্রোলার'
 
 
# --------------------------
# Controller Home View
# --------------------------
 
@login_required
@user_passes_test(is_controller)
def controller_home(request):
    """Controller dashboard - shows all non-draft bills with stats"""
    all_non_draft_bills = Bill.objects.exclude(status='draft')
    
    # Get new bills count (bills sent to controller that haven't been processed)
    new_bills_count = Bill.objects.filter(status='sent_to_controller').count()
    
    bills_list = all_non_draft_bills.select_related('user', 'user__profile').order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        bills_list = bills_list.filter(status=status_filter)
    
    total_bills = all_non_draft_bills.count()
    total_amount = all_non_draft_bills.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # CORRECTED COUNTS - using controller-specific statuses
    pending_count = all_non_draft_bills.filter(status='pending').count()
    approved_count = all_non_draft_bills.filter(status='approved_by_controller').count()  # Controller approved
    rejected_count = all_non_draft_bills.filter(status='rejected_by_controller').count()  # Controller rejected
    paid_count = all_non_draft_bills.filter(status='paid').count()
    sent_to_controller_count = all_non_draft_bills.filter(status='sent_to_controller').count()
    
    # Get session to track if notification has been shown
    if 'notification_shown' in request.session and request.session['notification_shown'] < new_bills_count:
        # Reset notification shown flag if there are more new bills
        request.session['notification_shown'] = new_bills_count
    elif 'notification_shown' not in request.session:
        request.session['notification_shown'] = new_bills_count
    
    total_users = User.objects.count()
    recent_bills = Bill.objects.select_related('user').order_by('-created_at')[:10]
    
    paginator = Paginator(bills_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'new_bills_count': new_bills_count,
        'total_bills': total_bills,
        'total_users': total_users,
        'total_amount': total_amount,
        'recent_bills': recent_bills,
        'bills': page_obj,
        'current_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,  # Now shows controller approved count
        'rejected_count': rejected_count,  # Now shows controller rejected count
        'paid_count': paid_count,
        'sent_to_controller_count': sent_to_controller_count,
    }
    return render(request, 'core/home_con.html', context)


@login_required
@require_POST
def mark_notification_seen(request):
    """Mark notification as seen"""
    if request.user.is_authenticated and request.user.profile.user_type == 'কন্ট্রোলার':
        new_bills_count = Bill.objects.filter(status='sent_to_controller').count()
        request.session['notification_shown'] = new_bills_count
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def send_bill_to_controller(request, bill_id):
    """Send approved bill to controller for final approval"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Only approved bills can be sent to controller
    if bill.status != 'approved':
        messages.error(request, 'শুধুমাত্র অনুমোদিত বিল কন্ট্রোলারে পাঠানো যাবে।')
        return redirect('all_bills')
    
    # Update bill status
    bill.status = 'sent_to_controller'
    bill.sent_to_controller_at = timezone.now()
    bill.save()
    
    log_activity(request.user, 'Bill sent to controller', 
                f'Bill {bill.bill_number} sent to controller for approval')
    messages.success(request, f'বিল {bill.bill_number} কন্ট্রোলারের অনুমোদনের জন্য প্রেরণ করা হয়েছে!')
    
    return redirect('all_bills')



@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def cont_bills(request):
    """Controller bills view with year-wise sections"""
    # Get all bills sent from chairman (status = 'sent_to_controller')
    all_bills = Bill.objects.filter(status='sent_to_controller').order_by('-sent_to_controller_at')
    
    # Helper function to determine year from remarks
    def get_bill_year(bill):
        if '১ম বর্ষ' in bill.remarks or 'JSTUChairman1' in bill.remarks:
            return '1st'
        elif '২য় বর্ষ' in bill.remarks or 'JSTUChairman2' in bill.remarks:
            return '2nd'
        elif '৩য় বর্ষ' in bill.remarks or 'JSTUChairman3' in bill.remarks:
            return '3rd'
        elif '৪র্থ বর্ষ' in bill.remarks or 'JSTUChairman4' in bill.remarks:
            return '4th'
        return None
    
    # Separate bills by year
    first_year_bills = []
    second_year_bills = []
    third_year_bills = []
    fourth_year_bills = []
    
    for bill in all_bills:
        year = get_bill_year(bill)
        if year == '1st':
            first_year_bills.append(bill)
        elif year == '2nd':
            second_year_bills.append(bill)
        elif year == '3rd':
            third_year_bills.append(bill)
        elif year == '4th':
            fourth_year_bills.append(bill)
    
    # CORRECTED COUNTS - using controller-specific statuses
    context = {
        'total_bills': all_bills.count(),
        'pending_count': all_bills.count(),
        'approved_count': Bill.objects.filter(status='approved_by_controller').count(),  # Controller approved
        'rejected_count': Bill.objects.filter(status='rejected_by_controller').count(),  # Controller rejected
        'first_year_bills': first_year_bills,
        'second_year_bills': second_year_bills,
        'third_year_bills': third_year_bills,
        'fourth_year_bills': fourth_year_bills,
    }
    return render(request, 'core/cont_bills.html', context)




@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def controller_update_bill_status(request, bill_id):
    """Controller updates bill status"""
    bill = get_object_or_404(Bill, id=bill_id)
    status = request.POST.get('status')
    remarks = request.POST.get('remarks', '')
    
    if status in ['approved_by_controller', 'rejected_by_controller']:
        bill.status = status
        if remarks:
            bill.remarks = (bill.remarks or '') + f"\nকন্ট্রোলার মন্তব্য: {remarks}"
        bill.controller_approved_at = timezone.now()
        bill.controller_approved_by = request.user
        bill.save()
        
        log_activity(request.user, f'Bill {status} by controller', 
                    f'Bill {bill.bill_number} {status} by controller')
        
        status_text = 'অনুমোদিত' if status == 'approved_by_controller' else 'বাতিল'
        messages.success(request, f'বিল {bill.bill_number} {status_text} করা হয়েছে!')
    
    return redirect('cont_bills')


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def controller_delete_bill(request, bill_id):
    """Controller deletes a bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    bill_number = bill.bill_number
    bill.delete()
    
    log_activity(request.user, 'Bill deleted by controller', 
                f'Bill {bill_number} deleted by controller')
    messages.success(request, f'বিল {bill_number} স্থায়ীভাবে ডিলিট করা হয়েছে!')
    
    return redirect('cont_bills')


def apply_accepted_bill_filters(request, bills):
    """Apply every filter available on the controller's accepted-bills page.

    Returns (filtered_queryset, filters_dict).
    """
    year_filter = request.GET.get('year', '').strip()
    user_filter = request.GET.get('user', '').strip()
    semester_filter = request.GET.get('semester', '').strip()
    degree_filter = request.GET.get('degree_type', '').strip()
    department_filter = request.GET.get('department', '').strip()
    bank_filter = request.GET.get('bank_name', '').strip()
    bill_number_filter = request.GET.get('bill_number', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    amount_min = request.GET.get('amount_min', '').strip()
    amount_max = request.GET.get('amount_max', '').strip()

    if year_filter:
        year_text = {'1st': '১ম বর্ষ', '2nd': '২য় বর্ষ', '3rd': '৩য় বর্ষ', '4th': '৪র্থ বর্ষ'}.get(year_filter, '')
        if year_text:
            bills = bills.filter(remarks__icontains=year_text)
    if user_filter:
        bills = bills.filter(user__username__icontains=user_filter)
    if semester_filter:
        bills = bills.filter(semester=semester_filter)
    if degree_filter:
        bills = bills.filter(degree_type=degree_filter)
    if department_filter:
        bills = bills.filter(department__icontains=department_filter)
    if bank_filter:
        bills = bills.filter(bank_name=bank_filter)
    if bill_number_filter:
        bills = bills.filter(
            Q(bill_number__icontains=bill_number_filter) | Q(voucher_number__icontains=bill_number_filter)
        )

    if date_from:
        try:
            parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            bills = bills.filter(controller_approved_at__date__gte=parsed)
        except ValueError:
            date_from = ''
    if date_to:
        try:
            parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            bills = bills.filter(controller_approved_at__date__lte=parsed)
        except ValueError:
            date_to = ''

    if amount_min:
        try:
            bills = bills.filter(total_amount__gte=Decimal(amount_min))
        except InvalidOperation:
            amount_min = ''
    if amount_max:
        try:
            bills = bills.filter(total_amount__lte=Decimal(amount_max))
        except InvalidOperation:
            amount_max = ''

    filters = {
        'year_filter': year_filter,
        'user_filter': user_filter,
        'semester_filter': semester_filter,
        'degree_filter': degree_filter,
        'department_filter': department_filter,
        'bank_filter': bank_filter,
        'bill_number_filter': bill_number_filter,
        'date_from': date_from,
        'date_to': date_to,
        'amount_min': amount_min,
        'amount_max': amount_max,
    }
    return bills, filters


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def accepted_bills(request):
    """Controller accepted bills view"""
    # Get all bills approved by controller
    accepted_bills_list = Bill.objects.filter(status='approved_by_controller').select_related('user').order_by('-controller_approved_at')

    # Apply filters FIRST
    accepted_bills_list, filters = apply_accepted_bill_filters(request, accepted_bills_list)

    # Calculate year for each bill
    for bill in accepted_bills_list:
        if '১ম বর্ষ' in bill.remarks or 'JSTUChairman1' in bill.remarks:
            bill.year = '1st'
        elif '২য় বর্ষ' in bill.remarks or 'JSTUChairman2' in bill.remarks:
            bill.year = '2nd'
        elif '৩য় বর্ষ' in bill.remarks or 'JSTUChairman3' in bill.remarks:
            bill.year = '3rd'
        elif '৪র্থ বর্ষ' in bill.remarks or 'JSTUChairman4' in bill.remarks:
            bill.year = '4th'
        else:
            bill.year = ''

    # Pagination
    paginator = Paginator(accepted_bills_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate total amount from FILTERED list
    total_amount = accepted_bills_list.aggregate(total=Sum('total_amount'))['total'] or 0

    # Query string (without 'page') so pagination/PDF links keep the active filters
    querydict = request.GET.copy()
    querydict.pop('page', None)
    filter_querystring = querydict.urlencode()

    # Get counts from the FILTERED list, not from all bills
    total_accepted = accepted_bills_list.count()  # This will match the displayed count
    
    # For sidebar stats, use the FILTERED counts as well, or show ALL counts
    # Option 1: Show counts from the filtered list (matches what's displayed)
    context = {
        'accepted_bills': page_obj,
        'total_accepted': total_accepted,  # MATCHES the displayed bills
        'total_amount': total_amount,
        'pending_count': accepted_bills_list.filter(status='sent_to_controller').count(),  # Filtered
        'rejected_count': accepted_bills_list.filter(status='rejected_by_controller').count(),  # Filtered
        'semester_choices': Bill.SEMESTER_CHOICES,
        'degree_choices': Bill.DEGREE_CHOICES,
        'bank_choices': Bill.BANK_CHOICES,
        'filter_querystring': filter_querystring,
        **filters,
    }
    return render(request, 'core/accepted_bills.html', context)


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def export_accepted_bills_pdf(request):
    """Generate a PDF report of the currently filtered controller-approved bills."""
    accepted_bills_list = Bill.objects.filter(status='approved_by_controller').select_related('user').order_by('-controller_approved_at')
    accepted_bills_list, filters = apply_accepted_bill_filters(request, accepted_bills_list)

    total_amount = accepted_bills_list.aggregate(total=Sum('total_amount'))['total'] or 0
    total_count = accepted_bills_list.count()

    year_labels = {'1st': '১ম বর্ষ', '2nd': '২য় বর্ষ', '3rd': '৩য় বর্ষ', '4th': '৪র্থ বর্ষ'}

    context = {
        'bills': accepted_bills_list,
        'filters': filters,
        'status_label': 'কন্ট্রোলার কর্তৃক অনুমোদিত',
        'year_label': year_labels.get(filters['year_filter'], filters['year_filter']),
        'total_amount': total_amount,
        'total_count': total_count,
        'generated_at': timezone.now(),
        'generated_by': request.user,
        'report_title': 'অনুমোদিত বিল রিপোর্ট',
        'report_subtitle': 'কন্ট্রোলার প্যানেল',
        'convert_to_bangla_digits': convert_to_bangla_digits,
        'format_bangla_number': format_bangla_number,
    }

    pdf_content = render_bills_report_pdf(context)

    if not pdf_content:
        messages.error(request, 'পিডিএফ রিপোর্ট তৈরি করতে সমস্যা হয়েছে।')
        return redirect('accepted_bills')

    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"accepted_bills_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    log_activity(request.user, 'Accepted bills report exported', f'{total_count} filtered accepted bills exported as PDF report')
    return response


@login_required
def bill_details_api(request, bill_id):
    """API endpoint for bill details"""
    bill = get_object_or_404(Bill, id=bill_id)
    tasks = bill.tasks.all()
    
    data = {
        'bill_number': bill.bill_number,
        'user_name': bill.user.get_full_name() or bill.user.username,
        'user_type': bill.user.profile.user_type if hasattr(bill.user, 'profile') else '',
        'semester': bill.semester,
        'total_amount': f"{bill.total_amount:,.2f}",
        'approved_date': bill.controller_approved_at.strftime('%d-%m-%Y %I:%M %p') if bill.controller_approved_at else '',
        'approved_by': bill.controller_approved_by.get_full_name() or bill.controller_approved_by.username if bill.controller_approved_by else '',
        'remarks': bill.remarks,
        'tasks': [{'work_type': t.work_type, 'benefit': t.benefit, 'amount': f"{t.amount:,.2f}"} for t in tasks],
    }
    return JsonResponse(data)


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def rejected_bills(request):
    """Controller rejected bills view"""
    # Get all bills rejected by controller
    rejected_bills_list = Bill.objects.filter(status='rejected_by_controller').order_by('-controller_approved_at')
    
    # Get filter parameters
    year_filter = request.GET.get('year', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if year_filter:
        year_text = {'1st': '১ম বর্ষ', '2nd': '২য় বর্ষ', '3rd': '৩য় বর্ষ', '4th': '৪র্থ বর্ষ'}.get(year_filter, '')
        if year_text:
            rejected_bills_list = rejected_bills_list.filter(remarks__icontains=year_text)
    
    if user_filter:
        rejected_bills_list = rejected_bills_list.filter(user__username__icontains=user_filter)
    
    if date_from:
        rejected_bills_list = rejected_bills_list.filter(controller_approved_at__gte=date_from)
    
    if date_to:
        rejected_bills_list = rejected_bills_list.filter(controller_approved_at__lte=date_to)
    
    # Calculate year for each bill
    for bill in rejected_bills_list:
        if '১ম বর্ষ' in bill.remarks or 'JSTUChairman1' in bill.remarks:
            bill.year = '1st'
        elif '২য় বর্ষ' in bill.remarks or 'JSTUChairman2' in bill.remarks:
            bill.year = '2nd'
        elif '৩য় বর্ষ' in bill.remarks or 'JSTUChairman3' in bill.remarks:
            bill.year = '3rd'
        elif '৪র্থ বর্ষ' in bill.remarks or 'JSTUChairman4' in bill.remarks:
            bill.year = '4th'
        else:
            bill.year = ''
    
    # Pagination
    paginator = Paginator(rejected_bills_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total amount
    total_amount = rejected_bills_list.aggregate(total=Sum('total_amount'))['total'] or 0
    
    context = {
        'rejected_bills': page_obj,
        'total_rejected': rejected_bills_list.count(),
        'total_amount': total_amount,
        'pending_count': Bill.objects.filter(status='sent_to_controller').count(),
        'approved_count': Bill.objects.filter(status='approved_by_controller').count(),
        'year_filter': year_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'core/rejected_bills.html', context)

@login_required
@require_POST
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def controller_return_bill_to_chairman(request, bill_id):
    """Bill Rollback (Step 1): Controller sends a controller-rejected bill back to the chairman
    instead of leaving it permanently rejected. The chairman will then be able to review the
    controller's comment, sign, and forward it on to the original bill creator."""
    bill = get_object_or_404(Bill, id=bill_id)

    if bill.status != 'rejected_by_controller':
        messages.error(request, 'শুধুমাত্র কন্ট্রোলার কর্তৃক বাতিলকৃত বিল চেয়ারম্যানে ফেরত পাঠানো যাবে।')
        return redirect('rejected_bills')

    bill.status = 'controller_returned'
    bill.returned_to_chairman_at = timezone.now()
    bill.returned_to_chairman_by = request.user
    bill.save()

    log_activity(request.user, 'Bill returned to chairman by controller',
                f'Bill {bill.bill_number} returned to chairman for review')
    messages.success(request, f'বিল {bill.bill_number} চেয়ারম্যানের কাছে ফেরত পাঠানো হয়েছে!')

    return redirect('rejected_bills')


def _chairman_scoped_queryset(request, base_qs):
    """Scope a bill queryset to the logged-in chairman's year, same convention used elsewhere
    (a chairman only sees bills whose remarks mention their year)."""
    chairman_username = request.user.username
    year_map = {
        'JSTUChairman1': '১ম বর্ষ',
        'JSTUChairman2': '২য় বর্ষ',
        'JSTUChairman3': '৩য় বর্ষ',
        'JSTUChairman4': '৪র্থ বর্ষ',
    }
    year_text = year_map.get(chairman_username, '')
    if year_text:
        return base_qs.filter(remarks__icontains=year_text)
    return base_qs


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def chairman_returned_bills(request):
    """Bill Rollback (Step 2): Chairman's view of bills the controller has sent back.
    From here the chairman can view/download the bill, read the controller's comment,
    add their signature, and forward the bill on to the original creator (ফেরত বিল)."""
    # Only show controller_returned bills that are NOT hidden and NOT already returned to user
    bills_list = Bill.objects.filter(
        status='controller_returned',
        is_hidden_from_chairman=False
    ).select_related('user', 'user__profile')
    
    bills_list = _chairman_scoped_queryset(request, bills_list).order_by('-returned_to_chairman_at')

    paginator = Paginator(bills_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'bills': page_obj,
        'total_returned': bills_list.count(),
    }
    return render(request, 'core/chairman_returned_bills.html', context)

@login_required
@require_POST
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def chairman_return_bill_to_user(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    if bill.status != 'controller_returned':
        messages.error(request, 'শুধুমাত্র কন্ট্রোলার ফেরত বিলই ব্যবহারকারীর কাছে ফেরত পাঠানো যাবে।')
        return redirect('chairman_returned_bills')

    chairman_note = request.POST.get('remarks', '').strip()

    # Change status to 'returned_to_user' (প্রস্তুতকারীর কাছে ফেরত)
    bill.status = 'returned_to_user'
    bill.returned_to_user_at = timezone.now()
    bill.returned_to_user_by = request.user
    
    # HIDE FROM CHAIRMAN - This removes it from all chairman views
    bill.is_hidden_from_chairman = True
    
    # Add chairman's note to remarks
    if chairman_note:
        bill.remarks = (bill.remarks or '') + f"\nচেয়ারম্যান মন্তব্য (ফেরত): {chairman_note}"
    bill.save()

    log_activity(request.user, 'Bill returned to user by chairman',
                f'Bill {bill.bill_number} returned to {bill.user.username} for correction')
    messages.success(request, f'বিল {bill.bill_number} বিল প্রস্তুতকারীর কাছে ফেরত পাঠানো হয়েছে!')

    return redirect('chairman_returned_bills')


@login_required
def bill_counts_api(request):
    if not (hasattr(request.user, 'profile') and
             request.user.profile.user_type == 'কন্ট্রোলার'):
         return JsonResponse({'error': 'Forbidden'}, status=403)
    """API endpoint for bill counts - used by JavaScript notification"""
    from django.db.models import Sum, Count
    all_non_draft = Bill.objects.exclude(status='draft')
    return JsonResponse({
        'total_bills': all_non_draft.count(),
        'pending_count': all_non_draft.filter(status='pending').count(),
        'approved_count': all_non_draft.filter(status='approved').count(),
        'rejected_count': all_non_draft.filter(status='rejected').count(),
        'sent_to_controller_count': Bill.objects.filter(status='sent_to_controller').count(),
    })


@login_required
@require_POST
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def chairman_direct_return_to_user(request, bill_id):
    """Chairman directly returns a bill to the user without controller involvement"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Only pending or approved bills can be returned directly
    if bill.status not in ['pending', 'approved']:
        messages.error(request, 'শুধুমাত্র অপেক্ষমান অথবা অনুমোদিত বিল প্রস্তুতকারীর কাছে ফেরত পাঠানো যাবে।')
        return redirect('all_bills')
    
    chairman_note = request.POST.get('remarks', '').strip()
    
    # STEP 1: First reject the bill
    bill.status = 'rejected'
    bill.approved_by = None
    bill.approved_at = None
    bill.rejected_at = timezone.now()
    bill.rejected_by = request.user
    
    # STEP 2: Then return to user (this will be the final status shown to user)
    bill.status = 'returned_to_user'
    bill.returned_to_user_at = timezone.now()
    bill.returned_to_user_by = request.user
    
    # HIDE FROM CHAIRMAN - This removes it from all chairman views
    bill.is_hidden_from_chairman = True
    
    # Add chairman's note to remarks
    if chairman_note:
        bill.remarks = (bill.remarks or '') + f"\nচেয়ারম্যান কর্তৃক বাতিল (ফেরত): {chairman_note}"
    else:
        bill.remarks = (bill.remarks or '') + f"\nচেয়ারম্যান কর্তৃক বাতিল করা হয়েছে: {timezone.now().strftime('%d-%m-%Y %H:%M')}"
    
    bill.save()
    
    log_activity(request.user, 'Bill rejected and returned to user by chairman',
                f'Bill {bill.bill_number} rejected and returned to {bill.user.username} for correction')
    messages.success(request, f'বিল {bill.bill_number} বাতিল করে প্রস্তুতকারীর কাছে ফেরত পাঠানো হয়েছে!')
    
    return redirect('all_bills')


@login_required
@require_POST
def send_returned_bill(request, bill_id):
    """Send a returned bill directly to chairman without editing"""
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    
    # Only returned_to_user bills can be sent
    if bill.status != 'returned_to_user':
        messages.error(request, 'শুধুমাত্র ফেরত বিল পাঠানো যাবে।')
        return redirect('my_bills')
    
    # Check if signature is added
    if not bill.user_signature_added:
        messages.error(request, 'বিলে আপনার স্বাক্ষর যোগ করা হয়নি। দয়া করে প্রথমে স্বাক্ষর যোগ করুন।')
        return redirect('my_bills')
    
    # Change status to pending (send to chairman)
    bill.status = 'pending'
    bill.sent_at = timezone.now()
    bill.is_hidden_from_chairman = False  # Make it visible to chairman again
    bill.resend_count = (bill.resend_count or 0) + 1
    
    # Add note about resend
    bill.remarks = (bill.remarks or '') + (
        f"\nপুনঃপ্রেরণ ({timezone.now().strftime('%d-%m-%Y %H:%M')}): "
        f"বিল প্রস্তুতকারী সংশোধন করে একই ভাউচার নম্বরে (ভাউচার নং: {bill.voucher_number}) "
        f"পুনরায় চেয়ারম্যানের কাছে পাঠিয়েছেন।"
    )
    bill.save()
    
    log_activity(request.user, 'Returned bill resent', 
                f'Bill {bill.bill_number} resent to chairman for approval')
    messages.success(request, f'বিল {bill.bill_number} সফলভাবে চেয়ারম্যানের কাছে পুনরায় পাঠানো হয়েছে!')
    
    return redirect('my_bills')
