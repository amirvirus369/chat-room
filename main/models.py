from django.db import models
from account.models import CustomUser
import os
# Create your models here.

class Message(models.Model):
    sender = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='sender_user')
    recive = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='recive_user')
    reply = models.ForeignKey('self',on_delete=models.CASCADE,related_name='reply_user',null=True,blank=True)
    message = models.TextField(null=True,blank=True)
    file = models.FileField(upload_to='file',null=True,blank=True)
    date = models.DateTimeField(auto_now=True)
    seen = models.BooleanField(default=False)

    @property
    def filename(self):
      return os.path.basename(self.file.name) if self.file else ''

    def __str__(self):
        return self.sender.full_name


class Block(models.Model):
    blocker = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='block')
    blocked = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='blocker')
    class Meta:
        unique_together = ('blocker','blocked')


class Group(models.Model):
    name = models.CharField(max_length=100)
    creator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(CustomUser, related_name='chat_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class GroupMessage(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='group_messages')
    message = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to='group_files/', null=True, blank=True)
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies'
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

