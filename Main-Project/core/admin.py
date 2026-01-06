from django.contrib import admin
from .models import Profile, SliderImage, Bill, Task

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type']
    list_filter = ['user_type']

class SliderImageAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at']
    list_editable = ['is_active']
    list_filter = ['is_active']

class TaskInline(admin.TabularInline):
    model = Task
    extra = 1

class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'voucher_number', 'user', 'semester', 'total_amount', 'created_at']
    list_filter = ['semester', 'created_at']
    inlines = [TaskInline]

admin.site.register(Profile, ProfileAdmin)
admin.site.register(SliderImage, SliderImageAdmin)
admin.site.register(Bill, BillAdmin)
admin.site.register(Task)