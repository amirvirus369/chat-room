from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from .models import CustomUser
from django.contrib.auth.forms import ReadOnlyPasswordHashField, AdminPasswordChangeForm
import re

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        label='رمز عبور', 
        widget=forms.PasswordInput(attrs={'class': 'vTextField'}),
        help_text='یک رمز عبور قوی حداقل ۸ کاراکتری وارد کنید.'
    )
    confirm_password = forms.CharField(
        label='تایید رمز عبور', 
        widget=forms.PasswordInput(attrs={'class': 'vTextField'}),
        help_text='رمز عبور را مجدداً وارد کنید.'
    )

    class Meta:
        model = CustomUser
        fields = ('phone_number', 'full_name', 'avatar', 'is_premium')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        phone_number = "".join(phone_number.split()) # حذف فضاهای خالی
        if not re.match(r'^09\d{9}$', phone_number):
            raise ValidationError('فرمت شماره تلفن معتبر نیست! باید با 09 شروع شده و ۱۱ رقم باشد.')
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise ValidationError('این شماره تلفن قبلاً در سیستم ثبت شده است.')
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("🚨 رمز عبور و تاییدیه آن کاملاً با هم مغایرت دارند!")
            if len(password) < 8:
                raise ValidationError("🚨 رمز عبور باید حداقل ۸ کاراکتر باشد.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="رمز عبور",
        help_text=(
            "رمزهای عبور به صورت خام ذخیره نمی‌شوند، بنابراین راهی برای دیدن رمز عبور این کاربر وجود ندارد، "
            "اما می‌توانید رمز عبور را با استفاده از <a href=\"../password/\">این فرم</a> تغییر دهید."
        ),
    )

    class Meta:
        model = CustomUser
        fields = (
            'phone_number', 'password', 'full_name', 'avatar',
            'is_premium', 'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        phone_number = "".join(phone_number.split())
        if not re.match(r'^09\d{9}$', phone_number):
            raise ValidationError('فرمت شماره تلفن معتبر نیست!')
        
        if CustomUser.objects.filter(phone_number=phone_number).exclude(pk=self.instance.pk).exists():
            raise ValidationError('این شماره تلفن توسط کاربر دیگری رزرو شده است.')
        return phone_number

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm
    
    list_display = ['phone_number', 'full_name', 'is_premium', 'is_staff', 'is_active']
    list_filter = ['is_premium', 'is_staff', 'is_active', 'groups']
    search_fields = ['phone_number', 'full_name']
    ordering = ['phone_number']

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('اطلاعات فردی بازیکن', {'fields': ('full_name', 'avatar', 'is_premium')}),
        ('سطوح دسترسی و پرمیشن‌ها', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': 'از این بخش می‌توانید کاربر را عضو یک گروه خاص کنید یا پرمیشن‌های اتمیک (مانند افزودن، تغییر یا حذف دست‌ها) را مستقیماً به تیک بزنید.'
        }),
        ('تاریخ‌های مهم', {'fields': ('last_login',)}),
    )

    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password', 'confirm_password', 'full_name', 'avatar', 'is_premium', 'is_active', 'is_staff'),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)