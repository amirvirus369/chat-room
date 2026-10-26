from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from . import models
from account.models import CustomUser
from django.utils import timezone
from django.http import HttpResponse
from django.core.cache import cache


class RealTime(WebsocketConsumer):

    def connect(self):
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            self.close()
            return HttpResponse('دسترسی به این صفحه ندارید لطفا اول ثبت نام کنید ')

        name = self.scope['url_route']['kwargs'].get('full_name')

        try:
            self.receiver = CustomUser.objects.get(full_name=name)
        except CustomUser.DoesNotExist:
            self.close(code=4404)
            return

        self.group_name = f'user_{self.user.id}'

        async_to_sync(self.channel_layer.group_add)(self.group_name,self.channel_name)

        self.accept()

        

       
        self.counted = True
        if self.mark_online():
            self.broadcast_status('online')
        self.send_online_list()


    def get_contact_ids(self):
        sent = models.Message.objects.filter(sender=self.user).values_list('recive_id', flat=True)
        got = models.Message.objects.filter(recive=self.user).values_list('sender_id', flat=True)
        ids = set(sent) | set(got)
        ids.add(self.receiver.id)
        ids.discard(self.user.id)
        return ids

    def mark_online(self):
        key = f'online_count_{self.user.id}'
        cache.add(key, 0, timeout=None)
        return cache.incr(key) == 1      

    def mark_offline(self):
        key = f'online_count_{self.user.id}'
        try:
            n = cache.decr(key)
        except ValueError:
            n = 0
        if n <= 0:
            cache.set(key, 0, timeout=None)
            return True                  
        return False

    def broadcast_status(self, status):
        for uid in self.get_contact_ids():
            async_to_sync(self.channel_layer.group_send)(f'user_{uid}', {
                'type': 'annoumcement',
                'user_name': self.user.full_name,
                'status': status,
            })

    def send_online_list(self):
        ids = self.get_contact_ids()
        online = [
            u.full_name
            for u in CustomUser.objects.filter(id__in=ids)
            if cache.get(f'online_count_{u.id}', 0) > 0
        ]
        self.send(text_data=json.dumps({
            'type_of_data': 'online_list',
            'users': online,
        }))

    

    def receive(self, text_data ):
        try:
            data = json.loads(text_data)
        except:
            return HttpResponse('جیسون لود نشده ')
        message_type = data.get('type')

        if message_type == 'new':
            is_block = models.Block.objects.filter(blocker = self.user,blocked = self.receiver).exists() or models.Block.objects.filter(blocker = self.receiver,blocked = self.user).exists()
            if is_block:
                return
            message = str(data.get('msg','')).strip()
            

            models.Message.objects.create(
                sender = self.user,
                recive = self.receiver,
                message = message,
                date = timezone.now(),
                seen = False,
            )

            response = ({
                
                'type_of_data':'new',
                'sender':self.user.full_name,
                'message':message,
                'date':timezone.now().strftime("%H:%M"),
                'username':self.receiver.full_name
                
            })

            async_to_sync(self.channel_layer.group_send)(
                f'user_{self.receiver.id}',{
                    'type':'send_message_new',
                    'data':response
                }
            )

        elif message_type == 'ihave_seen':
           
            msg = models.Message.objects.filter(recive=self.user,sender=self.receiver,seen = False)
            if not msg.exists():
                return

            msg.update(seen = True)

            async_to_sync(self.channel_layer.group_send)(f'user_{self.receiver.id}',{
                'type':'send_send',
                'sender':self.receiver.full_name,
                'reciver': self.user.full_name
            })
        elif message_type == 'search':
            query = str(data.get('quary','').strip())
            users = []
            if query:
                search_chat = CustomUser.objects.filter(full_name__icontains = query).exclude(full_name = self.receiver)
                users = [{'full_name':u.full_name} for u in search_chat]

            self.send(text_data=json.dumps({
                'users':users,
                'type_of_data':'search'
            }))
        elif message_type == 'block':
            models.Block.objects.filter(blocker = self.user,blocked = self.receiver)
            async_to_sync(self.channel_layer.group_send)(f'user_{self.receiver.id}',{
                'type':'block',
                'blocker_name':self.user.full_name
            })
        elif message_type == 'unblock':
                    models.Block.objects.get_or_create(blocker = self.user,blocked = self.receiver).delete()
                    async_to_sync(self.channel_layer.group_send)(f'user_{self.receiver.id}',{
                        'type':'block',
                        'blocker_name':self.user.full_name
                    })         
            





    def annoumcement(self,event):
        self.send(text_data=json.dumps({
            'type_of_data':'onlainam',
            'user_name':event.get('user_name'),
            'status':event.get('status')
        }))


    def send_message_new(self,event):
        data = event.get('data',{})
        self.send(text_data=json.dumps(data))



    def send_send(self,event):
        self.send(text_data=json.dumps({
            'type_of_data':'ihave_seen',
            'sender':event.get('sender'),
            'reciver':event.get('reciver')
        }))

    def send_file(self,event):
        data = event.get('data',{})
        self.send(text_data=json.dumps(data))

    def check_user(self,event):
        async_to_sync(self.channel_layer.send)(event['request_chanel'],{
            'status':'online',
            'user_name':self.user.full_name,
            'type':'annoumcement'
        })

    def block(self,event):
        self.send(text_data=json.dumps({
            'type_of_data':'block',
            'blocker_name':event.get('blocker_name')
        }))


    def disconnect(self, code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name
            )

        if getattr(self, 'counted', False):
            self.counted = False
            if self.mark_offline():
                self.broadcast_status('offline')