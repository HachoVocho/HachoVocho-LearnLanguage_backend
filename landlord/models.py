from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from localization.models import CityModel
from translations.models import LanguageModel

# Create your models here.
class LandlordDetailsModel(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128,null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='static/profile_pictures/', null=True, blank=True)
    preferred_language = models.ForeignKey(LanguageModel, on_delete=models.CASCADE, related_name='preferred_language_landlord',blank=True,null=True)
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email
    
class LandlordEmailVerificationModel(models.Model):
    landlord = models.ForeignKey(LandlordDetailsModel, on_delete=models.CASCADE, related_name='landlord_email_verifications')
    otp = models.CharField(max_length=255, unique=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.landlord.email} - Verified: {self.is_verified}"

class LandlordPropertyTypeModel(models.Model):
    type_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name

class LandlordPropertyAmenityModel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class LandlordPropertyDetailsModel(models.Model):
    landlord = models.ForeignKey(LandlordDetailsModel, on_delete=models.CASCADE, related_name='properties')
    property_name = models.CharField(max_length=255)
    property_address = models.TextField()
    property_size = models.TextField()
    property_type = models.ForeignKey(LandlordPropertyTypeModel, on_delete=models.CASCADE, related_name='properties')
    property_city = models.ForeignKey(CityModel, on_delete=models.CASCADE, related_name='cities',blank=False,default='')
    pin_code = models.TextField(default='',blank=False)
    number_of_rooms = models.PositiveIntegerField()
    floor = models.PositiveIntegerField(null=True, blank=True)
    property_description = models.TextField(null=True, blank=True)
    amenities = models.ManyToManyField(LandlordPropertyAmenityModel, related_name='properties', blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.property_name} - {self.property_type}"

class LandlordPropertyMediaModel(models.Model):
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name="property_media")
    file = models.FileField(upload_to="property_media/")
    media_type = models.CharField(max_length=10, choices=(("image", "Image"), ("video", "Video")))
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

class LandlordPropertyRoomTypeModel(models.Model):
    type_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name
      
class LandlordPropertyRoomDetailsModel(models.Model):
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name='rooms')
    room_size = models.TextField(null=True)
    room_type = models.ForeignKey(LandlordPropertyRoomTypeModel, on_delete=models.CASCADE, related_name='room_type',null=True)
    number_of_beds = models.PositiveIntegerField(null=True, blank=True)
    number_of_windows = models.PositiveIntegerField(null=True, blank=True)
    max_people_allowed = models.PositiveIntegerField(null=True, blank=True)
    floor = models.PositiveIntegerField(null=True, blank=True)
    location_in_property = models.CharField(
        max_length=50,
        choices=[
            ('center', 'Center'),
            ('circumferancial', 'Circumferancial'),
        ],
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Room in {self.property.property_name} ({self.room_type})"

class LandlordRoomMediaModel(models.Model):
    room = models.ForeignKey(LandlordPropertyRoomDetailsModel, on_delete=models.CASCADE, related_name="room_media")
    file = models.FileField(upload_to="room_media/")
    media_type = models.CharField(max_length=10, choices=(("image", "Image"), ("video", "Video")))
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)


class LandlordQuestionTypeModel(models.Model):
    QUESTION_TYPES = [
        ('single_mcq', 'Single Choice MCQ'),
        ('multiple_mcq', 'Multiple Select MCQ'),
        ('priority_based', 'Priority Based'),
    ]
    type_name = models.CharField(max_length=50, choices=QUESTION_TYPES, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name

class LandlordQuestionModel(models.Model):
    question_text = models.TextField()
    question_type = models.ForeignKey(LandlordQuestionTypeModel, on_delete=models.CASCADE, related_name='question_type')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,related_name='question_content_type',null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.question_text} ({self.question_type})"
    
class LandlordAnswerModel(models.Model):
    landlord = models.ForeignKey(LandlordDetailsModel, on_delete=models.CASCADE, related_name='landlord_details',null=True)
    question = models.ForeignKey(LandlordQuestionModel, on_delete=models.CASCADE, related_name='answers')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE,related_name='content_type',null=True)
    object_id = models.PositiveIntegerField(null=True)
    preference = models.IntegerField(null=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Question: {self.question}, Preference: {self.preference}"
    

class LandlordRoomWiseBedModel(models.Model):
    room = models.ForeignKey(LandlordPropertyRoomDetailsModel, on_delete=models.CASCADE, related_name='beds')
    tenant_preference_answers = models.ManyToManyField(LandlordAnswerModel,related_name='tenant_preference_answers')
    bed_number = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True,blank=True)
    is_rent_monthly = models.BooleanField(default=True)
    min_agreement_duration_in_months = models.IntegerField(null=True,blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    availability_start_date = models.DateField(null=True,blank=True)
    #availability_end_date = models.DateField(null=True,blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bed {self.room.number_of_beds} in {self.room}"

class LandlordBedMediaModel(models.Model):
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name="bed_media")
    file = models.FileField(upload_to="bed_media/")
    media_type = models.CharField(max_length=10, choices=(("image", "Image"), ("video", "Video")))
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

class LandlordOptionModel(models.Model):
    question = models.ForeignKey(LandlordQuestionModel, on_delete=models.CASCADE, related_name='question_options')
    option_text = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.option_text
    
class LandlordDocumentTypeModel(models.Model):
    type_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.type_name
    
class LandlordIdentityVerificationModel(models.Model):
    landlord = models.ForeignKey(LandlordDetailsModel, on_delete=models.CASCADE, related_name='identity_verifications')
    document_type = models.ForeignKey(LandlordDocumentTypeModel, on_delete=models.CASCADE, related_name='landlord_document_type')
    document_number = models.CharField(max_length=100, unique=True)
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
        return f"Landlord: {self.landlord.email}, Document Type: {self.document_type}, Status: {self.verification_status}"

class LandlordIdentityVerificationFile(models.Model):
    identity_document = models.ForeignKey(
        LandlordIdentityVerificationModel,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to='static/landlord_identity_documents/')
    uploaded_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"File for Document {self.identity_document.id}: {self.file.name}"


class LandlordPropertyVerificationModel(models.Model):
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.ForeignKey(LandlordDocumentTypeModel, on_delete=models.CASCADE, related_name='property_verification_document_type')
    document_file = models.FileField(upload_to='static/property_verification_documents/')
    verification_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ], default='pending')
    furnishing_status = models.CharField(
        max_length=50,
        choices=[
            ('furnished', 'Furnished'),
            ('semi_furnished', 'Semi-Furnished'),
            ('unfurnished', 'Unfurnished'),
        ],
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(default=now)
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Property: {self.property.property_name}, Status: {self.verification_status}"

