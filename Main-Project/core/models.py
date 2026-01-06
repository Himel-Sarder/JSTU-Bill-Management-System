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
        ('অ্যাসিস্ট্যান্ট প্রফেসর', 'অ্যাসিস্ট্যান্ট প্রফেসর'),
        ('লেকচারার', 'লেকচারার'),
        ('অফিস সহকারী', 'অফিস সহকারী'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=50, choices=USER_TYPES, verbose_name='পদবী')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.png', verbose_name='প্রোফাইল ছবি')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='ফোন নম্বর')
    joining_date = models.DateField(blank=True, null=True, verbose_name='যোগদানের তারিখ')

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
    title = models.CharField(max_length=200, verbose_name='শিরোনাম')
    image = models.ImageField(upload_to='slider_images/', verbose_name='ছবি')
    description = models.TextField(verbose_name='বর্ণনা')
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়')
    order = models.PositiveIntegerField(default=0, verbose_name='ক্রম')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title


# --------------------------
# Bill Model
# --------------------------
class Bill(models.Model):
    # Bank Information Fields
    BANK_CHOICES = [
        ('জনতা ব্যাংক', 'জনতা ব্যাংক'),
        ('ডাচ বাংলা ব্যাংক', 'ডাচ বাংলা ব্যাংক'),
        ('সোনালী ব্যাংক', 'সোনালী ব্যাংক'),
        ('ইসলামী ব্যাংক', 'ইসলামী ব্যাংক'),
    ]
    
    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES, blank=True, null=True, verbose_name='ব্যাংকের নাম')
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
    ]

    WORK_TYPE_CHOICES = [
        ('প্রশ্নপত্র প্রণয়ন', 'প্রশ্নপত্র প্রণয়ন'),
        ('উত্তরপত্র মূল্যায়ন', 'উত্তরপত্র মূল্যায়ন'),
        ('ভাইভা', 'ভাইভা'),
        ('প্র্যাকটিক্যাল', 'প্র্যাকটিক্যাল'),
        ('ক্লাস টেস্ট', 'ক্লাস টেস্ট'),
        ('প্রশ্নপত্র সমীক্ষণ', 'প্রশ্নপত্র সমীক্ষণ'),
        ('পরীক্ষা কমিটির সম্মানী', 'পরীক্ষা কমিটির সম্মানী'),
        ('প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং', 'প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং'),
        ('প্রশ্নপত্র কম্পোজ', 'প্রশ্নপত্র কম্পোজ'),
        
    ]

    BENEFIT_CHOICES = {
        'প্রশ্নপত্র প্রণয়ন': [
            ('তাত্ত্বিক (২ ঘন্টা)', 'তাত্ত্বিক (২ ঘন্টা)'),
            ('তাত্ত্বিক (৩ ঘণ্টা)', 'তাত্ত্বিক (৩ ঘণ্টা)'),
            ('তাত্ত্বিক (৪ ঘন্টা)', 'তাত্ত্বিক (৪ ঘন্টা)'),
            ('ক্লাস টেস্ট (১ ঘন্টা)', 'ক্লাস টেস্ট (১ ঘন্টা)'),
            ('মিড টার্ম (১.৫ ঘন্টা)', 'মিড টার্ম (১.৫ ঘন্টা)'),
        ],
        'উত্তরপত্র মূল্যায়ন': [
            ('তাত্ত্বিক ২ ঘন্টা-', 'তাত্ত্বিক ২ ঘন্টা'),
            ('তাত্ত্বিক ৩ ঘণ্টা-', 'তাত্ত্বিক ৩ ঘণ্টা'),
            ('তাত্ত্বিক (৪ ঘন্টা)-', 'তাত্ত্বিক (৪ ঘন্টা)'),
        ],
        'অভ্যন্তরীণ মূল্যয়ন (ক্লাস টেস্ট)': [
            ('অভ্যন্তরীণ মূল্যয়ন (ক্লাস টেস্ট)', 'অভ্যন্তরীণ মূল্যয়ন (ক্লাস টেস্ট)'),
        ],
        'ভাইভা': [
            ('ভাইভা ১ ঘন্টা', 'ভাইভা ১ ঘন্টা'),
        ],
        'ব্যবহারিক': [
            ('ব্যবহারিক', 'ব্যবহারিক'),
        ],
        'প্রশ্নপত্র সমীক্ষণ': [
            ('প্রশ্নপত্র সমীক্ষণ', 'প্রশ্নপত্র সমীক্ষণ'),
        ],
        'পরীক্ষা কমিটির সম্মানী': [
            ('সভাপতির সম্মানী (১ম, ২য় ও ৩য় বর্ষ)', 'সভাপতির সম্মানী (১ম, ২য় ও ৩য় বর্ষ)'),
            ('সভাপতির সম্মানী (৪র্থ বর্ষ)', 'সভাপতির সম্মানী (৪র্থ বর্ষ)'),
            ('প্রতি সেমিস্টারে আপ্যায়ন ও মোবাইল ভাতা', 'প্রতি সেমিস্টারে আপ্যায়ন ও মোবাইল ভাতা'),
            ('সদস্যের সম্মানী', 'সদস্যের সম্মানী'),
        ],
        'প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং':[
            ('প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং', 'প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং'),
        ],
        'প্রশ্নপত্র কম্পোজ': [
            ('প্রশ্নপত্র কম্পোজ', 'প্রশ্নপত্র কম্পোজ'),
        ],

    }

    AMOUNT_MAPPING = {
        'তাত্ত্বিক (২ ঘন্টা)': 1600,
        'তাত্ত্বিক (৩ ঘণ্টা)': 2000,
        'তাত্ত্বিক (৪ ঘন্টা)': 2400,
        'অভ্যন্তরীণ মূল্যয়ন (ক্লাস টেস্ট)': 900,
        'ক্লাস টেস্ট (১ ঘন্টা)': 300,
        'মিড টার্ম (১.৫ ঘন্টা)': 400,
        'ভাইভা ১ ঘন্টা': 500,
        'ব্যবহারিক': 600,
        'টিউটোরিয়াল ১ ঘন্টা': 400,
        'তাত্ত্বিক ২ ঘন্টা-': 1000,
        'তাত্ত্বিক ৩ ঘণ্টা-': 1000,
        'তাত্ত্বিক (৪ ঘন্টা)-': 1000,
        'প্রশ্নপত্র সমীক্ষণ': 2000,
        'সভাপতির সম্মানী (১ম, ২য় ও ৩য় বর্ষ)': 3500,
        'সভাপতির সম্মানী (৪র্থ বর্ষ)': 4000,
        'প্রতি সেমিস্টারে আপ্যায়ন ও মোবাইল ভাতা': 1500,
        'সদস্যের সম্মানী': 1500,
        'প্রশ্নপত্র প্রিন্টিং ও প্যাকেজিং': 1000,
        'প্রশ্নপত্র কম্পোজ': 300,



    }

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    bill_number = models.CharField(max_length=50, unique=True, verbose_name='বিল নম্বর')
    voucher_number = models.CharField(max_length=50, unique=True, verbose_name='ভাউচার নম্বর')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='ব্যবহারকারী')
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, verbose_name='সেমিস্টার')
    department = models.CharField(max_length=100, default='কম্পিউটার বিজ্ঞান এবং প্রকৌশল', verbose_name='বিভাগ')
    bangla_date = models.CharField(max_length=50, verbose_name='বাংলা তারিখ')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='মোট টাকা')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='স্ট্যাটাস')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_bills', verbose_name='অনুমোদনকারী')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='অনুমোদনের সময়')
    remarks = models.TextField(blank=True, null=True, verbose_name='মন্তব্য')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'বিল'
        verbose_name_plural = 'বিলগুলি'

    def save(self, *args, **kwargs):
        """Auto-generate bill number, voucher number, and bangla date if not set"""
        if not self.bill_number:
            self.bill_number = f"{datetime.now().strftime('%Y%m')}-{random.randint(10, 99)}"
        if not self.voucher_number:
            self.voucher_number = f"{datetime.now().strftime('%Y%m')}-{random.randint(10, 99)}"
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
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'paid': 'info'
        }
        color = status_colors.get(self.status, 'secondary')
        return f'<span class="badge bg-{color}">{self.get_status_display()}</span>'

    def __str__(self):
        return f"বিল {self.bill_number}"


# --------------------------
# Task Model
# --------------------------
class Task(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='tasks')
    work_type = models.CharField(max_length=50, choices=Bill.WORK_TYPE_CHOICES, verbose_name='কাজের ধরণ')
    benefit = models.CharField(max_length=50, verbose_name='উপকাজ')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='টাকার পরিমাণ')

    class Meta:
        verbose_name = 'কাজ'
        verbose_name_plural = 'কাজগুলি'

    def __str__(self):
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
