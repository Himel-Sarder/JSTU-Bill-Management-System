from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Profile, Bill, WorkType, Benefit


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
        fields = ['username', 'email', 'first_name', 'password1', 'password2', 'user_type']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']

        if commit:
            user.save()
            profile = Profile.objects.get(user=user)
            profile.user_type = self.cleaned_data['user_type']
            profile.save()

        return user

class ProfileUpdateForm(forms.ModelForm):
    # Add user fields to the form
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='নাম',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Profile
        fields = ['phone_number', 'profile_picture']  # Include profile_picture
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ফোন নম্বর'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_profile_picture'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate user fields from the user instance
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['email'].initial = self.instance.user.email

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
    class Meta:
        model = Bill
        fields = ['semester', 'bank_name', 'bank_branch', 'account_number', 'routing_number']
        widgets = {
            'semester': forms.Select(attrs={'class': 'form-control'}),
            'bank_name': forms.Select(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'শাখার নাম'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'একাউন্ট নাম্বার'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'রাউটিং নাম্বার'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_name'].required = False
        self.fields['bank_branch'].required = False
        self.fields['account_number'].required = False
        self.fields['routing_number'].required = False


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