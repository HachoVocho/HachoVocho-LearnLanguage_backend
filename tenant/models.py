from django.db import models
from django.utils.timezone import now

class TenantDetailsModel(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email

class TenantEmailVerificationModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='tenant_email_verifications')
    otp = models.CharField(max_length=255, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant.email} - Verified: {self.is_verified}"
    
class TenantDocumentTypeModel(models.Model):
    type_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name

class TenantIdentityVerificationModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='identity_verifications')
    document_type = models.ForeignKey(TenantDocumentTypeModel, on_delete=models.CASCADE, related_name='document_type')
    document_number = models.CharField(max_length=100, unique=True)
    document_file = models.FileField(upload_to='identity_documents/')
    verification_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='pending')
    submitted_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"User: {self.user.email}, Document Type: {self.document_type}, Status: {self.verification_status}"


class TenantQuestionTypeModel(models.Model):
    QUESTION_TYPES = [
        ('single_mcq', 'Single Choice MCQ'),
        ('multiple_mcq', 'Multiple Select MCQ'),
        ('priority_based', 'Priority Based'),
    ]
    type_name = models.CharField(max_length=50,choices=QUESTION_TYPES, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name

class TenantQuestionModel(models.Model):
    question_text = models.TextField()
    question_type = models.ForeignKey(TenantQuestionTypeModel, on_delete=models.CASCADE, related_name='question_type')

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.question_text} ({self.question_type})"
# Tables for priority-based questions with options or dropdown values

class TenantOptionModel(models.Model):
    question = models.ForeignKey(TenantQuestionModel, on_delete=models.CASCADE, related_name='question_options')
    option_text = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.option_text

class TenantAnswerModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(TenantQuestionModel, on_delete=models.CASCADE, related_name='answers')
    option = models.ForeignKey(TenantOptionModel, on_delete=models.CASCADE, related_name='option_answers')
    priority = models.PositiveIntegerField(null=True, blank=True)  # Priority assigned by the user
    static_option = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"User: {self.user.email}, Question: {self.question.question_text}"
      