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


class Block(models.Model):
    blocker = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='block')
    blocked = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='blocker')
    class Meta:
        unique_together = ('blocker','blocked')




