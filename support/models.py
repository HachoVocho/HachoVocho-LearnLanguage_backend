# help_support/models.py
from django.db import models
from django.utils.timezone import now
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel

STATUS_CHOICES = [
    ('open',       'Open'),
    ('inprogress', 'In Progress'),
    ('closed',     'Closed'),
]

class TenantSupportTicket(models.Model):
    tenant         = models.ForeignKey(
                        TenantDetailsModel,
                        on_delete=models.CASCADE,
                        related_name='support_tickets'
                      )
    description    = models.TextField()
    status         = models.CharField(
                        max_length=10,
                        choices=STATUS_CHOICES,
                        default='open'
                     )
    admin_comment  = models.TextField(
                        blank=True,
                        help_text="Internal notes or replies from support team"
                     )
    updated_by     = models.CharField(
                        max_length=20,
                        default='tenant',
                        help_text="who last updated: 'tenant'|'admin'"
                     )
    created_at     = models.DateTimeField(default=now)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket #{self.id} (Tenant {self.tenant_id})"


class LandlordSupportTicket(models.Model):
    landlord       = models.ForeignKey(
                        LandlordDetailsModel,
                        on_delete=models.CASCADE,
                        related_name='support_tickets'
                      )
    description    = models.TextField()
    status         = models.CharField(
                        max_length=10,
                        choices=STATUS_CHOICES,
                        default='open'
                     )
    admin_comment  = models.TextField(
                        blank=True,
                        help_text="Internal notes or replies from support team"
                     )
    updated_by     = models.CharField(
                        max_length=20,
                        default='landlord',
                        help_text="who last updated: 'landlord'|'admin'"
                     )
    created_at     = models.DateTimeField(default=now)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Ticket #{self.id} (Landlord {self.landlord_id})"
