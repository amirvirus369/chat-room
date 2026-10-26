from django.urls import path
from . import views
app_name = 'chat'

urlpatterns = [
    path('chat/<str:full_name>',views.PageCHat,name='chat'),
    path('',views.ViewAuthen,name='authen'),
    path('reg',views.Register,name='reg'),
    path('very',views.verify,name='very'),
    path('login',views.Login_user,name='login'),
    path('logout',views.logout_user,name='logout'),
    path('upload/<str:user>/',views.upload,name='upload')
]