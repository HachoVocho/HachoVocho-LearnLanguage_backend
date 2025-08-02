from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.timezone import now
from parler.models import TranslatableModel, TranslatedFields
from localization.models import CityModel, CountryModel
from translations.models import LanguageModel
from user.models import DrinkingHabitModel, FoodHabitModel, IncomeRangeModel, IncomeRangeModel, OccupationModel, RelationshipStatusModel, ReligionModel, SmokingHabitModel, SocializingHabitModel

class TenantDetailsModel(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50,blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128,blank=True,null=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_google_account = models.BooleanField(default=False)
    profile_picture = models.FileField(upload_to="static/profile_pictures/",null=True,blank=True)
    preferred_city = models.ForeignKey(CityModel, on_delete=models.CASCADE, related_name='preferred_city',blank=True,null=True)
    preferred_language = models.ForeignKey(LanguageModel, on_delete=models.CASCADE, related_name='preferred_language_tenant',blank=True,null=True)
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email

    @property
    def user_type(self):
        return 'tenant'
    
    @property
    def is_authenticated(self):
        return True
    
class TenantPersonalityDetailsModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='tenant_personality')
    occupation = models.ForeignKey(OccupationModel, on_delete=models.CASCADE, related_name='occupation',blank=True,null=True)
    country = models.ForeignKey(CountryModel, on_delete=models.CASCADE, related_name='country',blank=True,null=True)
    religion = models.ForeignKey(ReligionModel, on_delete=models.CASCADE, related_name='religion',blank=True,null=True)
    income_range = models.ForeignKey(IncomeRangeModel, on_delete=models.CASCADE, related_name='income_range',blank=True,null=True)
    smoking_habit = models.ForeignKey(SmokingHabitModel, on_delete=models.CASCADE, related_name='smoking_habit',blank=True,null=True)
    drinking_habit = models.ForeignKey(DrinkingHabitModel, on_delete=models.CASCADE, related_name='drinking_habit',blank=True,null=True)
    socializing_habit = models.ForeignKey(SocializingHabitModel, on_delete=models.CASCADE, related_name='socializing_habit',blank=True,null=True)
    relationship_status = models.ForeignKey(RelationshipStatusModel, on_delete=models.CASCADE, related_name='relationship_status',blank=True,null=True)
    food_habit = models.ForeignKey(FoodHabitModel, on_delete=models.CASCADE, related_name='relationship_status',blank=True,null=True)
    pet_lover = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.tenant.email


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
    document_number = models.CharField(max_length=100, null=True, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    submitted_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"User: {self.tenant.email}, Document Type: {self.document_type}, Status: {self.verification_status}"

class TenantIdentityVerificationFile(models.Model):
    identity_document = models.ForeignKey(
        TenantIdentityVerificationModel,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='static/tenant_identity_documents/')
    uploaded_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"File for Document {self.identity_document.id}: {self.file.name}"

class TenantPreferenceQuestionTypeModel(models.Model):
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

class TenantPreferenceQuestionModel(TranslatableModel):
    question_type = models.ForeignKey(TenantPreferenceQuestionTypeModel, on_delete=models.CASCADE, related_name='question_type')
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)
    translations = TranslatedFields(
        title = models.TextField()
    )
    
    def __str__(self):
        return f"{self.question_type} ({self.question_type})"
# Tables for priority-based questions with options or dropdown values
    
class TenantPreferenceOptionModel(TranslatableModel):
    question = models.ForeignKey(
        TenantPreferenceQuestionModel,
        on_delete=models.CASCADE,
        related_name='options'
    )
    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)
    translations = TranslatedFields(
        title = models.TextField()
    )
    
class TenantPreferenceAnswerModel(models.Model):
    tenant = models.ForeignKey(TenantDetailsModel, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(TenantPreferenceQuestionModel, on_delete=models.CASCADE, related_name='answers')
    option = models.ForeignKey(TenantPreferenceOptionModel, on_delete=models.CASCADE, related_name='option_answers')
    priority = models.PositiveIntegerField(null=True, blank=True)  # Priority assigned by the user
    static_option = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"User: {self.tenant.email}, Question: {self.question.question_type}"
      