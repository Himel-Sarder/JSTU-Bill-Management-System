from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Profile, Bill, WorkType, Benefit


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='নাম')
    user_type = forms.ChoiceField(choices=Profile.USER_TYPES, label='পদবী')

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
    class Meta:
        model = Profile
        fields = ['user_type', 'profile_picture', 'phone_number', 'joining_date']
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'})
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='পুরাতন পাসওয়ার্ড'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='নতুন পাসওয়ার্ড'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
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
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# New forms for Work Type and Benefit management
class WorkTypeForm(forms.ModelForm):
    class Meta:
        model = WorkType
        fields = ['name', 'description', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'কাজের ধরণের নাম'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'বর্ণনা'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
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
            'base_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'একক (যেমন: কপি, প্রশ্ন)'}),
            'min_unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_unit': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['work_type'].queryset = WorkType.objects.filter(is_active=True)