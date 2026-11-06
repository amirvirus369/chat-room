from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from . import models
from account.models import CustomUser
from django.utils import timezone
from django.core.cache import cache


class RealTime(WebsocketConsumer):

    def connect(self):
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            self.close()
            return 

        name = self.scope['url_route']['kwargs']
        self.personal_group = f'user_{self.user.id}'
        async_to_sync(self.channel_layer.group_add)(self.personal_group, self.channel_name)
        if 'group_id' in name:
            self.is_group = True
            self.group_id = int(name['group_id'])
            try:
              self.group_id_check = models.Group.objects.get(id=self.group_id,members=self.user)


            except models.Group.DoesNotExist:
                self.close(code=4404)
                return

            self.group_name = f'group_{self.group_id}'
            async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)          
        else:
            self.is_group = False
            full_name = name.get('full_name')

            try:
                self.receiver = CustomUser.objects.get(full_name=full_name)
            except CustomUser.DoesNotExist:
                self.close(code=4404)
                return

            self.group_name = self.personal_group


        self.accept()

        

       
        self.counted = True
        if self.mark_online():
            self.broadcast_status('online')
        self.send_online_list()

    def get_private_contact_ids(self):
        sent = models.Message.objects.filter(sender=self.user).values_list('recive_id', flat=True)
        got = models.Message.objects.filter(recive=self.user).values_list('sender_id', flat=True)
        ids = set(sent) | set(got)
        if hasattr(self, 'receiver'):
            ids.add(self.receiver.id)
        ids.discard(self.user.id)
        return ids


    def set_group_read(self, msg_id):
        key = f'group_last_read_{self.user.id}_{self.group_id}'
        if msg_id and msg_id > (cache.get(key) or 0):
            cache.set(key, msg_id, timeout=None)

    def get_contact_ids(self):
        """مخاطبین شخصی + اعضای گروه (اگر داخل گروه هست)"""
        ids = set(self.get_private_contact_ids())
        if self.is_group:
            ids |= set(
                self.group_id_check.members
                .exclude(id=self.user.id)
                .values_list('id', flat=True)
            )
        return ids

    def mark_online(self):
        key = f'online_count_{self.user.id}'
        count = cache.get(key) or 0
        count += 1
        cache.set(key, count, timeout=300)  
        return count == 1   

    def mark_offline(self):
        key = f'online_count_{self.user.id}'
        try:
            count = cache.get(key) or 0
            count -= 1
            if count <= 0:
                cache.delete(key)         
                return True
            else:
                cache.set(key, count, timeout=300)
                return False
        except Exception:
            cache.delete(key)
            return True

    def refresh_online(self):
        key = f'online_count_{self.user.id}'
        count = cache.get(key)
        if count and count > 0:
            cache.set(key, count, timeout=300)

    def broadcast_status(self, status):
        for uid in self.get_contact_ids():
            async_to_sync(self.channel_layer.group_send)(f'user_{uid}', {
                'type': 'annoumcement',
                'user_name': self.user.full_name,
                'status': status,
            })

    def send_online_list(self):
        ids = self.get_private_contact_ids()
        online = [
            u.full_name
            for u in CustomUser.objects.filter(id__in=ids)
            if cache.get(f'online_count_{u.id}', 0) > 0
        ]
        self.send(text_data=json.dumps({
            'type_of_data': 'online_list',
            'users': online,
        }))


    def push_block_state(self):
        a_blocks_b = models.Block.objects.filter(blocker=self.user, blocked=self.receiver).exists()
        b_blocks_a = models.Block.objects.filter(blocker=self.receiver, blocked=self.user).exists()
        payload = {
            'type': 'block_state',
            'a_id': self.user.id,
            'b_id': self.receiver.id,
            'a_blocks_b': a_blocks_b,
            'b_blocks_a': b_blocks_a,
        }
        for uid in {self.user.id, self.receiver.id}:
            async_to_sync(self.channel_layer.group_send)(f'user_{uid}', payload)

    

    def receive(self, text_data ):
        try:
            data = json.loads(text_data)
        except:
            return 
        message_type = data.get('type')

        if message_type == 'heartbeat':
            self.refresh_online()
            return

        if self.is_group and message_type in ('ihave_seen',  'block', 'unblock'):
           return

        if self.is_group and message_type == 'new':
            message = str(data.get('msg', '')).strip()
            if not message:
                return

            msg_obj = models.GroupMessage.objects.create(
                group=self.group_id_check,
                sender=self.user,
                message=message
            )

            response = {
                'id': msg_obj.id,
                'type_of_data': 'group_new',
                'sender': self.user.full_name,
                'message': message,
                'date': timezone.now().strftime("%H:%M"),
                'group_id': self.group_id_check.id
            }

            async_to_sync(self.channel_layer.group_send)(
                f'group_{self.group_id_check.id}',
                {'type': 'send_group_message', 'data': response}
            )
            for member in self.group_id_check.members.exclude(id=self.user.id):
                async_to_sync(self.channel_layer.group_send)(
                    f'user_{member.id}',
                    {
                        'type': 'notify_group_message',
                        'data': response
                    }
                )
            return
        
        if not self.is_group and message_type == 'new':
            is_block = models.Block.objects.filter(blocker = self.user,blocked = self.receiver).exists() or models.Block.objects.filter(blocker = self.receiver,blocked = self.user).exists()
            if is_block:
                return
            message = str(data.get('msg','')).strip()
            

            models.Message.objects.create(
                sender = self.user,
                recive = self.receiver,
                message = message,
                date = timezone.now(),
                seen = (self.receiver.id == self.user.id),
            )

            response = ({
                
                'type_of_data':'new',
                'sender':self.user.full_name,
                'message':message,
                'date':timezone.now().strftime("%H:%M"),
                'username':self.receiver.full_name
                
            })
            if self.receiver.id != self.user.id:
                async_to_sync(self.channel_layer.group_send)(
                    f'user_{self.receiver.id}',{
                        'type':'send_message_new',
                        'data':response
                    }
                )

        elif message_type == 'create_group':
            group_name = str(data.get('name', '')).strip()
            member_names = data.get('members', [])  

            if not group_name:
                self.send(text_data=json.dumps({
                    'type_of_data': 'error',
                    'message': 'نام گروه نمی‌تواند خالی باشد'
                }))
                return

            group = models.Group.objects.create(
                name=group_name,
                creator=self.user
            )
            group.members.add(self.user)  

            added_users = [self.user]
            for full_name in member_names:
                try:
                    user = CustomUser.objects.get(full_name=full_name)
                    if user != self.user:
                        group.members.add(user)
                        added_users.append(user)
                except CustomUser.DoesNotExist:
                    continue

            self.send(text_data=json.dumps({
                'type_of_data': 'group_created',
                'group_id': group.id,
                'group_name': group.name,
                'creator': self.user.full_name
            }))

            for user in added_users:
                if user != self.user:
                    async_to_sync(self.channel_layer.group_send)(
                        f'user_{user.id}',
                        {
                            'type': 'notify_group_added',
                            'group_id': group.id,
                            'group_name': group.name,
                            'creator': self.user.full_name
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
            query = str(data.get('quary', '')).strip()
            users = []
            if query:
                search_chat = CustomUser.objects.filter(full_name__icontains=query).exclude(id=self.user.id)
                users = [{'full_name': u.full_name} for u in search_chat]
            self.send(text_data=json.dumps({'users': users, 'type_of_data': 'search'}))

        elif message_type == 'block':
             models.Block.objects.get_or_create(blocker=self.user, blocked=self.receiver)
             self.push_block_state()

        elif message_type == 'unblock':
            models.Block.objects.filter(blocker=self.user, blocked=self.receiver).delete()
            self.push_block_state()

        elif message_type == 'add_members':
            if not self.is_group:
                return

            if self.group_id_check.creator_id != self.user.id:
                self.send(text_data=json.dumps({
                    'type_of_data': 'error',
                    'message': 'فقط سازنده گروه می‌تواند عضو اضافه کند'
                }))
                return

            member_names = data.get('members', [])
            added_users = []

            for full_name in member_names:
                try:
                    user = CustomUser.objects.get(full_name=full_name)
                    if user not in self.group_id_check.members.all() and user != self.user:
                        self.group_id_check.members.add(user)
                        added_users.append(user)
                except CustomUser.DoesNotExist:
                    continue

            if not added_users:
                return

            for user in added_users:
                async_to_sync(self.channel_layer.group_send)(
                    f'user_{user.id}',
                    {
                        'type': 'notify_group_added',
                        'group_id': self.group_id_check.id,
                        'group_name': self.group_id_check.name,
                        'creator': self.user.full_name
                    }
                )

            new_count = self.group_id_check.members.count()
            async_to_sync(self.channel_layer.group_send)(
                f'group_{self.group_id_check.id}',
                {
                    'type': 'group_members_updated',
                    'group_id': self.group_id_check.id,
                    'member_count': new_count,
                    'action': 'add',
                    'added_by': self.user.full_name
                }
            )

            self.send(text_data=json.dumps({
                'type_of_data': 'members_added',
                'count': len(added_users),
                'member_count': new_count
            }))

        elif message_type == 'remove_member':
            if not self.is_group:
                return

            if self.group_id_check.creator_id != self.user.id:
                self.send(text_data=json.dumps({
                    'type_of_data': 'error',
                    'message': 'فقط سازنده گروه می‌تواند عضو حذف کند'
                }))
                return

            full_name = str(data.get('full_name', '')).strip()
            if not full_name:
                return

            try:
                user_to_remove = CustomUser.objects.get(full_name=full_name)
            except CustomUser.DoesNotExist:
                return

            if user_to_remove.id == self.user.id:
                self.send(text_data=json.dumps({
                    'type_of_data': 'error',
                    'message': 'نمی‌توانید خودتان را حذف کنید'
                }))
                return

            if user_to_remove not in self.group_id_check.members.all():
                return

            self.group_id_check.members.remove(user_to_remove)

            async_to_sync(self.channel_layer.group_send)(
                f'user_{user_to_remove.id}',
                {
                    'type': 'notify_removed_from_group',
                    'group_id': self.group_id_check.id,
                    'group_name': self.group_id_check.name
                }
            )

            new_count = self.group_id_check.members.count()
            async_to_sync(self.channel_layer.group_send)(
                f'group_{self.group_id_check.id}',
                {
                    'type': 'group_members_updated',
                    'group_id': self.group_id_check.id,
                    'member_count': new_count,
                    'action': 'remove',
                    'removed_name': full_name
                }
            )

            self.send(text_data=json.dumps({
                'type_of_data': 'member_removed',
                'full_name': full_name,
                'member_count': new_count
            }))
            





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


    def send_group_message(self, event):
        self.send(text_data=json.dumps(event['data']))
        if self.is_group and event['data'].get('group_id') == self.group_id:
            self.set_group_read(event['data'].get('id'))

    def send_group_file(self, event):
        self.send(text_data=json.dumps(event['data']))
        if self.is_group and event['data'].get('group_id') == self.group_id:
            self.set_group_read(event['data'].get('id'))

    def block_state(self, event):
        if self.is_group:      
           return
        if self.user.id == event['a_id']:
            other_id = event['b_id']
            i_blocked, he_blocked = event['a_blocks_b'], event['b_blocks_a']
        else:
            other_id = event['a_id']
            i_blocked, he_blocked = event['b_blocks_a'], event['a_blocks_b']

        if self.receiver.id != other_id:   
            return

        self.send(text_data=json.dumps({
            'type_of_data': 'block_state',
            'i_blocked': i_blocked,
            'he_blocked': he_blocked,
        }))

    def notify_group_added(self, event):
        self.send(text_data=json.dumps({
            'type_of_data': 'added_to_group',
            'group_id': event['group_id'],
            'group_name': event['group_name'],
            'creator': event['creator']
        }))

    def notify_group_message(self, event):
        data = event['data'].copy()
        data = event['data']
        data['type_of_data'] = 'group_message_notification'
        self.send(text_data=json.dumps(data))

    def group_members_updated(self, event):
        self.send(text_data=json.dumps({
            'type_of_data': 'group_members_updated',
            'group_id': event['group_id'],
            'member_count': event['member_count'],
            'action': event.get('action'),
            'added_by': event.get('added_by'),
            'removed_name': event.get('removed_name')
        }))

    def notify_removed_from_group(self, event):
        self.send(text_data=json.dumps({
            'type_of_data': 'removed_from_group',
            'group_id': event['group_id'],
            'group_name': event['group_name']
        }))




    def disconnect(self, code):
            if hasattr(self, 'personal_group'):
                async_to_sync(self.channel_layer.group_discard)(
                    self.personal_group, self.channel_name
                )

            if hasattr(self, 'group_name') and self.group_name != getattr(self, 'personal_group', None):
                async_to_sync(self.channel_layer.group_discard)(
                    self.group_name, self.channel_name
                )

            if getattr(self, 'counted', False):
                self.counted = False
                if self.mark_offline():
                    self.broadcast_status('offline')