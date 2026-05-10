from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import reverse
import json
from .models import SliderImage, Bill, Task, Profile, ActivityLog, SystemSetting, WorkType, Benefit
from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomPasswordChangeForm, BillForm, BillStatusForm
from .utils import generate_bill_pdf, generate_bill_pdf_download, generate_bill_pdf_view, generate_bill_pdf_chairman


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
    slider_images = SliderImage.objects.filter(is_active=True).order_by('order')
    total_bills = Bill.objects.count()
    total_users = User.objects.count()
    total_amount = Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    from django.conf import settings
    
    # Check if user is authenticated and is Chairman
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.user_type == 'চেয়ারম্যান':
            # For Chairman, use home_c.html
            context = {
                'slider_images': slider_images,
                'total_bills': total_bills,
                'total_users': total_users,
                'total_amount': total_amount,
                'MEDIA_URL': settings.MEDIA_URL,
                'pending_count': Bill.objects.filter(status='pending').count(),
                'approved_count': Bill.objects.filter(status='approved').count(),
                'rejected_count': Bill.objects.filter(status='rejected').count(),
                'paid_count': Bill.objects.filter(status='paid').count(),
            }
            
            # Add year-specific statistics based on username
            if request.user.username == 'JSTUChairman1':
                # 1st Year: 1st and 2nd semesters
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
                # 2nd Year: 3rd and 4th semesters
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
                # 3rd Year: 5th and 6th semesters
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
                # 4th Year: 7th and 8th semesters
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
    
    # For all other users, use home.html
    context = {
        'slider_images': slider_images,
        'total_bills': total_bills,
        'total_users': total_users,
        'total_amount': total_amount,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    return render(request, 'core/home.html', context)
    
    # For all other users, use home.html
    context = {
        'slider_images': slider_images,
        'total_bills': total_bills,
        'total_users': total_users,
        'total_amount': total_amount,
        'MEDIA_URL': settings.MEDIA_URL,
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
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        password_form = CustomPasswordChangeForm(request.user, request.POST)

        if 'profile_update' in request.POST:
            if profile_form.is_valid():
                profile_form.save()
                log_activity(request.user, 'Profile updated', 'User updated their profile')
                messages.success(request, 'আপনার প্রোফাইল সফলভাবে আপডেট করা হয়েছে!')
                return redirect('profile')
        elif 'password_change' in request.POST:
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
    """View user's own bills (drafts and all)"""
    bills_list = Bill.objects.filter(user=request.user).order_by('-created_at')

    paginator = Paginator(bills_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/my_bills.html', {'bills': page_obj})


@login_required
@require_POST
def delete_bill(request, bill_id):
    """Delete a bill with different rules based on user type"""
    bill = get_object_or_404(Bill, id=bill_id)

    is_chairman = request.user.is_authenticated and request.user.profile.user_type == 'চেয়ারম্যান'

    if not is_chairman:
        # Must own the bill
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

        # draft, rejected, approved — all allowed to delete
        bill_number = bill.bill_number
        bill.delete()

        log_activity(request.user, 'Bill deleted', f'Bill {bill_number} permanently deleted')
        messages.success(request, f'বিল {bill_number} স্থায়ীভাবে ডিলিট করা হয়েছে!')

        # Redirect to my_bills if it was a draft, otherwise bill_status
        if bill.status == 'draft':
            return redirect('my_bills')
        return redirect('bill_status')

    else:
        # Chairman logic
        if bill.status == 'pending':
            messages.error(request, 'অপেক্ষমান বিল ডিলিট করা যাবে না।')
            return redirect('all_bills')
        elif bill.status == 'paid':
            messages.error(request, 'পরিশোধিত বিল ডিলিট করা যাবে না।')
            return redirect('all_bills')

        bill.is_hidden_from_chairman = True
        bill.save()

        log_activity(request.user, 'Bill hidden from chairman',
                    f'Bill {bill.bill_number} hidden from chairman view')
        messages.success(request, f'বিল {bill.bill_number} চেয়ারম্যানের প্যানেল থেকে মুছে ফেলা হয়েছে।')
        return redirect('all_bills')


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
    if request.user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']:
        bills_list = Bill.objects.exclude(status='draft').exclude(is_hidden_from_chairman=True).order_by('-created_at')
    else:
        bills_list = Bill.objects.filter(user=request.user).exclude(status='draft').order_by('-created_at')

    if request.user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']:
        pending_count = Bill.objects.exclude(is_hidden_from_chairman=True).filter(status='pending').count()
        approved_count = Bill.objects.exclude(is_hidden_from_chairman=True).filter(status='approved').count()
        rejected_count = Bill.objects.exclude(is_hidden_from_chairman=True).filter(status='rejected').count()
        paid_count = Bill.objects.exclude(is_hidden_from_chairman=True).filter(status='paid').count()
    else:
        pending_count = Bill.objects.filter(user=request.user, status='pending').count()
        approved_count = Bill.objects.filter(user=request.user, status='approved').count()
        rejected_count = Bill.objects.filter(user=request.user, status='rejected').count()
        paid_count = Bill.objects.filter(user=request.user, status='paid').count()

    status_filter = request.GET.get('status', '')
    if status_filter:
        bills_list = bills_list.filter(status=status_filter)

    paginator = Paginator(bills_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'bills': page_obj,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'paid_count': paid_count,
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
    """Add user's signature to bill - Only for draft bills"""
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    
    # Only draft bills can have signature added
    if bill.status != 'draft':
        messages.error(request, 'শুধুমাত্র খসড়া বিলে স্বাক্ষর যোগ করা যাবে।')
        return redirect('my_bills')
    
    # Check if signature is already added
    if bill.user_signature_added:
        messages.warning(request, 'এই বিলে ইতিমধ্যে আপনার স্বাক্ষর যুক্ত হয়েছে।')
        return redirect('my_bills')
    
    if request.user.profile.signature_general:
        # Mark signature as added
        bill.user_signature_added = True
        signature_note = f"\nস্বাক্ষর যুক্ত: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')}"
        bill.remarks = (bill.remarks or '') + signature_note
        bill.save()
        
        log_activity(request.user, 'Signature added to bill', 
                    f'User signature added to bill {bill.bill_number}')
        messages.success(request, f'বিল {bill.bill_number} এ আপনার স্বাক্ষর সফলভাবে যুক্ত হয়েছে!')
    else:
        messages.error(request, 'আপনার স্বাক্ষর আপলোড করা হয়নি। দয়া করে প্রথমে স্বাক্ষর আপলোড করুন।')
        return redirect('signature_upload_general')
    
    return redirect('my_bills')


# --------------------------
# Admin Views
# --------------------------

@login_required
@user_passes_test(is_admin)
def all_bills(request):
    """View all bills for chairman - filters bills assigned to specific chairman"""
    chairman_username = request.user.username
    
    year_map = {
        'JSTUChairman1': '১ম বর্ষ',
        'JSTUChairman2': '২য় বর্ষ',
        'JSTUChairman3': '৩য় বর্ষ',
        'JSTUChairman4': '৪র্থ বর্ষ',
    }
    
    year_text = year_map.get(chairman_username, '')
    
    if year_text:
        bills = Bill.objects.exclude(status='draft').exclude(is_hidden_from_chairman=True).filter(
            remarks__icontains=year_text
        ).order_by('-sent_at', '-created_at')
    else:
        bills = Bill.objects.exclude(status='draft').exclude(is_hidden_from_chairman=True).order_by('-sent_at', '-created_at')
    
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')

    if status_filter:
        bills = bills.filter(status=status_filter)
    if user_filter:
        bills = bills.filter(user__username__icontains=user_filter)

    paginator = Paginator(bills, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_bills = bills.count()
    pending_count = bills.filter(status='pending').count()
    approved_count = bills.filter(status='approved').count()
    rejected_count = bills.filter(status='rejected').count()
    paid_count = bills.filter(status='paid').count()

    context = {
        'bills': page_obj,
        'status_filter': status_filter,
        'user_filter': user_filter,
        'total_bills': total_bills,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'paid_count': paid_count,
    }
    return render(request, 'core/all_bills.html', context)


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
    """Add chairman's signature to approved bill based on chairman type"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if bill.status != 'approved':
        messages.error(request, 'শুধুমাত্র অনুমোদিত বিলে স্বাক্ষর যোগ করা যাবে।')
        return redirect('all_bills')
    
    # Check if signature is already added
    if bill.chairman_signature_added:
        messages.warning(request, 'এই বিলে ইতিমধ্যে চেয়ারম্যানের স্বাক্ষর যুক্ত হয়েছে।')
        return redirect('all_bills')
    
    if request.method == 'POST':
        chairman_username = request.user.username
        signature_added = False
        
        if chairman_username == 'JSTUChairman1' and request.user.profile.signature_chairman1:
            signature_added = True
        elif chairman_username == 'JSTUChairman2' and request.user.profile.signature_chairman2:
            signature_added = True
        elif chairman_username == 'JSTUChairman3' and request.user.profile.signature_chairman3:
            signature_added = True
        elif chairman_username == 'JSTUChairman4' and request.user.profile.signature_chairman4:
            signature_added = True
        
        if signature_added:
            bill.chairman_signature_added = True
            signature_note = f"\nচেয়ারম্যানের স্বাক্ষর যুক্ত: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')} ({chairman_username})"
            bill.remarks = (bill.remarks or '') + signature_note
            bill.save()
            
            log_activity(request.user, 'Signature added to bill', 
                        f'Chairman signature added to bill {bill.bill_number}')
            messages.success(request, f'বিল {bill.bill_number} এ আপনার স্বাক্ষর সফলভাবে যুক্ত হয়েছে!')
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
            work_type = WorkType.objects.get(
                name=work_type_name,
                degree_type=degree_type,
                is_active=True
            )

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
        work_type = WorkType.objects.get(
            name=work_type_name,
            degree_type=degree_type,
            is_active=True
        )
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






# admin----------------------------------------------------------------
# ---------------------------------------------------------------------
from django.contrib.admin.views.decorators import staff_member_required
from .models import ActivityLog, Bill

@staff_member_required
def admin_dashboard(request):
    """Custom admin dashboard view"""
    from django.db.models import Sum, Count
    
    context = {
        'total_bills': Bill.objects.count(),
        'pending_bills': Bill.objects.filter(status='pending').count(),
        'approved_bills': Bill.objects.filter(status='approved').count(),
        'rejected_bills': Bill.objects.filter(status='rejected').count(),
        'paid_bills': Bill.objects.filter(status='paid').count(),
        'total_amount': Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'recent_activities': ActivityLog.objects.select_related('user').order_by('-created_at')[:10],
        'recent_bills': Bill.objects.select_related('user').order_by('-created_at')[:5],
    }
    return render(request, 'admin/index.html', context)

import json


@login_required
def edit_bill(request, bill_id):
    """Edit an existing bill"""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Check permission
    if bill.user != request.user:
        messages.error(request, 'আপনার এই বিল এডিট করার অনুমতি নেই।')
        return redirect('my_bills')
    
    # Only draft or rejected bills can be edited
    if bill.status not in ['draft', 'rejected']:
        messages.error(request, 'শুধুমাত্র খসড়া বা বাতিলকৃত বিল এডিট করা যাবে।')
        return redirect('my_bills')
    
    if request.method == 'POST':
        form = BillForm(request.POST, instance=bill)
        action = request.POST.get('action', 'save')
        
        if form.is_valid():
            bill = form.save(commit=False)
            
            if action == 'send':
                bill.status = 'pending'
                bill.sent_at = timezone.now()
                success_message = 'বিল সফলভাবে আপডেট এবং পাঠানো হয়েছে!'
                redirect_url = 'bill_status'
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
