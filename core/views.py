from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, update_session_auth_hash, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q, Sum, Count, Case, When, IntegerField
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import reverse
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime
from .models import (SliderImage, Bill, Task, Profile, ActivityLog, SystemSetting,
                     WorkType, Benefit, ChairmanDocument, Department, TaxSetting)
from .forms import CustomUserCreationForm, ProfileUpdateForm, CustomPasswordChangeForm, BillForm, BillStatusForm, ChairmanDocumentForm
from .utils import (
    generate_bill_pdf, generate_bill_pdf_download, generate_bill_pdf_view, generate_bill_pdf_chairman,
    render_bills_report_pdf, render_accepted_summary_pdf,
    convert_to_bangla_digits, format_bangla_number,
)


# --------------------------
# Helper Functions
# --------------------------

def is_chairman(user):
    """Chairman by role.

    Deliberately not tied to any username: with several departments there are
    many chairmen, and which academic year each one serves comes from
    profile.chairman_year.
    """
    return (user.is_authenticated and hasattr(user, 'profile')
            and user.profile.user_type == 'চেয়ারম্যান')


def is_admin(user):
    """Check if user has admin privileges"""
    return user.is_authenticated and user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']


# Legacy 1st..8th semester values that belong to each academic year, so counts
# and filters still see bills created before the year/semester split.
# Bengali year label -> the suffix used in the dashboard context keys
BENGALI_MONTHS = ['জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
                  'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর']

YEAR_SUFFIX = {'১ম বর্ষ': '1st', '২য় বর্ষ': '2nd', '৩য় বর্ষ': '3rd',
               '৪র্থ বর্ষ': '4th', 'মাস্টার্স': 'masters'}

# Sections shown on the controller's bills page, in order.
CONTROLLER_YEAR_GROUPS = [
    ('1st', '১ম বর্ষ', '1st Year', 'year-1'),
    ('2nd', '২য় বর্ষ', '2nd Year', 'year-2'),
    ('3rd', '৩য় বর্ষ', '3rd Year', 'year-3'),
    ('4th', '৪র্থ বর্ষ', '4th Year', 'year-4'),
    ('masters', 'মাস্টার্স', 'Masters', 'year-5'),
]


def bill_year_suffix(bill):
    """'1st'..'4th' for a bill, or '' when the year is unknown.

    Reads the academic_year field (falling back to the legacy semester) rather
    than scanning bill.remarks for a chairman username, which broke as soon as
    more than one department had a chairman for the same year.
    """
    return YEAR_SUFFIX.get(bill.resolved_academic_year or '', '')


LEGACY_SEMESTERS_BY_YEAR = {
    '১ম বর্ষ': ['১ম সেমিস্টার', '২য় সেমিস্টার'],
    '২য় বর্ষ': ['৩য় সেমিস্টার', '৪র্থ সেমিস্টার'],
    '৩য় বর্ষ': ['৫ম সেমিস্টার', '৬ষ্ঠ সেমিস্টার'],
    '৪র্থ বর্ষ': ['৭ম সেমিস্টার', '৮ম সেমিস্টার'],
    'মাস্টার্স': ['মাস্টার্স'],
}


def year_bills_q(year_label):
    """Q() matching bills in an academic year, new field or legacy value."""
    return (Q(academic_year=year_label) |
            Q(academic_year__isnull=True,
              semester__in=LEGACY_SEMESTERS_BY_YEAR.get(year_label, [])))


def user_department(user):
    """The department a user belongs to, or None if none is set."""
    profile = getattr(user, 'profile', None)
    return profile.department if profile and profile.department_id else None


def scope_to_department(queryset, user):
    """Limit a Bill queryset to the user's own department.

    Applied to chairman-facing views: an exam committee chairman approves
    bills for their own department, not the whole university. The controller
    is deliberately NOT scoped - Controller of Examinations is a
    university-wide office - and gets a department filter instead.

    A user with no department set sees nothing rather than everything, so a
    half-configured account can't quietly leak another department's bills.
    """
    dept = user_department(user)
    if dept is None:
        return queryset.none()
    return queryset.filter(department=dept)


def scope_bills_for_role(queryset, user):
    """Department scoping that depends on the role.

    Chairman and office assistant work inside one department, so they only
    ever see their own. The controller is university-wide and sees every
    department, with a filter to narrow it down instead.
    """
    profile = getattr(user, 'profile', None)
    if profile and profile.user_type == 'কন্ট্রোলার':
        return queryset
    return scope_to_department(queryset, user)


def department_work_types_q(user):
    """Work types available to a user: shared ones plus their department's.

    A WorkType with department=NULL applies everywhere, which is how all the
    existing work types are stored, so nothing changes for a single-department
    setup. Setting a department makes that work type exclusive to it.
    """
    dept = user_department(user)
    if dept is None:
        return Q(department__isnull=True)
    return Q(department__isnull=True) | Q(department=dept)



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

# Statuses a bill can only hold once the chairman has forwarded it, i.e. the
# controller's own workload. Anything before this is still with the chairman.
CONTROLLER_STATUSES = [
    'sent_to_controller',
    'approved_by_controller',
    'rejected_by_controller',
    'controller_returned',
    'paid',
]


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

            # Counts are scoped to the bills that actually reached the
            # controller. Counting every non-draft bill made the panel claim
            # bills that are still sitting with a chairman.
            reached = Bill.objects.filter(status__in=CONTROLLER_STATUSES)

            pending_count = reached.filter(status='sent_to_controller').count()   # awaiting the controller
            approved_count = reached.filter(status='approved_by_controller').count()
            rejected_count = reached.filter(status='rejected_by_controller').count()
            paid_count = reached.filter(status='paid').count()
            sent_to_controller_count = pending_count

            con_total = reached.count()
            con_amount = reached.aggregate(total=Sum('total_amount'))['total'] or 0

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
            dept_bills = scope_to_department(Bill.objects.all(), request.user)
            context = {
                'slider_images': slider_images,
                'total_bills':   total_bills,
                'total_users':   total_users,
                'total_amount':  total_amount,
                'MEDIA_URL':     settings.MEDIA_URL,
                'pending_count':  dept_bills.filter(status='pending').count(),
                'approved_count': dept_bills.filter(status='approved').count(),
                'rejected_count': dept_bills.filter(status='rejected').count(),
                'paid_count':     dept_bills.filter(status='paid').count(),
                'controller_returned_count': dept_bills.filter(status='controller_returned').count(),
                'user_department': user_department(request.user),
            }
 
            # Each chairman account owns one academic year. The counts below
            # used to be ~130 lines of Q(semester__icontains=...) chains; the
            # explicit academic_year field makes that a single helper call,
            # and year_bills_q() still matches pre-split bills via their
            # legacy semester value.
            # The chairman's year is stored on their profile, so any number of
            # chairmen can exist across departments.
            year_label = getattr(request.user.profile, 'chairman_year', None)
            suffix = YEAR_SUFFIX.get(year_label)

            if year_label and suffix:
                year_q = year_bills_q(year_label)
                # Counts are limited to the chairman's own department
                own = scope_to_department(Bill.objects.all(), request.user)
                context[f'total_bills_{suffix}_year'] = own.filter(year_q).count()
                for status in ('pending', 'approved', 'rejected', 'paid'):
                    context[f'{status}_bills_{suffix}_year'] = own.filter(
                        year_q, status=status
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
    """User profile management: details, picture, and password.

    Two independent forms POST to this one view and are told apart by a hidden
    marker field. Whichever one was submitted keeps its bound data (and errors)
    on re-render; the other is rebuilt clean so it does not show stale errors.
    """
    profile_obj = request.user.profile
    profile_form = None
    password_form = None
    active_panel = 'profile'

    if request.method == 'POST' and 'profile_update' in request.POST:
        active_panel = 'profile'
        profile_form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile_obj,
        )
        if profile_form.is_valid():
            # User and Profile are written together, so a failure on either
            # one cannot leave the account half-updated.
            with transaction.atomic():
                profile_form.save()
            log_activity(request.user, 'Profile updated', 'User updated their profile')
            messages.success(request, 'আপনার প্রোফাইল সফলভাবে আপডেট করা হয়েছে!')
            return redirect('profile')
        messages.error(request, 'দয়া করে নিচের ভুলগুলো ঠিক করুন।')

    elif request.method == 'POST' and 'password_change' in request.POST:
        active_panel = 'password'
        password_form = CustomPasswordChangeForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            log_activity(request.user, 'Password changed', 'User changed their password')
            messages.success(request, 'আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন করা হয়েছে!')
            return redirect('profile')
        messages.error(request, 'পাসওয়ার্ড পরিবর্তন করা যায়নি। দয়া করে নিচের ভুলগুলো ঠিক করুন।')

    # Unbound instances for whichever form was not submitted
    if profile_form is None:
        profile_form = ProfileUpdateForm(instance=profile_obj)
    if password_form is None:
        password_form = CustomPasswordChangeForm(request.user)

    # Last five months of the user's own activity, for the two charts on the
    # profile page. Computed here rather than in the template so the bar
    # heights are plain numbers the template just prints.
    today = timezone.now()
    months = []
    year, month = today.year, today.month
    for _ in range(5):
        months.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    months.reverse()

    own_bills = Bill.objects.filter(user=request.user)
    count_points, amount_points = [], []
    for year, month in months:
        in_month = own_bills.filter(created_at__year=year, created_at__month=month)
        count = in_month.count()
        amount = in_month.aggregate(total=Sum('total_amount'))['total'] or 0
        label = BENGALI_MONTHS[month - 1]
        count_points.append({'label': label, 'value': count})
        amount_points.append({'label': label, 'value': float(amount)})

    max_count = max((p['value'] for p in count_points), default=0)
    max_amount = max((p['value'] for p in amount_points), default=0)
    for point in count_points:
        point['height'] = round(point['value'] / max_count * 100) if max_count else 0
        point['display'] = convert_to_bangla_digits(point['value'])
    for point in amount_points:
        point['height'] = round(point['value'] / max_amount * 100) if max_amount else 0
        point['display'] = convert_to_bangla_digits(f'{point["value"]:,.0f}')

    # Signature slots this user can actually reach.

    #
    # Every user gets a general signature. A chairman additionally gets one
    # chairman signature, for whichever year their profile says they serve --
    # no longer four numbered slots tied to four fixed usernames.
    signature_slots = [{
        'label': 'আপনার স্বাক্ষর',
        'file': profile_obj.signature_general,
        'upload_url': 'signature_upload_general',
    }]

    if profile_obj.is_chairman:
        year = profile_obj.chairman_year
        signature_slots.append({
            'label': f'{year} চেয়ারম্যান' if year else 'চেয়ারম্যান স্বাক্ষর',
            'file': profile_obj.active_chairman_signature,
            'upload_url': 'signature_upload_chairman',
        })

    # The controller does not create bills, so the personal charts above mean
    # nothing to them. They get their own review summary for the current month
    # instead: how the month's decisions split, and which departments are
    # sending the most work through.
    controller_charts = None
    if is_controller(request.user):
        month_bills = Bill.objects.filter(
            controller_approved_at__year=today.year,
            controller_approved_at__month=today.month,
        )
        accepted = month_bills.filter(status='approved_by_controller').count()
        rejected = month_bills.filter(status='rejected_by_controller').count()
        decided = accepted + rejected

        # conic-gradient needs the accepted share as a percentage
        accepted_pct = round(accepted / decided * 100, 1) if decided else 0

        top_departments = list(
            month_bills.filter(status='approved_by_controller')
            .exclude(department__isnull=True)
            .values('department__name', 'department__short_name')
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )
        busiest = max((d['total'] for d in top_departments), default=0)
        department_points = [{
            'label': d['department__short_name'] or d['department__name'],
            'title': d['department__name'],
            'value': d['total'],
            'display': convert_to_bangla_digits(d['total']),
            'height': round(d['total'] / busiest * 100) if busiest else 0,
        } for d in top_departments]

        controller_charts = {
            'month_label': BENGALI_MONTHS[today.month - 1],
            'accepted': accepted,
            'rejected': rejected,
            'decided': decided,
            'accepted_display': convert_to_bangla_digits(accepted),
            'rejected_display': convert_to_bangla_digits(rejected),
            'decided_display': convert_to_bangla_digits(decided),
            'accepted_pct': accepted_pct,
            'accepted_pct_display': convert_to_bangla_digits(f'{accepted_pct:g}'),
            'rejected_pct_display': convert_to_bangla_digits(
                f'{round(100 - accepted_pct, 1):g}') if decided else convert_to_bangla_digits(0),
            'departments': department_points,
        }

    # A chairman receives bills and forwards them; the personal "bills I
    # created" charts are meaningless for them too. They get the outcome of
    # what they forwarded, plus how much work is arriving.
    chairman_charts = None
    if profile_obj.is_chairman:
        scoped = scope_bills_for_role(Bill.objects.all(), request.user)
        if profile_obj.chairman_year:
            scoped = scoped.filter(year_bills_q(profile_obj.chairman_year))

        # Same five-month window as the bar chart below, so both agree
        first_year, first_month = months[0]
        window_start = timezone.make_aware(datetime(first_year, first_month, 1)) \
            if timezone.is_aware(today) else datetime(first_year, first_month, 1)

        decided_qs = scoped.filter(controller_approved_at__gte=window_start)
        ch_accepted = decided_qs.filter(status='approved_by_controller').count()
        ch_rejected = decided_qs.filter(status='rejected_by_controller').count()
        ch_decided = ch_accepted + ch_rejected
        ch_pct = round(ch_accepted / ch_decided * 100, 1) if ch_decided else 0

        # Bills users have sent up to this chairman, month by month
        received_points = []
        for year, month in months:
            received = scoped.filter(sent_at__year=year, sent_at__month=month).count()
            received_points.append({
                'label': BENGALI_MONTHS[month - 1],
                'value': received,
                'display': convert_to_bangla_digits(received),
            })
        busiest_month = max((p['value'] for p in received_points), default=0)
        for point in received_points:
            point['height'] = round(point['value'] / busiest_month * 100) if busiest_month else 0

        chairman_charts = {
            'accepted': ch_accepted,
            'rejected': ch_rejected,
            'decided': ch_decided,
            'accepted_display': convert_to_bangla_digits(ch_accepted),
            'rejected_display': convert_to_bangla_digits(ch_rejected),
            'decided_display': convert_to_bangla_digits(ch_decided),
            'accepted_pct': ch_pct,
            'accepted_pct_display': convert_to_bangla_digits(f'{ch_pct:g}'),
            'rejected_pct_display': convert_to_bangla_digits(
                f'{round(100 - ch_pct, 1):g}') if ch_decided else convert_to_bangla_digits(0),
            'received': received_points,
            'received_total': convert_to_bangla_digits(
                sum(p['value'] for p in received_points)),
        }

    context = {

        'profile_form': profile_form,
        'password_form': password_form,
        'profile_obj': profile_obj,
        'signature_slots': signature_slots,
        'active_panel': active_panel,
        'controller_charts': controller_charts,
        'chairman_charts': chairman_charts,
        'bill_count_chart': count_points,
        'bill_amount_chart': amount_points,
        'bill_count_total': convert_to_bangla_digits(sum(p['value'] for p in count_points)),
        'bill_amount_total': convert_to_bangla_digits(f"{sum(p['value'] for p in amount_points):,.0f}"),
    }
    return render(request, 'core/profile.html', context)


# --------------------------
# Profile picture (saved immediately, independent of the details form)
# --------------------------

PROFILE_PICTURE_TYPES = ('image/jpeg', 'image/jpg', 'image/png', 'image/webp')
PROFILE_PICTURE_MAX_MB = 2


@login_required
@require_POST
def profile_picture_upload(request):
    """Store a new profile picture and return the new URL as JSON.

    Deliberately separate from the details form. Previously the picture was
    only written when the whole form was submitted, so choosing an image and
    then navigating away silently discarded it. Saving on selection means the
    camera button always sticks, and it cannot wipe unsaved edits to the name
    or phone fields either.
    """
    upload = request.FILES.get('profile_picture')
    if not upload:
        return JsonResponse({'ok': False, 'error': 'কোনো ছবি পাওয়া যায়নি।'}, status=400)

    if getattr(upload, 'content_type', '') not in PROFILE_PICTURE_TYPES:
        return JsonResponse(
            {'ok': False, 'error': 'শুধুমাত্র JPEG, PNG অথবা WebP ছবি আপলোড করুন।'}, status=400)

    if upload.size > PROFILE_PICTURE_MAX_MB * 1024 * 1024:
        return JsonResponse(
            {'ok': False, 'error': f'ছবির সাইজ {PROFILE_PICTURE_MAX_MB}MB এর কম হতে হবে।'},
            status=400)

    profile = request.user.profile
    if profile.profile_picture:
        profile.profile_picture.delete(save=False)
    profile.profile_picture = upload
    profile.save()

    log_activity(request.user, 'Profile picture updated', 'User changed their profile picture')
    return JsonResponse({
        'ok': True,
        'url': profile.profile_picture.url,
        'message': 'প্রোফাইল ছবি আপডেট করা হয়েছে।',
    })


@login_required
@require_POST
def profile_picture_delete(request):
    """Remove the current profile picture; the initials avatar takes over."""
    profile = request.user.profile
    if not profile.profile_picture:
        return JsonResponse({'ok': False, 'error': 'কোনো ছবি নেই।'}, status=400)

    profile.profile_picture.delete(save=False)
    profile.profile_picture = None
    profile.save()

    log_activity(request.user, 'Profile picture removed', 'User removed their profile picture')
    return JsonResponse({
        'ok': True,
        'initials': profile.initials,
        'message': 'প্রোফাইল ছবি মুছে ফেলা হয়েছে।',
    })


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
            # A bill belongs to the department of whoever created it
            bill.department = user_department(request.user)

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

    return render(request, 'core/bill_create.html', {
        'form': form,
        'user_department': user_department(request.user),
    })


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
    """Bill status page with per-status counts.

    Admin-role users see the bills they are responsible for; everyone else
    sees their own. Crucially this now goes through scope_bills_for_role, so a
    chairman or office assistant only sees their own department. Before the
    multi-department change this returned every bill in the system, which
    would have leaked one department's bills to another.
    """
    is_admin_role = request.user.profile.user_type in ['চেয়ারম্যান', 'অফিস সহকারী', 'কন্ট্রোলার']

    if is_admin_role:
        visible = scope_bills_for_role(
            Bill.objects.exclude(is_hidden_from_chairman=True), request.user)
    else:
        visible = Bill.objects.filter(user=request.user)

    # Free-text search. Applied before the counts are taken so the filter
    # buttons can never advertise more bills than the search actually shows.
    search_query = request.GET.get('q', '').strip()
    if search_query:
        # Bill numbers are stored with English digits but rendered in Bengali,
        # so a term copied off the page has to be normalised before matching.
        term = search_query.translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
        lookup = (
            Q(bill_number__icontains=term)
            | Q(controller_bill_number__icontains=term)
            | Q(voucher_number__icontains=term)
            | Q(bangla_date__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(department__name__icontains=search_query)
            | Q(academic_year__icontains=search_query)
            | Q(exam_semester__icontains=search_query)
            | Q(semester__icontains=search_query)
        )
        if term.replace('.', '', 1).isdigit():
            lookup |= Q(total_amount__icontains=term)
            lookup |= Q(session__start_year__icontains=term)
            lookup |= Q(session__end_year__icontains=term)
        visible = visible.filter(lookup).distinct()

    bills_list = visible.exclude(status='draft').order_by('-created_at')

    # Counts come off the same queryset, so they can never disagree with the list
    def count(status):
        return visible.filter(status=status).count()

    pending_count = count('pending')
    approved_count = count('approved')
    rejected_count = count('rejected')
    paid_count = count('paid')
    approved_by_controller_count = count('approved_by_controller')
    rejected_by_controller_count = count('rejected_by_controller')
    controller_returned_count = count('controller_returned')
    returned_to_user_count = count('returned_to_user')
    sent_to_controller_count = count('sent_to_controller')

    status_filter = request.GET.get('status', '')
    if status_filter:
        bills_list = bills_list.filter(status=status_filter)

    result_count = bills_list.count()

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
        'search_query': search_query,
        'result_count': result_count,
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
    
    year_text = {'1st': '১ম বর্ষ', '2nd': '২য় বর্ষ',
                 '3rd': '৩য় বর্ষ', '4th': '৪র্থ বর্ষ'}.get(selected_year)

    if not year_text:
        messages.error(request, 'অবৈধ বর্ষ নির্বাচন।')
        return redirect('my_bills')

    # Keep the bill's own year in step with what was chosen, then resolve the
    # chairman by year AND department rather than a hardcoded username.
    if bill.academic_year != year_text:
        bill.academic_year = year_text

    bill.status = 'pending'
    bill.sent_at = timezone.now()

    chairman = bill.chairman
    if chairman is None:
        dept_name = bill.department.name if bill.department_id else 'আপনার বিভাগ'
        messages.error(
            request,
            f'{dept_name}-এ {year_text}-এর জন্য কোনো চেয়ারম্যান নির্ধারণ করা নেই। '
            'অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।')
        return redirect('my_bills')

    bill.remarks = f"বর্ষ: {year_text} | চেয়ারম্যান: {chairman.username} | {bill.remarks or ''}"
    bill.save()

    log_activity(request.user, 'Bill sent',
                 f'Bill {bill.bill_number} sent to {chairman.username} ({year_text})')
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
    # Which year this chairman handles now comes from their profile.
    year_text = getattr(request.user.profile, 'chairman_year', '') or ''

    if year_text:
        bills = Bill.objects.exclude(status='draft').exclude(
            is_hidden_from_chairman=True
        ).exclude(
            status='returned_to_user'  # Exclude returned_to_user bills
        ).filter(
            # academic_year is an explicit field now; year_bills_q also matches
            # bills created before the year/semester split.
            year_bills_q(year_text)
        ).select_related('user').order_by('-sent_at', '-created_at')
    else:
        bills = Bill.objects.exclude(status='draft').exclude(
            is_hidden_from_chairman=True
        ).exclude(
            status='returned_to_user'  # Exclude returned_to_user bills
        ).select_related('user').order_by('-sent_at', '-created_at')

    # A chairman whose year has not been assigned yet sees nothing rather than
    # every bill in the department -- same fail-closed rule used for a user
    # with no department. Office assistants and the controller have no year by
    # design, so this only applies to the chairman role.
    if is_chairman(request.user) and not year_text:
        return bills.none()

    # Chairman/office assistant see only their own department;
    # the controller is university-wide.
    return scope_bills_for_role(bills, request.user)


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
        # The dropdown now offers academic years; year_bills_q also
        # catches bills created before the year/semester split.
        bills = bills.filter(year_bills_q(semester_filter))
    if degree_filter:
        bills = bills.filter(degree_type=degree_filter)
    if department_filter:
        # department is a FK now, so match on its name
        bills = bills.filter(department__name__icontains=department_filter)
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
        'semester_choices': Bill.ACADEMIC_YEAR_CHOICES,
        'department_choices': Department.objects.filter(is_active=True),
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
@user_passes_test(is_chairman)
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
        profile = request.user.profile
        # One signature per chairman, whichever year and department they serve
        signature_added = bool(profile.active_chairman_signature)
        
        if signature_added:
            # Mark signature as added - THIS FLAG MAKES THE SIGNATURE PERMANENT
            bill.chairman_signature_added = True
            
            # Also store the chairman username in a dedicated field for easier lookup
            # (You may want to add a chairman_username field to Bill model)
            # For now, store it clearly in remarks
            year_text = profile.chairman_year or ''
            
            signature_note = f"\nচেয়ারম্যানের স্বাক্ষর যুক্ত: {timezone.now().strftime('%d-%m-%Y %H:%M:%S')} ({request.user.username} - {year_text})"
            bill.remarks = (bill.remarks or '') + signature_note
            bill.save()
            
            log_activity(request.user, 'Signature added to bill', 
                        f'Chairman signature added to bill {bill.bill_number}')
            messages.success(request, f'বিল {bill.bill_number} এ আপনার স্বাক্ষর সফলভাবে যুক্ত হয়েছে! এটি স্থায়ীভাবে সংরক্ষিত হবে।')
            
            # After adding signature, show the PDF
            return redirect('view_bill_pdf', bill_id=bill.id)
        else:
            messages.error(request, 'আপনার স্বাক্ষর আপলোড করা হয়নি। দয়া করে প্রথমে স্বাক্ষর আপলোড করুন।')
            return redirect('signature_upload_chairman')

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
            department_work_types_q(request.user),
            is_active=True
        ).order_by('order')
    elif degree_type == 'masters':
        work_types = WorkType.objects.filter(
            Q(degree_type='masters') | Q(degree_type='both'),
            department_work_types_q(request.user),
            is_active=True
        ).order_by('order')
    else:
        work_types = WorkType.objects.filter(
            department_work_types_q(request.user), is_active=True).order_by('order')

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
                department_work_types_q(request.user),
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
            department_work_types_q(request.user),
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

    # Only the bill's owner or admin-role users may inspect its signature/debug data.
    if bill.user != request.user and not is_admin(request.user):
        return JsonResponse({'error': 'আপনার এই বিল দেখার অনুমতি নেই।'}, status=403)

    from .utils import get_chairman_signature_for_bill
    signature_url = get_chairman_signature_for_bill(bill)
    
    # Resolve the chairman the same way the PDF does: year + department
    chairman_info = {}
    chairman = bill.chairman
    if chairman is None:
        chairman_info = {'error': 'No chairman matches this bill\'s year and department'}
    else:
        sig_field = chairman.profile.active_chairman_signature
        chairman_info = {
            'username': chairman.username,
            'chairman_year': chairman.profile.chairman_year,
            'department': str(chairman.profile.department) if chairman.profile.department_id else None,
            'has_signature': bool(sig_field),
            'signature_name': sig_field.name if sig_field else None,
            'file_exists': sig_field.storage.exists(sig_field.name) if sig_field else False,
        }
    
    debug_data = {
        'bill_id': bill.id,
        'bill_number': bill.bill_number,
        'bill_status': bill.status,
        'bill_remarks': bill.remarks,
        'academic_year': bill.resolved_academic_year,
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
    """Controller bills, split by department and then by academic year.

    Departments come from the admin, so the tabs are built from the database
    rather than hardcoded. ?department=<id> narrows the whole page to one
    department; no parameter means every department.
    """
    pending_all = Bill.objects.filter(status='sent_to_controller')

    departments = Department.objects.filter(is_active=True).order_by('order', 'name')

    # Validate the tab selection instead of trusting the query string
    selected_id = (request.GET.get('department') or '').strip()
    selected_dept = None
    if selected_id.isdigit():
        selected_dept = departments.filter(pk=int(selected_id)).first()

    # Tabs, each with its own pending count so the controller can see at a
    # glance where the work is. Counts ignore the current selection.
    department_tabs = [{
        'id': '',
        'label': 'সব বিভাগ',
        'title': 'সব বিভাগ',
        'count': pending_all.count(),
        'is_active': selected_dept is None,
    }]
    for dept in departments:
        department_tabs.append({
            'id': dept.pk,
            'label': dept.short_name or dept.name,
            'title': dept.name,
            'count': pending_all.filter(department=dept).count(),
            'is_active': selected_dept is not None and dept.pk == selected_dept.pk,
        })

    bills = pending_all.select_related('user', 'department', 'session')
    approved = Bill.objects.filter(status='approved_by_controller')
    rejected = Bill.objects.filter(status='rejected_by_controller')
    if selected_dept is not None:
        bills = bills.filter(department=selected_dept)
        approved = approved.filter(department=selected_dept)
        rejected = rejected.filter(department=selected_dept)

    bills = bills.order_by('-sent_to_controller_at')

    # Year buckets, built as data so the template loops once instead of
    # repeating a near-identical block per year. 'masters' is included -- it
    # used to fall through every branch and its bills were invisible here.
    buckets = {key: [] for key, _bn, _en, _css in CONTROLLER_YEAR_GROUPS}
    for bill in bills:
        key = bill_year_suffix(bill)
        if key in buckets:
            buckets[key].append(bill)

    year_groups = [{
        'key': key,
        'label_bn': label_bn,
        'label_en': label_en,
        'css': css,
        'bills': buckets[key],
    } for key, label_bn, label_en, css in CONTROLLER_YEAR_GROUPS]

    context = {
        'total_bills': bills.count(),
        'pending_count': bills.count(),
        'approved_count': approved.count(),
        'rejected_count': rejected.count(),
        'department_tabs': department_tabs,
        'selected_department': selected_dept,
        'year_groups': year_groups,
        # Kept so anything still referencing the old names keeps working
        'first_year_bills': buckets['1st'],
        'second_year_bills': buckets['2nd'],
        'third_year_bills': buckets['3rd'],
        'fourth_year_bills': buckets['4th'],
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

        # Approval is what mints the controller bill number. Rejected bills
        # never get one, and an already-numbered bill keeps its number.
        assigned = None
        if status == 'approved_by_controller':
            assigned = bill.assign_controller_bill_number()
            if assigned is None:
                messages.warning(
                    request,
                    f'বিল {bill.bill_number} অনুমোদিত হয়েছে, তবে সেশন/বর্ষ না থাকায় '
                    'কন্ট্রোলার বিল নম্বর তৈরি করা যায়নি। বিলটি সম্পাদনা করে সেশন নির্ধারণ করুন।')

        log_activity(request.user, f'Bill {status} by controller',
                     f'Bill {bill.bill_number} {status} by controller'
                     + (f' (controller no. {assigned})' if assigned else ''))

        status_text = 'অনুমোদিত' if status == 'approved_by_controller' else 'বাতিল'
        if assigned:
            messages.success(
                request,
                f'বিল {bill.bill_number} {status_text} করা হয়েছে! '
                f'কন্ট্রোলার বিল নম্বর: {assigned}')
        else:
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
        # The dropdown now offers academic years; year_bills_q also
        # catches bills created before the year/semester split.
        bills = bills.filter(year_bills_q(semester_filter))
    if degree_filter:
        bills = bills.filter(degree_type=degree_filter)
    if department_filter:
        # department is a FK now, so match on its name
        bills = bills.filter(department__name__icontains=department_filter)
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
        bill.year = bill_year_suffix(bill)

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
        'semester_choices': Bill.ACADEMIC_YEAR_CHOICES,
        'department_choices': Department.objects.filter(is_active=True),
        'degree_choices': Bill.DEGREE_CHOICES,
        'bank_choices': Bill.BANK_CHOICES,
        'filter_querystring': filter_querystring,
        **filters,
    }
    return render(request, 'core/accepted_bills.html', context)


# Degree suffixes that WorkType.__str__ appends. Older bills stored the
# displayed string ("প্রশ্নপত্র প্রণয়ন (অনার্স)") in Task.work_type instead of the
# plain name, so matching has to ignore the suffix or those amounts would not
# line up with their column.
_DEGREE_SUFFIXES = (' (অনার্স)', ' (মাস্টার্স)', ' (উভয়)')


def normalise_work_type(name):
    """'প্রশ্নপত্র প্রণয়ন (অনার্স)' -> 'প্রশ্নপত্র প্রণয়ন'."""
    value = (name or '').strip()
    for suffix in _DEGREE_SUFFIXES:
        if value.endswith(suffix):
            return value[:-len(suffix)].strip()
    return value


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'কন্ট্রোলার')
def export_accepted_bills_pdf(request):
    """Consolidated PDF of controller-approved bills.

    One row per bill creator, one column per work type, then মোট টাকা, কর and
    পরিশোধিত টাকা, with a column-wise totals row at the bottom.

    EVERY work type gets its own column: the ones defined in the admin, plus
    any name that appears in the data but is no longer defined. Nothing is
    lumped into a catch-all, and the page is widened to fit however many
    columns that turns out to be.
    """
    bills = (Bill.objects.filter(status='approved_by_controller')
             .select_related('user', 'department', 'session')
             .prefetch_related('tasks')
             .order_by('-controller_approved_at'))
    bills, filters = apply_accepted_bill_filters(request, bills)
    bills = list(bills)

    # Resolve the department so the header can name it and so department
    # specific work types are included
    department = None
    dept_name = (filters.get('department_filter') or '').strip()
    if dept_name:
        department = Department.objects.filter(name__icontains=dept_name).first()
    if department is None:
        dept_ids = {b.department_id for b in bills if b.department_id}
        if len(dept_ids) == 1:
            department = Department.objects.filter(pk=dept_ids.pop()).first()

    # 1. Every work type the admin has defined, in admin order
    work_types = WorkType.objects.filter(is_active=True)
    if department is not None:
        work_types = work_types.filter(
            Q(department__isnull=True) | Q(department=department))
    columns = list(dict.fromkeys(
        normalise_work_type(n)
        for n in work_types.order_by('order', 'name').values_list('name', flat=True)))

    # 2. Plus anything present in the data that is no longer defined, so it
    #    still gets a named column of its own rather than a catch-all
    extra = sorted({
        normalise_work_type(task.work_type)
        for bill in bills for task in bill.tasks.all()
        if normalise_work_type(task.work_type) not in columns
    })
    columns.extend(extra)

    rate = TaxSetting.current_rate()

    rows = {}
    for bill in bills:
        row = rows.setdefault(bill.user_id, {
            'user': bill.user,
            'cells': {name: Decimal('0') for name in columns},
            'total': Decimal('0'),
        })
        row['total'] += Decimal(str(bill.total_amount or 0))
        for task in bill.tasks.all():
            key = normalise_work_type(task.work_type)
            if key in row['cells']:
                row['cells'][key] += Decimal(str(task.amount or 0))

    report_rows = []
    for row in sorted(rows.values(),
                      key=lambda r: (r['user'].get_full_name() or r['user'].username)):
        tax = TaxSetting.tax_on(row['total'], rate)
        report_rows.append({
            'user': row['user'],
            'name': row['user'].get_full_name() or row['user'].username,
            'values': [row['cells'][name] for name in columns],
            'total': row['total'],
            'tax': tax,
            'net': row['total'] - tax,
        })

    column_totals = [
        sum((r['values'][i] for r in report_rows), Decimal('0'))
        for i in range(len(columns))
    ]
    grand_total = sum((r['total'] for r in report_rows), Decimal('0'))
    grand_tax = sum((r['tax'] for r in report_rows), Decimal('0'))
    grand_net = sum((r['net'] for r in report_rows), Decimal('0'))

    # Widen the page instead of squeezing columns. A4 landscape is the floor;
    # past that the sheet grows by a fixed amount per extra work column.
    FIXED_MM = 118          # serial + name + মোট + কর + পরিশোধিত + margins
    PER_COLUMN_MM = 26
    page_width = max(297, FIXED_MM + PER_COLUMN_MM * len(columns))
    page_height = 210

    exam_titles = {b.exam_title for b in bills}
    exam_heading = exam_titles.pop() if len(exam_titles) == 1 else ''

    context = {
        'columns': columns,
        'rows': report_rows,
        'column_totals': column_totals,
        'grand_total': grand_total,
        'grand_tax': grand_tax,
        'grand_net': grand_net,
        'tax_rate': rate,
        'department': department,
        'exam_heading': exam_heading,
        'filters': filters,
        'total_count': len(bills),
        'page_width': page_width,
        'page_height': page_height,
        'generated_at': timezone.now(),
        'generated_by': request.user,
        'report_title': 'অনুমোদিত বিলের সমন্বিত বিবরণী',
    }
    return render_accepted_summary_pdf(context)


    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"accepted_bills_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    log_activity(request.user, 'Accepted bills report exported', f'{total_count} filtered accepted bills exported as PDF report')
    return response


@login_required
def bill_details_api(request, bill_id):
    """API endpoint for bill details"""
    bill = get_object_or_404(Bill, id=bill_id)

    # Only the bill's owner or admin-role users (chairman/office assistant/controller)
    # may view its details — prevents one user from seeing another user's bill.
    if bill.user != request.user and not is_admin(request.user):
        return JsonResponse({'error': 'আপনার এই বিল দেখার অনুমতি নেই।'}, status=403)

    tasks = bill.tasks.all()
    
    data = {
        'bill_number': bill.bill_number,
        'user_name': bill.user.get_full_name() or bill.user.username,
        'user_type': bill.user.profile.user_type if hasattr(bill.user, 'profile') else '',
        'semester': bill.year_semester,
        'exam_title': bill.exam_title,
        'session': bill.session.label_bn if bill.session_id else '',
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
        bill.year = bill_year_suffix(bill)
    
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
    """Scope a bill queryset to the logged-in chairman's academic year.

    The year is read from their profile, and matched against the bill's
    academic_year field (with a fallback for pre-split bills) instead of
    scanning remarks for a hardcoded username.
    """
    year_text = getattr(request.user.profile, 'chairman_year', '') or ''
    if year_text:
        return base_qs.filter(year_bills_q(year_text))
    return base_qs


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.profile.user_type == 'চেয়ারম্যান')
def chairman_returned_bills(request):
    """Bill Rollback (Step 2): Chairman's view of bills the controller has sent back.
    From here the chairman can view/download the bill, read the controller's comment,
    add their signature, and forward the bill on to the original creator (ফেরত বিল)."""
    # Only show controller_returned bills that are NOT hidden and NOT already returned to user
    bills_list = scope_bills_for_role(Bill.objects.all(), request.user).filter(
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
    """API endpoint for bill counts - used by JavaScript notification.

    Same scope as the controller home page: only bills that have reached the
    controller, so the polled numbers match what was rendered server-side.
    """
    reached = Bill.objects.filter(status__in=CONTROLLER_STATUSES)
    sent = reached.filter(status='sent_to_controller').count()
    return JsonResponse({
        'total_bills': reached.count(),
        'pending_count': sent,
        'approved_count': reached.filter(status='approved_by_controller').count(),
        'rejected_count': reached.filter(status='rejected_by_controller').count(),
        'sent_to_controller_count': sent,
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
        bill.remarks = (bill.remarks or '') + f"\nচেয়ারম্যান মন্তব্য (ফেরত): {chairman_note}"
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


# --------------------------
# Chairman Document Upload / Send to Controller
# --------------------------

@login_required
@user_passes_test(is_chairman)
def chairman_documents(request):
    """Chairman panel: upload files and forward them to the controller."""
    if request.method == 'POST':
        form = ChairmanDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            doc.save()

            # "Upload and send" does both in one step
            if request.POST.get('action') == 'upload_and_send':
                doc.mark_sent()
                log_activity(request.user, 'Document sent',
                             f'Document "{doc.title}" uploaded and sent to controller')
                messages.success(request, f'"{doc.title}" আপলোড করে কন্ট্রোলারের কাছে পাঠানো হয়েছে!')
            else:
                log_activity(request.user, 'Document uploaded',
                             f'Document "{doc.title}" uploaded')
                messages.success(request, f'"{doc.title}" সফলভাবে আপলোড করা হয়েছে!')
            return redirect('chairman_documents')
        messages.error(request, 'দয়া করে নিচের ভুলগুলো ঠিক করুন।')
    else:
        form = ChairmanDocumentForm()

    documents = ChairmanDocument.objects.filter(uploaded_by=request.user)

    return render(request, 'core/chairman_documents.html', {
        'form': form,
        'documents': documents,
        'sent_count': documents.filter(is_sent=True).count(),
        'pending_count': documents.filter(is_sent=False).count(),
        'max_size_mb': ChairmanDocument.MAX_SIZE_MB,
        'allowed_extensions': ', '.join(e.upper() for e in ChairmanDocument.ALLOWED_EXTENSIONS),
    })


@login_required
@user_passes_test(is_chairman)
@require_POST
def chairman_document_send(request, doc_id):
    """Forward one already-uploaded file to the controller."""
    doc = get_object_or_404(ChairmanDocument, id=doc_id, uploaded_by=request.user)

    if doc.is_sent:
        messages.info(request, f'"{doc.title}" ইতিমধ্যে কন্ট্রোলারের কাছে পাঠানো হয়েছে।')
    else:
        doc.mark_sent()
        log_activity(request.user, 'Document sent',
                     f'Document "{doc.title}" sent to controller')
        messages.success(request, f'"{doc.title}" কন্ট্রোলারের কাছে পাঠানো হয়েছে!')
    return redirect('chairman_documents')


@login_required
@user_passes_test(is_chairman)
@require_POST
def chairman_document_delete(request, doc_id):
    """Delete one of your own uploads, removing the stored file too."""
    doc = get_object_or_404(ChairmanDocument, id=doc_id, uploaded_by=request.user)
    title = doc.title
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    log_activity(request.user, 'Document deleted', f'Document "{title}" deleted')
    messages.success(request, f'"{title}" মুছে ফেলা হয়েছে।')
    return redirect('chairman_documents')


@login_required
@user_passes_test(is_controller)
def controller_documents(request):
    """Controller inbox: everything chairmen have sent."""
    documents = ChairmanDocument.objects.filter(is_sent=True).select_related('uploaded_by')

    chairman_filter = request.GET.get('chairman', '').strip()
    if chairman_filter:
        documents = documents.filter(uploaded_by__username=chairman_filter)

    search = request.GET.get('q', '').strip()
    if search:
        documents = documents.filter(title__icontains=search)

    documents = documents.order_by('-sent_at', '-uploaded_at')

    # Only chairmen who have actually sent something appear in the filter
    senders = User.objects.filter(
        chairman_documents__is_sent=True
    ).distinct().order_by('first_name', 'username')

    return render(request, 'core/controller_documents.html', {
        'documents': documents,
        'senders': senders,
        'chairman_filter': chairman_filter,
        'search': search,
        'total_count': ChairmanDocument.objects.filter(is_sent=True).count(),
    })


@login_required
def chairman_document_download(request, doc_id):
    """Serve an uploaded file with a permission check.

    Files deliberately do NOT go out over MEDIA_URL: that would make every
    upload readable by anyone who guessed the path. can_be_viewed_by() limits
    it to the uploader and, once sent, the controller.

    ?inline=1 renders a PDF in the browser; anything else downloads.
    """
    doc = get_object_or_404(ChairmanDocument, id=doc_id)

    if not doc.can_be_viewed_by(request.user):
        raise Http404('ফাইলটি পাওয়া যায়নি।')

    if not doc.exists_on_disk:
        messages.error(request, f'"{doc.title}" ফাইলটি সার্ভারে পাওয়া যায়নি।')
        return redirect('controller_documents' if is_controller(request.user)
                        else 'chairman_documents')

    # Opening it as the controller counts as reading it, so the chairman can
    # see whether their file was actually looked at.
    if is_controller(request.user) and doc.is_sent:
        doc.mark_read()

    inline = request.GET.get('inline') == '1' and doc.is_pdf
    response = FileResponse(
        doc.file.open('rb'),
        as_attachment=not inline,
        filename=doc.filename,
    )
    if inline:
        response['Content-Type'] = 'application/pdf'
    return response


# --------------------------
# Chairman Signature (year-based, replaces the four username-gated views)
# --------------------------

@login_required
@user_passes_test(is_chairman)
def signature_upload_chairman(request):
    """One signature-upload page for every chairman.

    The old design had four separate views, each locked to a hardcoded
    username (JSTUChairman1..4) and writing to its own numbered field. That
    capped the university at four chairmen. Now any chairman uploads their own
    signature, and which year it applies to comes from their profile.
    """
    profile = request.user.profile

    if request.method == 'POST':
        signature_file = request.FILES.get('signature')
        if not signature_file:
            messages.error(request, 'দয়া করে একটি ছবি নির্বাচন করুন।')
            return redirect('signature_upload_chairman')

        if signature_file.content_type not in ('image/jpeg', 'image/png', 'image/jpg'):
            messages.error(request, 'শুধুমাত্র JPEG বা PNG ফরম্যাটের ছবি আপলোড করুন।')
            return redirect('signature_upload_chairman')

        if signature_file.size > 2 * 1024 * 1024:
            messages.error(request, 'ছবির সাইজ ২MB এর কম হতে হবে।')
            return redirect('signature_upload_chairman')

        profile.signature_chairman = signature_file
        profile.save()
        log_activity(request.user, 'Signature uploaded',
                     f'Chairman ({profile.chairman_year or "no year"}) uploaded signature')
        messages.success(request, 'আপনার স্বাক্ষর সফলভাবে আপলোড করা হয়েছে!')
        return redirect('signature_upload_chairman')

    return render(request, 'core/signature_upload_chairman.html', {
        'signature': profile.active_chairman_signature,
        'chairman_year': profile.chairman_year,
        'department': profile.department,
    })


@login_required
@user_passes_test(is_chairman)
@require_POST
def delete_signature_chairman(request):
    """Remove this chairman's signature (both new and legacy fields)."""
    profile = request.user.profile
    removed = False

    if profile.signature_chairman:
        profile.signature_chairman.delete(save=False)
        profile.signature_chairman = None
        removed = True

    # Also clear whichever legacy numbered field backs their year, otherwise
    # active_chairman_signature would keep returning the old image.
    legacy_field = {
        '১ম বর্ষ': 'signature_chairman1',
        '২য় বর্ষ': 'signature_chairman2',
        '৩য় বর্ষ': 'signature_chairman3',
        '৪র্থ বর্ষ': 'signature_chairman4',
    }.get(profile.chairman_year or '')
    if legacy_field:
        legacy_value = getattr(profile, legacy_field)
        if legacy_value:
            legacy_value.delete(save=False)
            setattr(profile, legacy_field, None)
            removed = True

    profile.save()
    if removed:
        log_activity(request.user, 'Signature deleted', 'Chairman deleted signature')
        messages.success(request, 'আপনার স্বাক্ষর সফলভাবে ডিলিট করা হয়েছে!')
    else:
        messages.info(request, 'কোনো স্বাক্ষর পাওয়া যায়নি।')
    return redirect('signature_upload_chairman')