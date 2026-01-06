from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import Profile, Bill, Task, SliderImage

class CustomUserCreationForm(UserCreationForm):
    name = forms.CharField(max_length=100, label='নাম', widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'আপনার সম্পূর্ণ নাম'
    }))
    email = forms.EmailField(label='ইমেইল', widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'আপনার ইমেইল ঠিকানা'
    }))
    user_type = forms.ChoiceField(
        choices=Profile.USER_TYPES,
        label='পদবী',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(max_length=15, required=False, label='ফোন নম্বর', widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': '০১XXXXXXXXX'
    }))

    class Meta:
        model = User
        fields = ['username', 'name', 'email', 'user_type', 'phone_number', 'password1', 'password2']
        labels = {
            'username': 'ইউজার নাম',
            'password1': 'পাসওয়ার্ড',
            'password2': 'পাসওয়ার্ড নিশ্চিত করুন',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ইউজার নাম'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap class to all password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'পাসওয়ার্ড'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'পাসওয়ার্ড নিশ্চিত করুন'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['name']

        if commit:
            user.save()
            profile = user.profile
            profile.user_type = self.cleaned_data['user_type']
            profile.phone_number = self.cleaned_data['phone_number']
            profile.save()

        return user


class ProfileUpdateForm(forms.ModelForm):
    name = forms.CharField(max_length=100, label='নাম', widget=forms.TextInput(attrs={
        'class': 'form-control'
    }))
    email = forms.EmailField(label='ইমেইল', widget=forms.EmailInput(attrs={
        'class': 'form-control'
    }))
    phone_number = forms.CharField(max_length=15, required=False, label='ফোন নম্বর', widget=forms.TextInput(attrs={
        'class': 'form-control'
    }))
    
    class Meta:
        model = Profile
        fields = ['user_type', 'profile_picture', 'phone_number']
        widgets = {
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'user_type': 'পদবী',
            'profile_picture': 'প্রোফাইল ছবি',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['name'].initial = self.instance.user.first_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class TaskForm(forms.Form):
    work_type = forms.ChoiceField(
        choices=Bill.WORK_TYPE_CHOICES,
        label='কাজের ধরণ',
        widget=forms.Select(attrs={'class': 'work-type-select form-control'})
    )
    benefit = forms.ChoiceField(
        choices=[],
        label='উপকাজ',
        widget=forms.Select(attrs={'class': 'benefit-select form-control', 'disabled': True})
    )
    amount = forms.DecimalField(
        label='টাকার পরিমাণ',
        widget=forms.TextInput(attrs={'class': 'amount-input form-control', 'readonly': True})
    )

class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['semester', 'bank_name', 'bank_branch', 'account_number', 'routing_number']
        widgets = {
            'semester': forms.Select(attrs={'class': 'form-control'}),
            'bank_name': forms.Select(attrs={'class': 'form-control'}),
            'bank_branch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'শাখার নাম লিখুন'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'একাউন্ট নাম্বার লিখুন'}),
            'routing_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'রাউটিং নাম্বার লিখুন'}),
        }
        labels = {
            'semester': 'সেমিস্টার',
            'bank_name': 'ব্যাংকের নাম',
            'bank_branch': 'শাখা',
            'account_number': 'একাউন্ট নাম্বার',
            'routing_number': 'রাউটিং নাম্বার',
        }

class BillStatusForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ['status', 'remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'status': 'স্ট্যাটাস',
            'remarks': 'মন্তব্য',
        }

class SliderImageForm(forms.ModelForm):
    class Meta:
        model = SliderImage
        fields = ['title', 'image', 'description', 'is_active', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'শিরোনাম',
            'image': 'ছবি',
            'description': 'বর্ণনা',
            'is_active': 'সক্রিয়',
            'order': 'ক্রম',
        }