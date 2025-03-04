from django.db import models
from django.conf import settings

class DeviceNotificationModel(models.Model):
    user_id = models.IntegerField(blank=False,null=False)
    player_id = models.CharField(max_length=255, unique=True,blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user_id} - {self.player_id}"
