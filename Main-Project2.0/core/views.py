from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.contrib.auth.models import User
import json
from .models import SliderImage, Bill, Task, Profile, ActivityLog, SystemSetting, WorkType, Benefit
from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomPasswordChangeForm, BillForm, BillStatusForm
from .utils import generate_bill_pdf
from django.core.paginator import Paginator


def is_admin(user):
    return user.is_authenticated and user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী']


def log_activity(user, action, details='', ip_address=None):
    ActivityLog.objects.create(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address
    )


def home(request):
    slider_images = SliderImage.objects.filter(is_active=True).order_by('order')
    total_bills = Bill.objects.count()
    total_users = User.objects.count()
    total_amount = Bill.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    from django.conf import settings
    context = {
        'slider_images': slider_images,
        'total_bills': total_bills,
        'total_users': total_users,
        'total_amount': total_amount,
        'MEDIA_URL': settings.MEDIA_URL,
    }

    return render(request, 'core/home.html', context)


def register(request):
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


@login_required
def profile(request):
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


@login_required
def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.user = request.user
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
                    amount=task_data['amount']
                )
                task.save()
                total_amount += float(task_data['amount'])

            bill.total_amount = total_amount
            bill.save()

            log_activity(request.user, 'Bill created', f'Bill {bill.bill_number} created with {len(tasks_data)} tasks')
            messages.success(request, 'বিল সফলভাবে তৈরি হয়েছে!')
            return redirect('my_bills')
    else:
        form = BillForm()

    return render(request, 'core/bill_create.html', {'form': form})


@login_required
def my_bills(request):
    bills_list = Bill.objects.filter(user=request.user).order_by('-created_at')

    paginator = Paginator(bills_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/my_bills.html', {'bills': page_obj})


@login_required
@require_POST
def delete_bill(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id, user=request.user)
    bill_number = bill.bill_number
    bill.delete()
    log_activity(request.user, 'Bill deleted', f'Bill {bill_number} deleted')
    messages.success(request, 'বিল সফলভাবে ডিলিট করা হয়েছে!')
    return redirect('my_bills')


@login_required
def download_bill_pdf(request, bill_id):
    try:
        bill = get_object_or_404(Bill, id=bill_id)
        if bill.user != request.user and not is_admin(request.user):
            messages.error(request, 'আপনার এই বিল ডাউনলোড করার অনুমতি নেই।')
            return redirect('my_bills')

        response = generate_bill_pdf(bill)
        if response.status_code == 500:
            messages.error(request, 'পিডিএফ জেনারেট করতে সমস্যা হচ্ছে। দয়া করে আবার চেষ্টা করুন।')
            return redirect('my_bills')

        log_activity(request.user, 'Bill downloaded', f'Bill {bill.bill_number} downloaded as PDF')
        return response

    except Exception as e:
        messages.error(request, f'পিডিএফ ডাউনলোড করতে সমস্যা হচ্ছে: {str(e)}')
        return redirect('my_bills')


@login_required
def view_bill_pdf(request, bill_id):
    try:
        bill = get_object_or_404(Bill, id=bill_id)
        if bill.user != request.user and not is_admin(request.user):
            messages.error(request, 'আপনার এই বিল দেখার অনুমতি নেই।')
            return redirect('my_bills')

        response = generate_bill_pdf(bill)
        if response.status_code == 500:
            messages.error(request, 'পিডিএফ দেখাতে সমস্যা হচ্ছে। দয়া করে আবার চেষ্টা করুন।')
            return redirect('my_bills')

        response['Content-Disposition'] = f'inline; filename="bill_{bill.bill_number}.pdf"'
        log_activity(request.user, 'Bill viewed', f'Bill {bill.bill_number} viewed in browser')
        return response

    except Exception as e:
        messages.error(request, f'পিডিএফ দেখাতে সমস্যা হচ্ছে: {str(e)}')
        return redirect('my_bills')


from django.contrib.auth import logout


def custom_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'আপনি সফলভাবে লগআউট হয়েছেন!')
        return redirect('home')
    else:
        return render(request, 'core/logout_confirm.html')


@login_required
@user_passes_test(is_admin)
def all_bills(request):
    bills = Bill.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')

    if status_filter:
        bills = bills.filter(status=status_filter)
    if user_filter:
        bills = bills.filter(user__username__icontains=user_filter)

    paginator = Paginator(bills, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'bills': page_obj,
        'status_filter': status_filter,
        'user_filter': user_filter,
    }
    return render(request, 'core/all_bills.html', context)


@login_required
@user_passes_test(is_admin)
def update_bill_status(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    if request.method == 'POST':
        form = BillStatusForm(request.POST, instance=bill)
        if form.is_valid():
            bill = form.save(commit=False)
            if bill.status == 'approved' and not bill.approved_by:
                bill.approved_by = request.user
                bill.approved_at = timezone.now()
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
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    return render(request, 'core/user_management.html', {'users': users})


def get_benefit_choices_old(request):
    work_type = request.GET.get('work_type')
    benefits = Bill.BENEFIT_CHOICES.get(work_type, [])
    return JsonResponse({'benefits': benefits})


def get_amount_old(request):
    benefit = request.GET.get('benefit')
    amount = Bill.AMOUNT_MAPPING.get(benefit, 0)

    english_to_bangla = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
    bangla_amount = str(int(amount)).translate(english_to_bangla)

    return JsonResponse({'amount': amount, 'bangla_amount': bangla_amount})


def handler404(request, exception):
    return render(request, 'core/404.html', status=404)


def handler500(request):
    return render(request, 'core/500.html', status=500)


@login_required
@user_passes_test(is_admin)
def work_type_management(request):
    work_types = WorkType.objects.all()

    if request.method == 'POST':
        if 'add_work_type' in request.POST:
            name = request.POST.get('name')
            description = request.POST.get('description')
            needs_benefit = 'needs_benefit' in request.POST
            default_amount = request.POST.get('default_amount', 0)

            if name:
                WorkType.objects.create(
                    name=name,
                    description=description,
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


def get_work_types(request):
    work_types = WorkType.objects.filter(is_active=True).order_by('order')
    work_type_list = [(wt.name, wt.name) for wt in work_types]
    return JsonResponse({'work_types': work_type_list})


def get_work_type_amount(request):
    work_type_name = request.GET.get('work_type')

    try:
        work_type = WorkType.objects.get(name=work_type_name, is_active=True)
        if not work_type.needs_benefit:
            return JsonResponse({'amount': float(work_type.default_amount)})
        else:
            return JsonResponse({'amount': 0})
    except WorkType.DoesNotExist:
        return JsonResponse({'amount': 0})


def get_work_type_details(request):
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
    """Get calculation details for a benefit"""
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