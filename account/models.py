from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
import re


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('وارد کردن شماره تلفن برای ثبت‌نام الزامی است.')
        
        phone_number = "".join(phone_number.split())
        if not re.match(r'^09\d{9}$', phone_number):
            raise ValueError('فرمت شماره تلفن وارد شده معتبر نیست (باید با 09 شروع شود).')

        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(phone_number=phone_number, **extra_fields)
        
        if password:
            user.set_password(password) 
        else:
            raise ValueError('کاربر حتماً باید دارای رمز عبور باشد.')
            
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('سوپریوزر باید دارای دسترسی staff باشد.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('سوپریوزر باید دارای دسترسی superuser باشد.')

        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None 
    
    phone_number = models.CharField(
        max_length=11, 
        unique=True, 
        db_index=True, 
        verbose_name="شماره تلفن"
    )
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی", blank=True, null=True,unique=True)
    avatar = models.ImageField(upload_to='avatars/', verbose_name="تصویر پروفایل", blank=True, null=True)
    is_premium = models.BooleanField(default=False, verbose_name="کاربر ویژه / پرمیوم")
    
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ عضویت")

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    
    REQUIRED_FIELDS = ['full_name'] 

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران "

    def __str__(self):
        return self.phone_number