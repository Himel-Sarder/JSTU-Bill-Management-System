from django.db import models
from decimal import Decimal
import os
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save

_EN_TO_BN_DIGITS = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')


def to_bengali_digits(value):
    """'2022' -> '২০২২'. Used for exam year / session labels."""
    try:
        return str(value).translate(_EN_TO_BN_DIGITS)
    except Exception:
        return value

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
    # No `default=` here on purpose: it used to point at 'profile_pics/default.png',
    # a file that does not ship with the project, so the field was always truthy
    # and every user without an upload got a broken image. Blank now means blank,
    # and the template falls back to a generated initials avatar.
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True,
                                        verbose_name='প্রোফাইল ছবি')
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name='ফোন নম্বর')
    joining_date = models.DateField(blank=True, null=True, verbose_name='যোগদানের তারিখ')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='members', verbose_name='বিভাগ')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Signature fields for different users
    signature = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name='স্বাক্ষর')
    signature_general = models.ImageField(upload_to='signatures/general/', blank=True, null=True, verbose_name='সাধারণ স্বাক্ষর')
    # Which academic year this chairman is responsible for. Replaces the old
    # scheme where the year was inferred from the username (JSTUChairman1..4),
    # which capped the whole university at four chairmen.
    chairman_year = models.CharField(max_length=20, blank=True, null=True,
                                     choices=[('১ম বর্ষ', '১ম বর্ষ'), ('২য় বর্ষ', '২য় বর্ষ'),
                                              ('৩য় বর্ষ', '৩য় বর্ষ'), ('৪র্থ বর্ষ', '৪র্থ বর্ষ'),
                                              ('মাস্টার্স', 'মাস্টার্স')],
                                     verbose_name='চেয়ারম্যানের বর্ষ',
                                     help_text='পদবী চেয়ারম্যান হলে কোন বর্ষের দায়িত্বে।')
    # One signature per chairman. The four numbered fields below are legacy.
    signature_chairman = models.ImageField(upload_to='signatures/chairman/', blank=True, null=True,
                                           verbose_name='চেয়ারম্যানের স্বাক্ষর')
    signature_chairman1 = models.ImageField(upload_to='signatures/chairman1/', blank=True, null=True, verbose_name='চেয়ারম্যান ১ স্বাক্ষর')
    signature_chairman2 = models.ImageField(upload_to='signatures/chairman2/', blank=True, null=True, verbose_name='চেয়ারম্যান ২ স্বাক্ষর')
    signature_chairman3 = models.ImageField(upload_to='signatures/chairman3/', blank=True, null=True, verbose_name='চেয়ারম্যান ৩ স্বাক্ষর')
    signature_chairman4 = models.ImageField(upload_to='signatures/chairman4/', blank=True, null=True, verbose_name='চেয়ারম্যান ৪ স্বাক্ষর')

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"

    @property
    def display_name(self):
        """Full name if we have one, otherwise the username."""
        return self.user.get_full_name().strip() or self.user.username

    @property
    def initials(self):
        """First letters of the display name - used for the fallback avatar."""
        parts = [p for p in self.display_name.split() if p]
        if not parts:
            return '?'
        if len(parts) == 1:
            return parts[0][:1].upper()
        return (parts[0][:1] + parts[-1][:1]).upper()

    @property
    def has_picture(self):
        """True only when a real, readable file is behind the field."""
        field = self.profile_picture
        if not field:
            return False
        try:
            return field.storage.exists(field.name)
        except Exception:
            return False

    @property
    def is_chairman(self):
        return self.user_type == 'চেয়ারম্যান'

    @property
    def active_chairman_signature(self):
        """This chairman's signature.

        Prefers the single `signature_chairman` field; falls back to whichever
        legacy numbered field matches their year, so accounts migrated from the
        JSTUChairman1..4 scheme keep working without re-uploading.
        """
        if self.signature_chairman:
            return self.signature_chairman
        legacy = {
            '১ম বর্ষ': self.signature_chairman1,
            '২য় বর্ষ': self.signature_chairman2,
            '৩য় বর্ষ': self.signature_chairman3,
            '৪র্থ বর্ষ': self.signature_chairman4,
        }
        return legacy.get(self.chairman_year or '')

    def signature_for(self, slot):
        """Return the signature field for 'general' or 'chairman1'..'chairman4'."""
        return getattr(self, f'signature_{slot}', None)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Make sure every User always has a Profile.

    Also covers users created outside the signup form (createsuperuser,
    the admin, a shell, a data import), which previously could end up
    with no profile at all and blow up on `user.profile`.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
        return

    # Existing user with no profile row yet - heal it rather than
    # letting every `user.profile` access raise RelatedObjectDoesNotExist.
    if not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance)


# NOTE: there used to be a second post_save receiver here that ran
# `instance.profile.save()` on EVERY User.save(). It was silently
# destroying data: `instance.profile` returns the object cached on the
# user, so any User.save() re-wrote whatever that stale copy held.
#
# The concrete symptom: registration stored user_type correctly, then
# login() bumped last_login -> User.save() -> the receiver re-saved the
# stale profile (user_type='') and wiped the newly chosen পদবী.
#
# Nothing depends on the cascade - every caller that changes a profile
# field already calls profile.save() itself - so it is gone.


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

# --------------------------
# Department Model
# --------------------------
class Department(models.Model):
    """An academic department. Added and edited from the admin panel.

    Everything that used to assume Computer Science - bills, users, work types
    - now hangs off this.
    """

    name = models.CharField(max_length=150, unique=True, verbose_name='বিভাগের নাম')
    short_name = models.CharField(max_length=20, blank=True, verbose_name='সংক্ষিপ্ত নাম',
                                  help_text='যেমন: CSE, EEE')
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়',
                                    help_text='নিষ্ক্রিয় করলে নতুন বিল বা ব্যবহারকারীতে দেখা যাবে না।')
    order = models.PositiveIntegerField(default=0, verbose_name='ক্রম')

    class Meta:
        verbose_name = 'বিভাগ'
        verbose_name_plural = 'বিভাগসমূহ'
        ordering = ['order', 'name']

    @property
    def display_name(self):
        """Name as it appears on the PDF header, always ending in 'বিভাগ'."""
        name = (self.name or '').strip()
        return name if name.endswith('বিভাগ') else f'{name} বিভাগ'

    def __str__(self):
        if self.short_name:
            return f'{self.name} ({self.short_name})'
        return self.name


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
    department = models.ForeignKey('Department', on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='work_types', verbose_name='বিভাগ',
                                   help_text='খালি রাখলে সব বিভাগের জন্য প্রযোজ্য হবে।')
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়')
    order = models.PositiveIntegerField(default=0, verbose_name='ক্রম')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'কাজের ধরণ'
        verbose_name_plural = 'কাজের ধরণসমূহ'
        # Remove unique constraint on name alone, make it unique with degree_type
        unique_together = ['name', 'degree_type', 'department']

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
# --------------------------
# Academic Session (admin-managed, e.g. 2021-2022)
# --------------------------
class AcademicSession(models.Model):
    """An academic session such as 2021-2022.

    Managed from the admin. The exam year for a session is its END year, so
    session 2021-2022 gives exam year 2022.
    """

    start_year = models.PositiveIntegerField(verbose_name='সেশন শুরুর বছর')
    end_year = models.PositiveIntegerField(verbose_name='সেশন শেষের বছর')
    is_active = models.BooleanField(
        default=True,
        verbose_name='সক্রিয়',
        help_text='নিষ্ক্রিয় করলে নতুন বিলে এই সেশনটি আর দেখা যাবে না।'
    )

    class Meta:
        verbose_name = 'শিক্ষাবর্ষ (সেশন)'
        verbose_name_plural = 'শিক্ষাবর্ষ (সেশন)'
        ordering = ['-start_year']
        unique_together = ['start_year', 'end_year']

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_year and self.end_year and self.end_year <= self.start_year:
            raise ValidationError({'end_year': 'সেশন শেষের বছর শুরুর বছরের পরে হতে হবে।'})

    @property
    def label(self):
        """'2021-2022' in English digits."""
        return f'{self.start_year}-{self.end_year}'

    @property
    def label_bn(self):
        """'২০২১-২০২২' in Bengali digits."""
        return to_bengali_digits(self.label)

    @property
    def exam_year(self):
        """Exam year = the second (end) year of the session."""
        return self.end_year

    @property
    def exam_year_bn(self):
        return to_bengali_digits(self.exam_year)

    def __str__(self):
        return self.label_bn


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

    # Year + semester replace the old flat 1st..8th semester list.
    # Semester is now only 1st/2nd; which year it belongs to is explicit.
    ACADEMIC_YEAR_CHOICES = [
        ('১ম বর্ষ', '১ম বর্ষ'),
        ('২য় বর্ষ', '২য় বর্ষ'),
        ('৩য় বর্ষ', '৩য় বর্ষ'),
        ('৪র্থ বর্ষ', '৪র্থ বর্ষ'),
        # Masters has no 1st..4th year, but it still needs a session and an
        # exam year, so it rides the same field rather than a separate branch.
        ('মাস্টার্স', 'মাস্টার্স'),
    ]

    EXAM_SEMESTER_CHOICES = [
        ('১ম সেমিস্টার', '১ম সেমিস্টার'),
        ('২য় সেমিস্টার', '২য় সেমিস্টার'),
    ]

    # Maps a legacy 1st..8th semester value onto (year, semester)
    # Digits used in the controller bill number: ৩য় বর্ষ + ২য় সেমিস্টার -> '32'
    YEAR_CODE = {'১ম বর্ষ': '1', '২য় বর্ষ': '2', '৩য় বর্ষ': '3',
                 '৪র্থ বর্ষ': '4', 'মাস্টার্স': '5'}
    SEMESTER_CODE = {'১ম সেমিস্টার': '1', '২য় সেমিস্টার': '2'}

    LEGACY_SEMESTER_MAP = {
        '১ম সেমিস্টার': ('১ম বর্ষ', '১ম সেমিস্টার'),
        '২য় সেমিস্টার': ('১ম বর্ষ', '২য় সেমিস্টার'),
        '৩য় সেমিস্টার': ('২য় বর্ষ', '১ম সেমিস্টার'),
        '৪র্থ সেমিস্টার': ('২য় বর্ষ', '২য় সেমিস্টার'),
        '৫ম সেমিস্টার': ('৩য় বর্ষ', '১ম সেমিস্টার'),
        '৬ষ্ঠ সেমিস্টার': ('৩য় বর্ষ', '২য় সেমিস্টার'),
        '৭ম সেমিস্টার': ('৪র্থ বর্ষ', '১ম সেমিস্টার'),
        '৮ম সেমিস্টার': ('৪র্থ বর্ষ', '২য় সেমিস্টার'),
        'মাস্টার্স': ('মাস্টার্স', '১ম সেমিস্টার'),
    }

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('sent_to_controller', 'Sent to Controller'),
        ('approved_by_controller', 'Approved by Controller'),
        ('rejected_by_controller', 'Rejected by Controller'),
        ('controller_returned', 'Returned to Chairman by Controller'),
        ('returned_to_user', 'Returned to User'),
    ]

    bill_number = models.CharField(max_length=50, unique=True, verbose_name='বিল নম্বর')
    # Assigned only when the controller approves the bill. Format is
    # <exam year>-<year><semester>-<serial>, e.g. 2022-32-1 for the 1st
    # controller-approved 3rd-year 2nd-semester bill of exam year 2022.
    controller_bill_number = models.CharField(max_length=50, unique=True, null=True, blank=True,
                                             verbose_name='কন্ট্রোলার বিল নম্বর')
    voucher_number = models.CharField(max_length=50, unique=True, verbose_name='ভাউচার নম্বর')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='ব্যবহারকারী')
    # Legacy column, kept so historical bills keep rendering. New bills leave
    # it blank and use academic_year + exam_semester + session instead.
    semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, blank=True, null=True,
                                verbose_name='সেমিস্টার (পুরাতন)')
    academic_year = models.CharField(max_length=20, choices=ACADEMIC_YEAR_CHOICES, blank=True, null=True,
                                     verbose_name='বর্ষ')
    exam_semester = models.CharField(max_length=20, choices=EXAM_SEMESTER_CHOICES, blank=True, null=True,
                                     verbose_name='সেমিস্টার')
    session = models.ForeignKey('AcademicSession', on_delete=models.PROTECT, null=True, blank=True,
                                related_name='bills', verbose_name='সেশন')
    department = models.ForeignKey('Department', on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='bills', verbose_name='বিভাগ')
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

    # --------------------------
    # Bill Rollback (ফেরত) Fields
    # --------------------------
    # Controller -> Chairman rollback (a controller-rejected bill sent back to the chairman)
    returned_to_chairman_at = models.DateTimeField(null=True, blank=True, verbose_name='চেয়ারম্যানে ফেরত পাঠানোর সময়')
    returned_to_chairman_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controller_returned_bills',
        verbose_name='ফেরতকারী কন্ট্রোলার'
    )

    # Chairman -> Bill creator rollback (the chairman forwards the controller-returned bill back to its creator)
    returned_to_user_at = models.DateTimeField(null=True, blank=True, verbose_name='ব্যবহারকারীর কাছে ফেরত পাঠানোর সময়')
    returned_to_user_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chairman_returned_bills',
        verbose_name='ফেরতকারী চেয়ারম্যান'
    )

    # How many times the bill creator has edited & resent this rolled-back bill
    resend_count = models.PositiveIntegerField(default=0, verbose_name='পুনঃপ্রেরণ সংখ্যা')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'বিল'
        verbose_name_plural = 'বিলগুলি'

    @staticmethod
    def _next_serial(prefix, field='bill_number'):
        """Next free serial for a '<prefix>-<n>' numbering scheme.

        Reads the highest existing serial rather than counting rows, so
        deleting a bill never causes a number to be reused.
        """
        existing = Bill.objects.filter(**{f'{field}__startswith': f'{prefix}-'}) \
                               .values_list(field, flat=True)
        highest = 0
        for value in existing:
            tail = (value or '').rsplit('-', 1)[-1]
            if tail.isdigit():
                highest = max(highest, int(tail))
        return highest + 1

    def save(self, *args, **kwargs):
        """Auto-generate bill number, voucher number, and bangla date if not set"""
        if not self.bill_number:
            # <current year>-<serial>, e.g. 2026-1. Retried on collision so two
            # people saving at the same moment cannot take the same number.
            year = datetime.now().strftime('%Y')
            for _ in range(10):
                candidate = f"{year}-{self._next_serial(year)}"
                if not Bill.objects.filter(bill_number=candidate).exists():
                    self.bill_number = candidate
                    break
            else:
                self.bill_number = f"{year}-{random.randint(100000, 999999)}"
        if not self.voucher_number:
            self.voucher_number = f"{datetime.now().strftime('%Y%m')}-{random.randint(1, 99999)}"
        if not self.bangla_date:
            self.bangla_date = self.get_bangla_date()

        # Keep the legacy `semester` column in step with year + semester, so
        # older reports and exports that still read it keep working.
        #
        # NOTE: this used to live in a SECOND save() further down the class.
        # Python keeps only the last definition, so that one silently replaced
        # this method and bill/voucher numbers stopped being generated at all --
        # every new bill got an empty number and the second one hit a UNIQUE
        # constraint. Both behaviours now live in this single save().
        if self.academic_year and self.exam_semester and not self.semester:
            for legacy, (year_label, sem) in self.LEGACY_SEMESTER_MAP.items():
                if year_label == self.academic_year and sem == self.exam_semester:
                    self.semester = legacy
                    break

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
            'controller_returned': 'warning',
            'returned_to_user': 'warning',
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
            'controller_returned': 'কন্ট্রোলার ফেরত',
            'returned_to_user': 'ফেরত বিল',
        }
        label = status_display.get(self.status, self.status)
        
        return f'<span class="badge bg-{color}">{label}</span>'

    def get_controller_comment(self):
        """Return the most recent controller comment saved in remarks, if any."""
        if not self.remarks:
            return ''
        marker = 'কন্ট্রোলার মন্তব্য:'
        lines = [line.strip() for line in self.remarks.split('\n') if marker in line]
        if not lines:
            return ''
        last_line = lines[-1]
        return last_line.split(marker, 1)[1].strip()

    def get_chairman_return_note(self):
            """Return the most recent chairman note added while returning the bill to the user."""
            if not self.remarks:
                return ''
            markers = ['চেয়ারম্যান মন্তব্য (ফেরত):', 'চেয়ারম্যান কর্তৃক বাতিল (ফেরত):']
            lines = [line.strip() for line in self.remarks.split('\n') if any(m in line for m in markers)]
            if not lines:
                return ''
            last_line = lines[-1]
            for m in markers:
                if m in last_line:
                    return last_line.split(m, 1)[1].strip()
            return ''

    # ── Exam heading ────────────────────────────────────────────────
    #
    # Renders as e.g. "৩য় বর্ষ ২য় সেমিস্টার পরীক্ষা - ২০২২", which is what the
    # PDF heading and the bill lists show. Bills created before the year/
    # semester split fall back to their legacy `semester` value, so nothing
    # historical loses its heading.

    # ── Bill numbers ────────────────────────────────────────────────

    @property
    def year_semester_code(self):
        """'32' for ৩য় বর্ষ + ২য় সেমিস্টার, or '' if either is unknown."""
        year = self.YEAR_CODE.get(self.resolved_academic_year or '')
        semester = self.SEMESTER_CODE.get(self.exam_semester or '')
        if not year or not semester:
            return ''
        return f'{year}{semester}'

    def assign_controller_bill_number(self, force=False):
        """Give this bill its controller number, once the controller approves.

        Format: <exam year>-<year><semester>-<serial>, e.g. 2022-32-1. The
        serial restarts for each exam-year + year-semester group, so the first
        approved 3rd-year 2nd-semester bill of 2022 is number 1.

        Idempotent: a bill that already has a number keeps it, so re-approving
        or re-saving never renumbers a bill that has been printed.
        """
        if self.controller_bill_number and not force:
            return self.controller_bill_number

        exam_year = self.exam_year
        code = self.year_semester_code
        if not exam_year or not code:
            # Not enough information (no session, or no year/semester). Leave it
            # unset rather than inventing a number that means nothing.
            return None

        prefix = f'{exam_year}-{code}'
        for _ in range(10):
            candidate = f'{prefix}-{self._next_serial(prefix, "controller_bill_number")}'
            if not Bill.objects.filter(controller_bill_number=candidate).exists():
                self.controller_bill_number = candidate
                self.save(update_fields=['controller_bill_number'])
                return candidate
        return None

    @property
    def bill_number_bn(self):
        """Creation number in Bengali digits."""
        return to_bengali_digits(self.bill_number or '')

    @property
    def controller_bill_number_bn(self):
        """Controller number in Bengali digits, blank until approved."""
        return to_bengali_digits(self.controller_bill_number or '')

    @property
    def display_bill_number(self):
        """What the PDF prints in the bill-number box.

        Deliberately BLANK until the controller approves. The number that goes
        on a printed bill is the controller's (<exam year>-<year><semester>-<n>);
        the creation number is internal and never appears on the PDF. It is
        still shown to the user and the chairman in the web UI alongside it.
        """
        return self.controller_bill_number_bn

    @property

    def year_semester(self):

        """'৩য় বর্ষ ২য় সেমিস্টার', or the legacy value for older bills."""
        parts = [p for p in (self.academic_year, self.exam_semester) if p]
        if parts:
            return ' '.join(parts)
        return self.semester or ''

    @property
    def exam_year(self):
        """Exam year = the session's end year (2021-2022 -> 2022)."""
        return self.session.exam_year if self.session_id else None

    @property
    def exam_year_bn(self):
        year = self.exam_year
        return to_bengali_digits(year) if year else ''

    @property
    def resolved_academic_year(self):
        """This bill's academic year, from the field or the legacy semester."""
        if self.academic_year:
            return self.academic_year
        for legacy, (year, _sem) in self.LEGACY_SEMESTER_MAP.items():
            if legacy == self.semester:
                return year
        return None

    @property
    def chairman(self):
        """The chairman who owns this bill: same academic year AND department.

        Replaces the old lookup that matched a hardcoded username parsed out of
        bill.remarks. With several departments each year has its own chairman
        per department, so the department has to be part of the match.
        """
        year = self.resolved_academic_year
        if not year:
            return None
        qs = User.objects.filter(profile__user_type='চেয়ারম্যান',
                                 profile__chairman_year=year)
        if self.department_id:
            qs = qs.filter(profile__department=self.department_id)
        return qs.first()

    @property
    def exam_title(self):
        """Full heading: '৩য় বর্ষ ২য় সেমিস্টার পরীক্ষা - ২০২২'."""
        label = self.year_semester
        title = f'{label} পরীক্ষা'.strip() if label else 'পরীক্ষা'
        if self.exam_year:
            title = f'{title} - {self.exam_year_bn}'
        return title

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


# --------------------------
# Chairman Document Model
# --------------------------
class ChairmanDocument(models.Model):
    """A file a chairman uploads and can forward to the controller.

    Files are NOT served straight from MEDIA_URL. They go through a
    permission-checked download view so only the uploader and the controller
    (and only once it has been sent) can reach them.
    """

    ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png']
    MAX_SIZE_MB = 10

    title = models.CharField(max_length=200, verbose_name='শিরোনাম')
    file = models.FileField(upload_to='chairman_documents/%Y/%m/', verbose_name='ফাইল')
    note = models.TextField(blank=True, verbose_name='নোট',
                            help_text='কন্ট্রোলারের জন্য ঐচ্ছিক বার্তা')

    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='chairman_documents',
                                    verbose_name='আপলোডকারী')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='আপলোডের সময়')

    is_sent = models.BooleanField(default=False, verbose_name='কন্ট্রোলারে পাঠানো হয়েছে')
    is_read = models.BooleanField(default=False, verbose_name='কন্ট্রোলার দেখেছেন')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='দেখার সময়')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='পাঠানোর সময়')

    class Meta:
        verbose_name = 'চেয়ারম্যানের ফাইল'
        verbose_name_plural = 'চেয়ারম্যানের ফাইল'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    # ── File helpers ────────────────────────────────────────────────

    @property
    def filename(self):
        """Just the file name, without the upload_to directories."""
        return os.path.basename(self.file.name) if self.file else ''

    @property
    def extension(self):
        """Lower-case extension with no dot, e.g. 'pdf'."""
        return os.path.splitext(self.file.name)[1].lstrip('.').lower() if self.file else ''

    @property
    def is_pdf(self):
        """PDFs can be previewed in the browser; everything else downloads."""
        return self.extension == 'pdf'

    @property
    def size_display(self):
        """'১.৪ MB' / '২৩৮ KB' — blank if the file has gone missing."""
        try:
            size = self.file.size
        except Exception:
            return ''
        if size >= 1024 * 1024:
            return to_bengali_digits(f'{size / (1024 * 1024):.1f}') + ' MB'
        return to_bengali_digits(max(1, size // 1024)) + ' KB'

    @property
    def exists_on_disk(self):
        """False when the row survives but the file behind it is gone."""
        if not self.file:
            return False
        try:
            return self.file.storage.exists(self.file.name)
        except Exception:
            return False

    def mark_sent(self):
        """Forward to the controller. Idempotent - re-sending keeps the
        original timestamp so the controller's ordering stays stable."""
        if not self.is_sent:
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save(update_fields=['is_sent', 'sent_at'])
        return self

    def mark_read(self):
        """Record the first time the controller opened this file."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
        return self

    def can_be_viewed_by(self, user):
        """Uploader always; controller only once it has been sent."""
        if not user.is_authenticated:
            return False
        if self.uploaded_by_id == user.id:
            return True
        profile = getattr(user, 'profile', None)
        if profile and profile.user_type == 'কন্ট্রোলার':
            return self.is_sent
        return False


# --------------------------
# Tax Setting
# --------------------------
class TaxSetting(models.Model):
    """The tax percentage deducted on the controller's accepted-bill report.

    Managed from the admin. The most recently updated active row is the one in
    force, so changing the rate is just adding or editing a row -- old reports
    are unaffected because the rate is applied at render time.
    """

    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='করের হার (%)',
        help_text='যেমন: ১০ লিখলে মোট টাকার ১০% কর কাটা হবে।')
    label = models.CharField(max_length=100, blank=True, verbose_name='নাম',
                             help_text='ঐচ্ছিক, যেমন: আয়কর')
    is_active = models.BooleanField(default=True, verbose_name='সক্রিয়')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='সর্বশেষ পরিবর্তন')

    class Meta:
        verbose_name = 'কর (ট্যাক্স) সেটিং'
        verbose_name_plural = 'কর (ট্যাক্স) সেটিং'
        ordering = ['-updated_at']

    @classmethod
    def current_rate(cls):
        """Active tax rate as a Decimal percentage; 0 when none is set."""
        row = cls.objects.filter(is_active=True).order_by('-updated_at').first()
        return row.percentage if row else Decimal('0')

    @classmethod
    def tax_on(cls, amount, rate=None):
        """Tax owed on an amount, rounded to 2 decimal places."""
        rate = cls.current_rate() if rate is None else rate
        amount = Decimal(str(amount or 0))
        return (amount * Decimal(str(rate)) / Decimal('100')).quantize(Decimal('0.01'))

    def __str__(self):
        name = self.label or 'কর'
        return f'{name}: {self.percentage}%'