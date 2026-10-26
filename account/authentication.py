from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class PhoneAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        phone_number = username or kwargs.get('phone_number')
        if not phone_number:
            return None
            
        try:
            user = User.objects.get(phone_number=phone_number)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
