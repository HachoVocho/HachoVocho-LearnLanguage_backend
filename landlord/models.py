from django.db import models
from django.utils.timezone import now

# Create your models here.
class LandlordDetailsModel(models.Model):
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
    number_of_rooms = models.PositiveIntegerField()
    floor = models.PositiveIntegerField(null=True, blank=True)
    property_description = models.TextField(null=True, blank=True)
    property_images = models.ImageField(upload_to='property_images/', null=True, blank=True)
    property_videos = models.FileField(upload_to='property_videos/', null=True, blank=True)
    amenities = models.ManyToManyField(LandlordPropertyAmenityModel, related_name='properties', blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.property_name} - {self.property_type}"

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
    room_size = models.TextField()
    room_type = models.ForeignKey(LandlordPropertyRoomTypeModel, on_delete=models.CASCADE, related_name='room_type')
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

class LandlordRoomWiseBedModel(models.Model):
    room = models.ForeignKey(LandlordPropertyRoomDetailsModel, on_delete=models.CASCADE, related_name='beds')
    is_available = models.BooleanField(default=True)
    rent_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    availability_start_date = models.DateField()
    availability_end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bed {self.bed_number} in {self.room}"


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
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.ForeignKey(LandlordQuestionTypeModel, on_delete=models.CASCADE, related_name='question_type')
    applicable_property_types = models.ManyToManyField(LandlordPropertyTypeModel, related_name='applicable_questions')

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.question_text} ({self.question_type})"

class LandlordOptionModel(models.Model):
    question = models.ForeignKey(LandlordQuestionModel, on_delete=models.CASCADE, related_name='question_options')
    option_text = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.option_text

class LandlordAnswerModel(models.Model):
    bed = models.ForeignKey(LandlordRoomWiseBedModel, on_delete=models.CASCADE, related_name='room_wise_bed')
    question = models.ForeignKey(LandlordQuestionModel, on_delete=models.CASCADE, related_name='answers')
    option = models.ForeignKey(LandlordOptionModel, on_delete=models.CASCADE, related_name='option_answers', null=True, blank=True)
    static_option = models.CharField(max_length=255, null=True, blank=True)
    priority = models.PositiveIntegerField(null=True, blank=True)  # Priority assigned by the landlord

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Landlord: {self.landlord.email}, Question: {self.question.question_text}"
    
class LandlordPropertyVerificationDocumentTypeModel(models.Model):
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
    document_type = models.ForeignKey(LandlordPropertyVerificationDocumentTypeModel, on_delete=models.CASCADE, related_name='landlord_document_type')
    document_number = models.CharField(max_length=100, unique=True)
    document_file = models.FileField(upload_to='landlord_identity_documents/')
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


class LandlordPropertyVerificationModel(models.Model):
    property = models.ForeignKey(LandlordPropertyDetailsModel, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.ForeignKey(LandlordPropertyVerificationDocumentTypeModel, on_delete=models.CASCADE, related_name='property_verification_document_type')
    document_file = models.FileField(upload_to='property_verification_documents/')
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
