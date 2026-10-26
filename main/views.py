from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth import authenticate,login,logout
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from main import models
from account.models import CustomUser
from .flytoday_login import get_encrypted_phone, send_login_request, verify_otp
from django.db.models import Q,Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
# Create your views here.


def PageCHat(request,full_name):
    username = get_object_or_404(CustomUser,full_name=full_name)
    is_block = models.Block.objects.filter(blocker = request.user,blocked =username).exists() or models.Block.objects.filter(blocker = username,blocked = request.user).exists()
    block = False
    blocker = False
    if is_block:
        block = models.Block.objects.filter(blocker = request.user,blocked =username).exists()
        blocker =  models.Block.objects.filter(blocker = username,blocked = request.user).exists()
        
    sidbar = models.Message.objects.filter(Q(sender = request.user) | Q(recive =request.user)).select_related('sender', 'recive').order_by('-date')
    chat_all = models.Message.objects.filter(Q(sender = request.user,recive=username) | Q(sender=username,recive=request.user)).order_by('date')
    unread = models.Message.objects.filter(recive = request.user,seen = False).values('sender').annotate(total=Count(('id')))
    unread_for = {i['sender'] : i['total'] for i in unread}
    contact = []
    set_id = set()

    for i in sidbar:
        other = i.recive if i.sender_id == request.user.id else i.sender

        if other.id not in set_id:
            set_id.add(other.id)
            contact.append({
                'user':other,
                'chat':i,
                'seen':unread_for.get(other.id)
            })


            
    context = {
        'contact':contact,
        'username':username,
        'chat_all':chat_all,
        'block':block,
        'blocker':blocker,
        'is_block':is_block
    }
    return render(request,'chat.html',context)

@csrf_exempt
def upload(request,user):
    user = CustomUser.objects.get(full_name=user)
    is_block = models.Block.objects.filter(blocker = request.user,blocked =user).exists() or models.Block.objects.filter(blocker = user,blocked = request.user).exists()
    if is_block:
        return JsonResponse({'status': 'block'}, status=403)  
    if request.method == 'POST':
        file = request.FILES.get('file')
        if file:
            
            msg = models.Message.objects.create(
                sender = request.user,
                recive=user,
                file = file,
                date = timezone.now(),
                seen = False
            )


            res = {
                'type_of_data':'file',
                'file_url':msg.file.url,
                'sender':request.user.full_name,
                'username':user.full_name,
                'date':timezone.now().strftime('%H:%M')
                
            }
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(f'user_{user.id}',{'type':'send_file','data':res})
            return JsonResponse({'status':'success','file_url':msg.file.url})
        return JsonResponse({'status': 'invalid request'}, status=400)
    return JsonResponse({'status': 'request is not post'}, status=403)    





##############################################################################################
def ViewAuthen(request):
    if request.user.is_authenticated:
            return redirect('chat:chat', full_name=request.user.full_name)
    return render(request,'authen.html')


def Register(request):
    if request.user.is_authenticated:
        return redirect('chat:chat', full_name=request.user.full_name)
    if request.method == 'POST':
        name = request.POST.get('name')
        user = request.POST.get('user')
        pass1 = request.POST.get('pass1')
        pass2 = request.POST.get('pass2')
        if CustomUser.objects.filter(phone_number=user).exists():
            p = 'این کاربر قبلا ثبت نام کرده '
            return render(request,'authen.html',{'p':p})
        if pass1 != pass2:
            p = 'پسورد ها یکسان نیستن'
            return render(request,'authen.html',{'p':p})
        
        if CustomUser.objects.filter(full_name=name).exists():
            p = 'این نام قبلا ثبت شده لطفا از یک نام دیگه استفاده کنید '
            return render(request,'authen.html',{'p':p})
        encrypted_phone = get_encrypted_phone(user)
        if not encrypted_phone:
            p = 'خطا در پردازش شماره موبایل'
            return render(request, 'authen.html', {'p': p})
            
        result = send_login_request(encrypted_phone)
        if not result.get("success") or "ticket" not in result:
            p = f"خطا در ارسال کد تایید: {result.get('error', 'نامشخص')}"
            return render(request, 'authen.html', {'p': p})
        
        name_s = request.session['name'] = name
        user_s = request.session['user'] = user
        pass1_s = request.session['pass1'] = pass1
        request.session['ticket'] = result["ticket"]
        return redirect('chat:very')

def verify(request):
    if request.user.is_authenticated:
        return redirect('chat:chat', full_name=request.user.full_name)

    name = request.session.get('name')
    user = request.session.get('user')
    pass1 = request.session.get('pass1')
    ticket = request.session.get('ticket')

    if not (name and user and pass1 and ticket):
        return redirect('chat:register') 
    if request.method == 'POST':
        code = request.POST.get('code') 
        verify_result = verify_otp(ticket, code)

        if verify_result.get("success"):
            new_user = CustomUser.objects.create_user(phone_number=user,full_name=name,password=pass1)

            if new_user:
                for key in ['name', 'user', 'pass1', 'ticket']:
                    request.session.pop(key, None)

                login(request, new_user, backend='account.authentication.PhoneAuthBackend')
                return redirect('chat:chat',full_name=name)
        else:
            p = 'کد وارد شده اشتباه است '
            return render(request, 'verify.html', {'p': p})

    return render(request, 'verify.html')





def Login_user(request):
   if request.user.is_authenticated:
       return redirect('chat:chat', full_name=request.user.full_name)

   if request.method == 'POST':
       user = request.POST.get('user')
       pass1 = request.POST.get('pass')

       user = authenticate(phone_number = user,password = pass1)
       if user is not None:
           username = CustomUser.objects.get(phone_number=user)
           login(request,user,backend='account.authentication.PhoneAuthBackend')
           return redirect('chat:chat',full_name=username.full_name)
       else:
            p = 'اطلاعات وارد شده معتبر نیست '
            return render(request,'authen.html',{'p':p})
           
def logout_user(request):
    logout(request)
    return redirect('chat:authen')