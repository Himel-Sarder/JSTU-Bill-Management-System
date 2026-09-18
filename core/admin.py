from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import (Profile, SliderImage, WorkType, Benefit, Bill, Task,
                     AcademicSession, ChairmanDocument, Department, TaxSetting)

# ── Add this to your admin.py (at the top, after imports) ────────────────────

from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
import json


class CustomAdminSite(AdminSite):
    site_header  = "বিল ম্যানেজমেন্ট অ্যাডমিন"
    site_title   = "BillM Admin"
    index_title  = "ড্যাশবোর্ড"

    def index(self, request, extra_context=None):
        from core.models import Bill   # adjust app name if needed

        # ── Stats ──────────────────────────────────────────────
        total_bills    = Bill.objects.count()
        pending_bills  = Bill.objects.filter(status='pending').count()
        approved_bills = Bill.objects.filter(status='approved').count()
        rejected_bills = Bill.objects.filter(status='rejected').count()
        paid_bills     = Bill.objects.filter(status='paid').count()
        draft_bills    = Bill.objects.filter(status='draft').count()
        total_users    = User.objects.count()

        from django.db.models import Sum
        total_amount = Bill.objects.aggregate(t=Sum('total_amount'))['t'] or 0

        # ── Monthly data (last 7 months) ───────────────────────
        seven_months_ago = timezone.now() - timezone.timedelta(days=210)
        monthly_qs = (
            Bill.objects
            .filter(created_at__gte=seven_months_ago)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )
        bn_months = {
            1:'জানু', 2:'ফেব্রু', 3:'মার্চ', 4:'এপ্রিল',
            5:'মে',   6:'জুন',   7:'জুলাই', 8:'আগস্ট',
            9:'সেপ্টে',10:'অক্টো',11:'নভে',  12:'ডিসে',
        }
        monthly_labels = [bn_months[m['month'].month] for m in monthly_qs]
        monthly_data   = [m['count'] for m in monthly_qs]

        # ── Recent records ─────────────────────────────────────
        recent_bills = Bill.objects.select_related('user').order_by('-created_at')[:8]
        recent_users = User.objects.select_related('profile').order_by('-date_joined')[:8]

        extra_context = extra_context or {}
        extra_context.update({
            'total_bills':    total_bills,
            'pending_bills':  pending_bills,
            'approved_bills': approved_bills,
            'rejected_bills': rejected_bills,
            'paid_bills':     paid_bills,
            'draft_bills':    draft_bills,
            'total_users':    total_users,
            'total_amount':   total_amount,
            'monthly_labels': json.dumps(monthly_labels, ensure_ascii=False),
            'monthly_data':   json.dumps(monthly_data),
            'recent_bills':   recent_bills,
            'recent_users':   recent_users,
        })
        return super().index(request, extra_context)



class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    # Exactly one profile per user, so never offer a second blank form.
    extra = 0
    min_num = 1
    max_num = 1
    # The fields an admin actually needs when setting a user up. chairman_year
    # is what routes bills to a chairman, so it has to be visible here.
    fields = ('user_type', 'department', 'chairman_year', 'phone_number',
              'joining_date', 'profile_picture', 'signature_general',
              'signature_chairman')


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]

    def get_inline_instances(self, request, obj=None):
        """Hide the profile inline on the ADD form.

        A Profile is created automatically by a post_save signal on User. On
        the add form the user row does not exist yet, so the inline has nothing
        to bind to and submits an unsaved Profile. Django then INSERTs it right
        after the signal has already inserted one, and the OneToOne constraint
        rejects the second:

            IntegrityError: UNIQUE constraint failed: core_profile.user_id

        Django's own UserAdmin add step only collects username and password
        before redirecting to the change form, so nothing is lost: the profile
        fields are filled in there, editing the row the signal created.
        """
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type',
                    'get_department', 'get_chairman_year', 'is_staff')
    list_filter = ('profile__user_type', 'profile__department', 'profile__chairman_year',
                   'is_staff', 'is_superuser', 'is_active')

    def get_user_type(self, obj):
        return obj.profile.user_type if hasattr(obj, 'profile') else '-'

    get_user_type.short_description = 'পদবী'

    @admin.display(description='বিভাগ')
    def get_department(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.department if profile and profile.department_id else '-'

    @admin.display(description='চেয়ারম্যানের বর্ষ')
    def get_chairman_year(self, obj):
        profile = getattr(obj, 'profile', None)
        return (profile.chairman_year or '-') if profile else '-'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ('get_colored_name', 'department', 'description', 'needs_benefit', 'default_amount', 'is_active', 'order')
    list_filter = ('department', 'degree_type', 'needs_benefit', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('degree_type', 'order', 'name')
    list_editable = ('needs_benefit', 'default_amount', 'is_active', 'order')
    actions = ['duplicate_for_department']

    @admin.action(description='নির্বাচিত কাজের ধরণ প্রতিটি বিভাগের জন্য কপি করুন')
    def duplicate_for_department(self, request, queryset):
        """Copy shared work types into every department.

        Use this when departments need different rates for the same work:
        copy first, then edit each department's amounts. Existing
        combinations are skipped, so it is safe to run twice.
        """
        created = 0
        for dept in Department.objects.filter(is_active=True):
            for wt in queryset:
                exists = WorkType.objects.filter(
                    name=wt.name, degree_type=wt.degree_type, department=dept).exists()
                if exists:
                    continue
                benefits = list(wt.benefits.all())
                wt.pk = None
                wt.department = dept
                wt.save()
                for b in benefits:
                    b.pk = None
                    b.work_type = wt
                    b.save()
                created += 1
        self.message_user(request, f'{created} টি কাজের ধরণ কপি করা হয়েছে।')


    # Add degree type as a radio button choice in the add/edit form
    radio_fields = {"degree_type": admin.HORIZONTAL}

    fieldsets = (
        ('বেসিক তথ্য', {
            'fields': ('name', 'description', 'degree_type', 'needs_benefit')
        }),
        ('পরিমাণ সংক্রান্ত', {
            'fields': ('default_amount',)
        }),
        ('সেটিংস', {
            'fields': ('is_active', 'order')
        }),
    )

    def get_colored_name(self, obj):
        """Display name with color based on degree type"""
        degree_colors = {
            'honors': '#4ECDC4',  # Teal for honors
            'masters': '#FF6B6B',  # Coral for masters
            'both': '#95A5A6',  # Gray for both
        }
        color = degree_colors.get(obj.degree_type, '#FFFFFF')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            str(obj)
        )

    get_colored_name.short_description = 'কাজের ধরণ'
    get_colored_name.admin_order_field = 'name'

    def get_queryset(self, request):
        """Allow filtering by degree type via URL parameter"""
        qs = super().get_queryset(request)

        # Check if there's a degree filter in the request GET parameters
        if 'degree_type' in request.GET:
            degree_filter = request.GET.get('degree_type')
            if degree_filter:
                qs = qs.filter(degree_type=degree_filter)

        return qs

    def changelist_view(self, request, extra_context=None):
        """Add degree filter counts to context"""
        extra_context = extra_context or {}

        # Get counts for each degree type
        extra_context['honors_count'] = WorkType.objects.filter(degree_type='honors').count()
        extra_context['masters_count'] = WorkType.objects.filter(degree_type='masters').count()
        extra_context['both_count'] = WorkType.objects.filter(degree_type='both').count()

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_colored_work_type', 'calculation_type', 'base_amount', 'unit_label', 'is_active',
                    'order')
    list_filter = ('work_type__degree_type', 'calculation_type', 'is_active', 'work_type')
    search_fields = ('name', 'work_type__name')
    ordering = ('work_type', 'order', 'name')
    list_editable = ('is_active', 'order', 'base_amount')

    # Fix: Remove label_from_instance and use the model's __str__ method instead
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "work_type":
            # Show all work types - the __str__ method will handle the display with degree
            kwargs["queryset"] = WorkType.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    fieldsets = (
        ('বেসিক তথ্য', {
            'fields': ('work_type', 'name', 'is_active', 'order')
        }),
        ('গণনা সংক্রান্ত', {
            'fields': ('calculation_type', 'base_amount', 'unit_label', 'min_unit', 'max_unit')
        }),
    )

    def get_colored_work_type(self, obj):
        """Display work type with color based on degree"""
        degree_colors = {
            'honors': '#4ECDC4',
            'masters': '#FF6B6B',
            'both': '#95A5A6',
        }
        color = degree_colors.get(obj.work_type.degree_type, '#FFFFFF')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            str(obj.work_type)
        )

    get_colored_work_type.short_description = 'কাজের ধরণ'
    get_colored_work_type.admin_order_field = 'work_type__name'

    def get_queryset(self, request):
        """Filter benefits based on degree type from URL"""
        qs = super().get_queryset(request)

        # Check if there's a degree filter in the request GET parameters
        if 'degree_type' in request.GET:
            degree_filter = request.GET.get('degree_type')
            if degree_filter:
                qs = qs.filter(work_type__degree_type=degree_filter)

        return qs

    def changelist_view(self, request, extra_context=None):
        """Add degree filter counts to context"""
        extra_context = extra_context or {}

        # Get counts for benefits by degree type
        extra_context['honors_count'] = Benefit.objects.filter(work_type__degree_type='honors').count()
        extra_context['masters_count'] = Benefit.objects.filter(work_type__degree_type='masters').count()
        extra_context['both_count'] = Benefit.objects.filter(work_type__degree_type='both').count()

        return super().changelist_view(request, extra_context=extra_context)




@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'controller_bill_number', 'user', 'department', 'exam_heading', 'colored_status', 'total_amount_display', 'created_at')
    list_filter = ('department', 'status', 'academic_year', 'exam_semester', 'session', 'degree_type', 'created_at')
    search_fields = ('bill_number', 'controller_bill_number', 'user__username',
                     'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'bill_number',
                       'voucher_number', 'controller_bill_number')
    ordering = ('-created_at',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['mark_approved', 'mark_rejected', 'mark_paid', 'assign_session']

    @admin.action(description='নির্বাচিত বিলে সেশন নির্ধারণ করুন (সবচেয়ে সাম্প্রতিক সক্রিয় সেশন)')
    def assign_session(self, request, queryset):
        """Fill in the session on bills that predate the session field.

        Bills migrated from the old flat-semester scheme have no session, so
        they print without an exam year. Filter the changelist down to one
        batch at a time and apply the right session to each.
        """
        session = AcademicSession.objects.filter(is_active=True).order_by('-start_year').first()
        if session is None:
            self.message_user(request, 'কোনো সক্রিয় সেশন নেই।', level='error')
            return
        updated = queryset.filter(session__isnull=True).update(session=session)
        self.message_user(request, f'{updated} টি বিলে {session.label_bn} সেশন যুক্ত হয়েছে।')

    @admin.display(description='পরীক্ষা')
    def exam_heading(self, obj):
        """Shows '৩য় বর্ষ ২য় সেমিস্টার পরীক্ষা - ২০২২' in the changelist."""
        return obj.exam_title

    def colored_status(self, obj):
        colors = {
            'draft':    ('#95A5A6', 'খসড়া'),
            'pending':  ('#F39C12', 'অপেক্ষমান'),
            'approved': ('#27AE60', 'অনুমোদিত'),
            'rejected': ('#E74C3C', 'বাতিল'),
            'paid':     ('#2980B9', 'পরিশোধিত'),
        }
        color, label = colors.get(obj.status, ('#999', obj.status))
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:12px;font-size:12px;font-weight:600;">{}</span>',
            color, label
        )
    colored_status.short_description = 'স্ট্যাটাস'
    colored_status.admin_order_field = 'status'

    def total_amount_display(self, obj):
        return format_html('<strong style="color:#27AE60;">৳ {}</strong>', f'{obj.total_amount:,.0f}')
    total_amount_display.short_description = 'মোট টাকা'
    total_amount_display.admin_order_field = 'total_amount'

    @admin.action(description='নির্বাচিত বিল অনুমোদন করুন')
    def mark_approved(self, request, queryset):
        updated = queryset.exclude(status='paid').update(status='approved')
        self.message_user(request, f'{updated}টি বিল অনুমোদিত হয়েছে।')

    @admin.action(description='নির্বাচিত বিল বাতিল করুন')
    def mark_rejected(self, request, queryset):
        updated = queryset.exclude(status='paid').update(status='rejected')
        self.message_user(request, f'{updated}টি বিল বাতিল হয়েছে।')

    @admin.action(description='নির্বাচিত বিল পরিশোধিত করুন')
    def mark_paid(self, request, queryset):
        updated = queryset.filter(status='approved').update(status='paid')
        self.message_user(request, f'{updated}টি বিল পরিশোধিত হয়েছে।')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('bill', 'work_type', 'benefit', 'quantity', 'unit', 'amount')
    list_filter = ('work_type', 'bill__semester')
    search_fields = ('bill__bill_number', 'work_type', 'benefit')
    readonly_fields = ('bill',)

    fieldsets = (
        ('কাজের তথ্য', {
            'fields': ('bill', 'work_type', 'benefit')
        }),
        ('পরিমাণ ও টাকা', {
            'fields': ('quantity', 'unit', 'amount')
        }),
    )


@admin.register(SliderImage)
class SliderImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'is_active', 'order', 'created_at')
    list_filter = ('is_active',)
    ordering = ('order',)
    list_editable = ('order', 'is_active')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;" />',
                obj.image.url)
        return "No Image"

    image_preview.short_description = 'ছবি'


# Remove SystemSetting and ActivityLog from admin by not registering them
# If they were previously registered, we can unregister them
try:
    from .models import SystemSetting, ActivityLog

    if admin.site.is_registered(SystemSetting):
        admin.site.unregister(SystemSetting)
    if admin.site.is_registered(ActivityLog):
        admin.site.unregister(ActivityLog)
except (ImportError, admin.sites.NotRegistered):
    pass


admin.site.__class__ = CustomAdminSite
admin.site.site_header  = "বিল ম্যানেজমেন্ট অ্যাডমিন"
admin.site.site_title   = "BillM Admin"
admin.site.index_title  = "ড্যাশবোর্ড"

# --------------------------
# Academic Session admin
# --------------------------
@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    """Lets the admin add sessions (2021-2022, 2022-2023, ...) for bill forms."""

    list_display = ('label_bn', 'start_year', 'end_year', 'exam_year_display',
                    'is_active', 'bill_count')
    list_filter = ('is_active',)
    search_fields = ('start_year', 'end_year')
    ordering = ('-start_year',)
    list_editable = ('is_active',)

    @admin.display(description='সেশন')
    def label_bn(self, obj):
        return obj.label_bn

    @admin.display(description='পরীক্ষার বছর')
    def exam_year_display(self, obj):
        return obj.exam_year_bn

    @admin.display(description='বিল সংখ্যা')
    def bill_count(self, obj):
        return obj.bills.count()


# --------------------------
# Chairman Document admin
# --------------------------
@admin.register(ChairmanDocument)
class ChairmanDocumentAdmin(admin.ModelAdmin):
    """Read-mostly view of chairman uploads and what has reached the controller."""

    list_display = ('title', 'uploaded_by', 'file_type', 'file_size',
                    'sent_status', 'read_status', 'uploaded_at')
    list_filter = ('is_sent', 'is_read', 'uploaded_at', 'uploaded_by')
    search_fields = ('title', 'note', 'uploaded_by__username',
                     'uploaded_by__first_name', 'uploaded_by__last_name')
    readonly_fields = ('uploaded_at', 'sent_at', 'read_at')
    date_hierarchy = 'uploaded_at'
    ordering = ('-uploaded_at',)
    list_per_page = 25
    actions = ['send_to_controller']

    @admin.display(description='ধরন')
    def file_type(self, obj):
        return obj.extension.upper() or '-'

    @admin.display(description='সাইজ')
    def file_size(self, obj):
        return obj.size_display or '-'

    @admin.display(description='অবস্থা')
    def sent_status(self, obj):
        # format_html() requires at least one argument in Django 5+; calling it
        # with a bare literal raises TypeError and takes the whole changelist
        # down, so the text is passed as a parameter.
        colour, label = (('#27AE60', 'পাঠানো হয়েছে') if obj.is_sent
                         else ('#F39C12', 'অপেক্ষমান'))
        return format_html('<span style="color:{};font-weight:600;">{}</span>',
                           colour, label)

    @admin.display(description='দেখা হয়েছে')
    def read_status(self, obj):
        return 'হ্যাঁ' if obj.is_read else 'না'

    @admin.action(description='নির্বাচিত ফাইল কন্ট্রোলারে পাঠান')
    def send_to_controller(self, request, queryset):
        sent = 0
        for doc in queryset.filter(is_sent=False):
            doc.mark_sent()
            sent += 1
        self.message_user(request, f'{sent} টি ফাইল কন্ট্রোলারে পাঠানো হয়েছে।')


# --------------------------
# Department admin
# --------------------------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Add and manage departments. Everything else in the system hangs off these."""

    list_display = ('name', 'short_name', 'is_active', 'order',
                    'member_count', 'bill_count', 'work_type_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'short_name')
    ordering = ('order', 'name')
    list_editable = ('is_active', 'order')

    @admin.display(description='ব্যবহারকারী')
    def member_count(self, obj):
        return obj.members.count()

    @admin.display(description='বিল')
    def bill_count(self, obj):
        return obj.bills.count()

    @admin.display(description='নিজস্ব কাজের ধরণ')
    def work_type_count(self, obj):
        return obj.work_types.count()


# --------------------------
# Tax setting admin
# --------------------------
@admin.register(TaxSetting)
class TaxSettingAdmin(admin.ModelAdmin):
    """Set the tax percentage used on the controller's accepted-bill report."""

    list_display = ('percentage', 'label', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    ordering = ('-updated_at',)

    def has_delete_permission(self, request, obj=None):
        # Keeping the history is useful; deactivate instead of deleting.
        return True