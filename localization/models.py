from django.db import models

from language_data.models import LanguageModel


class AllStaticStringsModel(models.Model):
    """
    Represents static strings for a specific page and language as a single JSON object.
    """
    language = models.ForeignKey(
        LanguageModel, on_delete=models.CASCADE, related_name="static_strings"
    )
    strings = models.JSONField(help_text="All static strings in specified language.",default=dict)  # Store all strings as JSON
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
