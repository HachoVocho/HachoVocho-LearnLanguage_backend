from django.db import models
from django.utils.timezone import now

class LanguageModel(models.Model):
    code = models.CharField(max_length=10, unique=True)  # e.g., 'en', 'es'
    name = models.CharField(max_length=100)  # e.g., 'English', 'Spanish'

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class TranslationModel(models.Model):
    key = models.CharField(max_length=255)
    language = models.ForeignKey(LanguageModel, on_delete=models.CASCADE, related_name='translations')
    value = models.TextField()

    class Meta:
        unique_together = (('key', 'language'),)
