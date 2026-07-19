from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
from datetime import datetime
from django.core.validators import MinValueValidator, MaxValueValidator


# --------------------------
# Profile Model
# --------------------------
class Profile(models.Model):
    USER_TYPES = [
        ('চেয়ারম্যান', 'চেয়ারম্যান'),
        ('কন্ট্রোলার', 'কন্ট্রোলার'),
        ('অ্যাসিস্ট্যান্ট প্রফেসর', 'অ্যাসিস্ট্যান্ট প্রফেসর'),
        ('লেকচারার', 'লেকচারার'),
        ('অফিস সহকারী', 'অফিস সহকারী'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=50, choices=USER_TYPES, verbose_name='পদবী')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png',
                                        verbose_name='প্রোফাইল ছবি')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='ফোন নম্বর')
    joining_date = models.DateField(blank=True, null=True, verbose_name='যোগদানের তারিখ')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Signature fields for different users
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name='স্বাক্ষর')
    signature_general = models.ImageField(upload_to='signatures/general/', blank=True, null=True, verbose_name='সাধারণ স্বাক্ষর')
    signature_chairman1 = models.ImageField(upload_to='signatures/chairman1/', blank=True, null=True, verbose_name='চেয়ারম্যান ১ স্বাক্ষর')
    signature_chairman2 = models.ImageField(upload_to='signatures/chairman2/', blank=True, null=True, verbose_name='চেয়ারম্যান ২ স্বাক্ষর')
    signature_chairman3 = models.ImageField(upload_to='signatures/chairman3/', blank=True, null=True, verbose_name='চেয়ারম্যান ৩ স্বাক্ষর')
    signature_chairman4 = models.ImageField(upload_to='signatures/chairman4/', blank=True, null=True, verbose_name='চেয়ারম্যান ৪ স্বাক্ষর')

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create profile when a new user is created"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


# --------------------------
# Slider Image Model
# --------------------------
class SliderImage(models.Model):
    title = models.CharField(
        max_length=200, 
        verbose_name='শিরোনাম',
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='slider_images/', 
        verbose_name='ছবি'
    )
    description = models.TextField(
        verbose_name='বর্ণনা',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='সক্রিয়'
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name='ক্রম'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title if self.title else f"Image {self.id}"


# --------------------------
# Work Type Model (Master Table for Work Types)
# --------------------------

class WorkType(models.Model):
    DEGREE_CHOICES = [
        ('both', 'উভয়'),
        ('honors', 'অনার্স'),
        ('masters', 'মাস্টার্স'),
    ]

    name = models.CharField(max_length=100, verbose_name='কাজের ধরণ')
    description = models.TextField(blank=True, verbose_name='বর্ণনা')
    degree_type = models.CharField(max_length=10, choices=DEGREE_CHOICES, default='both', verbose_name='ডিগ্রির ধরণ')
    needs_benefit = models.BooleanField(default=True, verbose_name='উপকাজ প্রয়োজন?')
    default_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='ডিফল্ট পরিমাণ (যদি উপকাজের দরকার না থাকে)'
    )
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়')
    order = models.PositiveIntegerField(default=0, verbose_name='ক্রম')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'কাজের ধরণ'
        verbose_name_plural = 'কাজের ধরণসমূহ'
        # Remove unique constraint on name alone, make it unique with degree_type
        unique_together = ['name', 'degree_type']

    def __str__(self):
        degree_display = dict(self.DEGREE_CHOICES).get(self.degree_type, '')
        if degree_display and degree_display != 'উভয়':
            return f"{self.name} ({degree_display})"
        return self.name

    def get_display_name(self):
        """Return name with degree suffix for display"""
        degree_display = dict(self.DEGREE_CHOICES).get(self.degree_type, '')
        if degree_display and degree_display != 'উভয়':
            return f"{self.name} ({degree_display})"
        return self.name


class Benefit(models.Model):
    CALCULATION_TYPES = [
        ('fixed', 'নির্দিষ্ট পরিমাণ'),
        ('per_piece', 'কতটি'),
        ('per_paper', 'প্রতি কপি'),
        ('per_question', 'প্রতি প্রশ্ন'),
        ('per_hour', 'প্রতি ঘণ্টা'),
        ('per_student', 'প্রতি শিক্ষার্থী'),
        ('per_semester', 'প্রতি সেমিস্টার'),
        ('per_person', 'জনপ্রতি'),
        ('per_day', 'প্রতি দিন')
    ]

    work_type = models.ForeignKey(WorkType, on_delete=models.CASCADE, related_name='benefits', verbose_name='কাজের ধরণ')
    name = models.CharField(max_length=100, verbose_name='উপকাজের নাম')
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPES, default='fixed', verbose_name='গণনা পদ্ধতি')
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='ভিত্তি পরিমাণ')
    unit_label = models.CharField(max_length=50, blank=True, verbose_name='একক লেবেল (যেমন: কতটি, কপি, প্রশ্ন)')
    min_unit = models.PositiveIntegerField(default=1, verbose_name='ন্যূনতম একক')
    max_unit = models.PositiveIntegerField(default=100, verbose_name='সর্বোচ্চ একক')
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়')
    order = models.PositiveIntegerField(default=0, verbose_name='ক্রম')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['work_type', 'order', 'name']
        verbose_name = 'উপকাজ'
        verbose_name_plural = 'উপকাজসমূহ'
        # Benefit name should be unique within a work_type
        unique_together = ['work_type', 'name']

    def __str__(self):
        return f"{self.work_type.get_display_name()} - {self.name}"

    def calculate_amount(self, quantity=1):
        """Calculate total amount based on calculation type and quantity"""
        if self.calculation_type == 'fixed':
            return self.base_amount
        elif self.calculation_type in ['per_piece', 'per_paper', 'per_question', 'per_hour', 'per_student', 'per_semester']:
            return self.base_amount * quantity
        return 0

# --------------------------
# Bill Model
# --------------------------
class Bill(models.Model):
    DEGREE_CHOICES = [
        ('honors', 'অনার্স'),
        ('masters', 'মাস্টার্স'),
    ]
    
    # Bank Information Fields
    BANK_CHOICES = [
        ('জনতা ব্যাংক', 'জনতা ব্যাংক'),
        ('ডাচ বাংলা ব্যাংক', 'ডাচ বাংলা ব্যাংক'),
        ('সোনালী ব্যাংক', 'সোনালী ব্যাংক'),
        ('ইসলামী ব্যাংক', 'ইসলামী ব্যাংক'),
    ]

    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES, blank=True, null=True,
                                 verbose_name='ব্যাংকের নাম')
    bank_branch = models.CharField(max_length=100, blank=True, null=True, verbose_name='শাখা')
    account_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='একাউন্ট নাম্বার')
    routing_number = models.CharField(max_length=50, blank=True, null=True, verbose_name='রাউটিং নাম্বার')

    SEMESTER_CHOICES = [
        ('১ম সেমিস্টার', '১ম সেমিস্টার'),
        ('২য় সেমিস্টার', '২য় সেমিস্টার'),
        ('৩য় সেমিস্টার', '৩য় সেমিস্টার'),
        ('৪র্থ সেমিস্টার', '৪র্থ সেমিস্টার'),
        ('৫ম সেমিস্টার', '৫ম সেমিস্টার'),
        ('৬ষ্ঠ সেমিস্টার', '৬ষ্ঠ সেমিস্টার'),
        ('৭ম সেমিস্টার', '৭ম সেমিস্টার'),
        ('৮ম সেমিস্টার', '৮ম সেমিস্টার'),
        ('মাস্টার্স', 'মাস্টার্স')
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('sent_to_controller', 'Sent to Controller'),
        ('approved_by_controller', 'Approved by Controller'),
        ('rejected_by_controller', 'Rejected by Controller'),
    ]

    bill_number = models.CharField(max_length=50, unique=True, verbose_name='বিল নম্বর')
    voucher_number = models.CharField(max_length=50, unique=True, verbose_name='ভাউচার নম্বর')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='ব্যবহারকারী')
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, verbose_name='সেমিস্টার')
    department = models.CharField(max_length=100, default='কম্পিউটার বিজ্ঞান এবং প্রকৌশল', verbose_name='বিভাগ')
    bangla_date = models.CharField(max_length=50, verbose_name='বাংলা তারিখ')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='মোট টাকা')
    
    # Status field - Increased max_length to 30 to accommodate longer status values
    status = models.CharField(
        max_length=30,  # Changed from 20 to 30
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name='স্ট্যাটাস'
    )
    
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_bills', 
        verbose_name='অনুমোদনকারী'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='অনুমোদনের সময়')
    remarks = models.TextField(blank=True, null=True, verbose_name='মন্তব্য')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hidden_from_chairman = models.BooleanField(default=False, verbose_name='চেয়ারম্যানের কাছে লুকানো')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='পাঠানোর সময়')  
    degree_type = models.CharField(max_length=10, choices=DEGREE_CHOICES, default='honors', verbose_name='ডিগ্রির ধরণ')
    user_signature_added = models.BooleanField(default=False, verbose_name='ব্যবহারকারীর স্বাক্ষর যুক্ত হয়েছে')
    chairman_signature_added = models.BooleanField(default=False, verbose_name='চেয়ারম্যানের স্বাক্ষর যুক্ত হয়েছে')
    
    # Controller related fields
    sent_to_controller_at = models.DateTimeField(null=True, blank=True, verbose_name='কন্ট্রোলে পাঠানোর সময়')
    controller_approved_at = models.DateTimeField(null=True, blank=True, verbose_name='কন্ট্রোলার অনুমোদনের সময়')
    controller_approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='controller_approved_bills', 
        verbose_name='কন্ট্রোলার অনুমোদনকারী'
    )

    # Return/Rollback related fields
    is_returned = models.BooleanField(default=False, verbose_name='ফেরত পাঠানো হয়েছে')
    return_reason = models.TextField(blank=True, null=True, verbose_name='ফেরত পাঠানোর কারণ')
    returned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_bills',
        verbose_name='ফেরতকারী'
    )
    returned_at = models.DateTimeField(null=True, blank=True, verbose_name='ফেরত পাঠানোর সময়')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'বিল'
        verbose_name_plural = 'বিলগুলি'

    def save(self, *args, **kwargs):
        """Auto-generate bill number, voucher number, and bangla date if not set"""
        if not self.bill_number:
            self.bill_number = f"{datetime.now().strftime('%Y%m')}-{random.randint(1, 99999)}"
        if not self.voucher_number:
            self.voucher_number = f"{datetime.now().strftime('%Y%m')}-{random.randint(1, 99999)}"
        if not self.bangla_date:
            self.bangla_date = self.get_bangla_date()
        super().save(*args, **kwargs)

    def get_bangla_date(self):
        """Convert English date to Bengali digits"""
        english_to_bangla_digits = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
        today = datetime.now()
        return today.strftime('%d-%m-%Y').translate(english_to_bangla_digits)

    def get_status_badge(self):
        """Return styled HTML badge for status"""
        status_colors = {
            'draft': 'secondary',
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'paid': 'info',
            'sent_to_controller': 'primary',
            'approved_by_controller': 'success',
            'rejected_by_controller': 'danger',
        }
        color = status_colors.get(self.status, 'secondary')
        
        status_display = {
            'draft': 'খসড়া',
            'pending': 'অপেক্ষমান',
            'approved': 'অনুমোদিত',
            'rejected': 'বাতিল',
            'paid': 'পরিশোধিত',
            'sent_to_controller': 'কন্ট্রোলারে প্রেরিত',
            'approved_by_controller': 'কন্ট্রোলার কর্তৃক অনুমোদিত',
            'rejected_by_controller': 'কন্ট্রোলার কর্তৃক বাতিল',
        }
        label = status_display.get(self.status, self.status)
        
        return f'<span class="badge bg-{color}">{label}</span>'

    def __str__(self):
        return f"বিল {self.bill_number}"

# --------------------------
# Task Model
# --------------------------
class Task(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='tasks')
    work_type = models.CharField(max_length=100, verbose_name='কাজের ধরণ')
    benefit = models.CharField(max_length=100, verbose_name='উপকাজ')
    quantity = models.PositiveIntegerField(default=1, verbose_name='পরিমাণ')
    unit = models.CharField(max_length=50, blank=True, verbose_name='একক')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='টাকার পরিমাণ')
    remarks = models.TextField(blank=True, null=True, verbose_name='মন্তব্য') 

    class Meta:
        verbose_name = 'কাজ'
        verbose_name_plural = 'কাজগুলি'

    def __str__(self):
        if self.unit and self.quantity > 1:
            return f"{self.work_type} - {self.benefit} ({self.quantity} {self.unit})"
        return f"{self.work_type} - {self.benefit}"


# --------------------------
# System Settings Model
# --------------------------
class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.key


# --------------------------
# Activity Log Model
# --------------------------
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username if self.user else 'System'} - {self.action}"
