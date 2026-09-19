import re
from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.db import models
from .models import Profile, Bill, WorkType, Benefit, AcademicSession, ChairmanDocument, Department


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'আপনার ইমেইল লিখুন'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='নাম',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'আপনার নাম লিখুন'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ইউজারনেম লিখুন'
        })
    )
    user_type = forms.ChoiceField(
        choices=[
            ('অ্যাসিস্ট্যান্ট প্রফেসর', 'অ্যাসিস্ট্যান্ট প্রফেসর'),
            ('লেকচারার', 'লেকচারার'),
            ('অফিস সহকারী', 'অফিস সহকারী'),
        ],
        label='পদবী',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        label='বিভাগ',
        empty_label='-- বিভাগ নির্বাচন করুন --',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'পাসওয়ার্ড লিখুন'
        }),
        label='পাসওয়ার্ড'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'পাসওয়ার্ড আবার লিখুন'
        }),
        label='পাসওয়ার্ড নিশ্চিত করুন'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'password1', 'password2', 'user_type', 'department']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']

        if commit:
            user.save()
            # Write through the instance cached on `user` (not a fresh
            # Profile.objects.get) so `user.profile` reflects the chosen
            # পদবী immediately afterwards - the register view logs the
            # user straight in, and anything reading user.profile in between
            # would otherwise see the empty value from the create signal.
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.user_type = self.cleaned_data['user_type']
            profile.department = self.cleaned_data['department']
            profile.save()
            user.profile = profile

        return user

class ProfileUpdateForm(forms.ModelForm):
    """The details a user edits about themselves.

    Only name, email and phone. The profile picture is handled separately by
    an upload endpoint so it saves the moment it is chosen; joining date,
    পদবী and বিভাগ are administrative and set from the admin panel.
    """

    first_name = forms.CharField(
        max_length=30, required=True, label='নামের প্রথম অংশ',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'প্রথম অংশ'}))
    last_name = forms.CharField(
        max_length=150, required=False, label='নামের শেষ অংশ',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'শেষ অংশ'}))
    email = forms.EmailField(
        required=True, label='ইমেইল',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}))

    class Meta:
        model = Profile
        fields = ['phone_number']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '01XXXXXXXXX',
                'inputmode': 'tel',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].required = False
        user = getattr(self.instance, 'user', None)
        if user is not None:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_first_name(self):
        name = (self.cleaned_data.get('first_name') or '').strip()
        if not name:
            raise forms.ValidationError('নাম লিখুন।')
        return name

    def clean_last_name(self):
        return (self.cleaned_data.get('last_name') or '').strip()

    def clean_email(self):
        """Email must be unique across accounts - it identifies the user."""
        email = (self.cleaned_data.get('email') or '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.user_id:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError('এই ইমেইলটি অন্য একটি অ্যাকাউন্টে ব্যবহৃত হচ্ছে।')
        return email

    def clean_phone_number(self):
        phone = (self.cleaned_data.get('phone_number') or '').strip()
        if not phone:
            return ''
        cleaned = re.sub(r'[\s\-()]', '', phone)
        if not re.fullmatch(r'\+?\d{6,15}', cleaned):
            raise forms.ValidationError(
                'সঠিক ফোন নম্বর লিখুন (বাংলাদেশের জন্য মোবাইল নম্বর, যেমন 01712345678)।')
        return cleaned

    def save(self, commit=True):
        """Persist both the Profile and its User in one call."""
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'পুরাতন পাসওয়ার্ড'}),
        label='পুরাতন পাসওয়ার্ড'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'নতুন পাসওয়ার্ড'}),
        label='নতুন পাসওয়ার্ড'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'নতুন পাসওয়ার্ড নিশ্চিত করুন'}),
        label='নতুন পাসওয়ার্ড নিশ্চিত করুন'
    )


class BillForm(forms.ModelForm):
    """Bill header form.

    The old single 'semester' dropdown (1st..8th) is replaced by an explicit
    year + semester pair plus the academic session. The exam year shown on the
    PDF is derived from the session's end year, so 2021-2022 -> 2022; nobody
    types the exam year by hand.

    bank_name is a free-text field rather than a fixed dropdown, so any
    bank name can be entered - not just the four that used to be hardcoded
    in Bill.BANK_CHOICES.
    """

    class Meta:
        model = Bill
        fields = ['academic_year', 'exam_semester', 'session',
                  'bank_name', 'bank_branch', 'account_number', 'routing_number']
        widgets = {
            'academic_year': forms.Select(attrs={'class': 'form-control', 'id': 'id_academic_year'}),
            'exam_semester': forms.Select(attrs={'class': 'form-control', 'id': 'id_exam_semester'}),
            'session': forms.Select(attrs={'class': 'form-control', 'id': 'id_session'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ব্যাংকের নাম লিখুন'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'শাখার নাম'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'একাউন্ট নাম্বার'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'রাউটিং নাম্বার'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Year / semester / session identify the exam, so they are required
        # even though the columns are nullable (nullable is for legacy rows).
        for name in ('academic_year', 'exam_semester', 'session'):
            self.fields[name].required = True

        self.fields['academic_year'].empty_label = '-- বর্ষ নির্বাচন করুন --'
        self.fields['exam_semester'].empty_label = '-- সেমিস্টার নির্বাচন করুন --'

        # Only sessions the admin has left active are offered. An inactive
        # session already attached to this bill stays selectable so editing an
        # old bill doesn't silently lose it.
        sessions = AcademicSession.objects.filter(is_active=True)
        if self.instance and self.instance.pk and self.instance.session_id:
            sessions = AcademicSession.objects.filter(
                models.Q(is_active=True) | models.Q(pk=self.instance.session_id)
            )
        self.fields['session'].queryset = sessions.order_by('-start_year')
        self.fields['session'].empty_label = '-- সেশন নির্বাচন করুন --'
        self.fields['session'].label_from_instance = lambda obj: obj.label_bn

        self.fields['bank_name'].required = False
        self.fields['bank_branch'].required = False
        self.fields['account_number'].required = False
        self.fields['routing_number'].required = False

    def clean_bank_name(self):
        return (self.cleaned_data.get('bank_name') or '').strip()


class BillStatusForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['status', 'remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'মন্তব্য'}),
        }


class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = WorkType
        fields = ['name', 'description', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'কাজের ধরণের নাম'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'বর্ণনা'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ক্রম'}),
        }


class BenefitForm(forms.ModelForm):
    class Meta:
        model = Benefit
        fields = ['work_type', 'name', 'calculation_type', 'base_amount',
                  'unit_label', 'min_unit', 'max_unit', 'is_active', 'order']
        widgets = {
            'work_type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'উপকাজের নাম'}),
            'calculation_type': forms.Select(attrs={'class': 'form-control'}),
            'base_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '০.০০'}),
            'unit_label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'যেমন: কপি, প্রশ্ন'}),
            'min_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '১'}),
            'max_unit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '১০০'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ক্রম'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work_type'].queryset = WorkType.objects.filter(is_active=True)
        self.fields['unit_label'].required = False


class ChairmanDocumentForm(forms.ModelForm):
    """Chairman file upload: a title plus the file itself."""

    class Meta:
        model = ChairmanDocument
        fields = ['title', 'file', 'note']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ফাইলের শিরোনাম লিখুন',
                'maxlength': 200,
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'id': 'id_document_file',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'কন্ট্রোলারের জন্য নোট (ঐচ্ছিক)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = True
        self.fields['file'].required = True
        self.fields['note'].required = False

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('ফাইলের শিরোনাম লিখুন।')
        return title

    def clean_file(self):
        """Server-side guard - the accept attribute is only a hint."""
        upload = self.cleaned_data.get('file')
        if not upload:
            raise forms.ValidationError('একটি ফাইল নির্বাচন করুন।')

        name = getattr(upload, 'name', '') or ''
        ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
        if ext not in ChairmanDocument.ALLOWED_EXTENSIONS:
            allowed = ', '.join(e.upper() for e in ChairmanDocument.ALLOWED_EXTENSIONS)
            raise forms.ValidationError(f'শুধুমাত্র এই ধরনের ফাইল আপলোড করা যাবে: {allowed}')

        size = getattr(upload, 'size', 0)
        if size > ChairmanDocument.MAX_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f'ফাইলের সাইজ {ChairmanDocument.MAX_SIZE_MB}MB এর কম হতে হবে।')
        if size == 0:
            raise forms.ValidationError('ফাইলটি খালি।')

        return upload
