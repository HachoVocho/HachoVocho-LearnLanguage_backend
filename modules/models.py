from django.db import models

from language_data.models import LanguageLevelModel

class ModuleModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class TopicModel(models.Model):
    name = models.CharField(max_length=200)
    module = models.ForeignKey(ModuleModel, on_delete=models.CASCADE, related_name="topics")
    level = models.ForeignKey(LanguageLevelModel, on_delete=models.CASCADE, related_name="topics")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.level.name} ({self.module.name})"