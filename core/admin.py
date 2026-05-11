from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Profile, SliderImage, WorkType, Benefit, Bill, Task

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


class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_user_type', 'is_staff')
    list_filter = ('profile__user_type', 'is_staff', 'is_superuser', 'is_active')

    def get_user_type(self, obj):
        return obj.profile.user_type if hasattr(obj, 'profile') else '-'

    get_user_type.short_description = 'পদবী'


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ('get_colored_name', 'description', 'needs_benefit', 'default_amount', 'is_active', 'order')
    list_filter = ('degree_type', 'needs_benefit', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('degree_type', 'order', 'name')
    list_editable = ('needs_benefit', 'default_amount', 'is_active', 'order')

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
    list_display = ('bill_number', 'user', 'semester', 'colored_status', 'total_amount_display', 'created_at')
    list_filter = ('status', 'semester', 'degree_type', 'created_at')
    search_fields = ('bill_number', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'bill_number', 'voucher_number')
    ordering = ('-created_at',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    actions = ['mark_approved', 'mark_rejected', 'mark_paid']

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
