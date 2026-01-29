from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, SliderImage, WorkType, Benefit, Bill, Task, SystemSetting, ActivityLog


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
    list_display = ('name', 'description', 'needs_benefit', 'default_amount', 'is_active', 'order', 'created_at')
    list_filter = ('needs_benefit', 'is_active')
    search_fields = ('name', 'description')
    ordering = ('order', 'name')
    list_editable = ('needs_benefit', 'default_amount', 'is_active', 'order')
    fieldsets = (
        ('বেসিক তথ্য', {
            'fields': ('name', 'description', 'needs_benefit')
        }),
        ('পরিমাণ সংক্রান্ত', {
            'fields': ('default_amount',)
        }),
        ('সেটিংস', {
            'fields': ('is_active', 'order')
        }),
    )


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ('name', 'work_type', 'calculation_type', 'base_amount', 'unit_label', 'is_active', 'order')
    list_filter = ('work_type', 'calculation_type', 'is_active')
    search_fields = ('name', 'work_type__name')
    ordering = ('work_type', 'order', 'name')
    list_editable = ('is_active', 'order', 'base_amount')

    fieldsets = (
        ('বেসিক তথ্য', {
            'fields': ('work_type', 'name', 'is_active', 'order')
        }),
        ('গণনা সংক্রান্ত', {
            'fields': ('calculation_type', 'base_amount', 'unit_label', 'min_unit', 'max_unit')
        }),
    )

    def get_queryset(self, request):
        # শুধুমাত্র সেই WorkType গুলোর Benefits দেখাবে যেগুলোর needs_benefit=True
        qs = super().get_queryset(request)
        return qs.filter(work_type__needs_benefit=True)


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'user', 'semester', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'semester', 'created_at')
    search_fields = ('bill_number', 'user__username', 'user__first_name')
    readonly_fields = ('created_at', 'updated_at', 'approved_at')
    ordering = ('-created_at',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('bill', 'work_type', 'benefit', 'quantity', 'unit', 'amount')
    list_filter = ('work_type', 'bill__semester')
    search_fields = ('bill__bill_number', 'work_type', 'benefit')
    readonly_fields = ('bill',)


@admin.register(SliderImage)
class SliderImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'created_at')
    list_filter = ('is_active',)
    ordering = ('order',)
    list_editable = ('order', 'is_active')


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'description')
    search_fields = ('key', 'description')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'action', 'details')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)