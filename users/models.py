from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.utils import timezone

from language_data.models import LanguageLevelModel, LanguageModel
from listening_module.models import ListeningSentencesDataModel
from modules.models import TopicModel

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
)

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, first_name, last_name, password, **extra_fields)

class UserModel(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    app_language = models.ForeignKey(
        LanguageModel,
        on_delete=models.CASCADE,
        related_name="app_language",
        help_text="The language which user wants in the app",
        default=1
    )
    is_active = models.BooleanField(default=False)  # Inactive until OTP verification
    is_staff = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",  # Avoids conflict with auth.User.groups
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",  # Avoids conflict with auth.User.user_permissions
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email

class OTPModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """
        Checks if the OTP is valid (not used and within 10 minutes of creation).
        """
        return not self.is_used and timezone.now() <= self.created_at + timezone.timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.email} - {self.code}"

class UserLanguagePreferenceModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="language_preferences")
    comfortable_language = models.ForeignKey(
        LanguageModel,
        on_delete=models.CASCADE,
        related_name="comfortable_users",
        help_text="The language which user is comfortable with"
    )
    learning_language = models.ForeignKey(
        LanguageModel,
        on_delete=models.CASCADE,
        related_name="learning_users",
        help_text="The language which user wants to learn"
    )

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"User: {self.user.email}, "
            f"Comfortable Language: {self.comfortable_language.name}, "
            f"Learning Language: {self.learning_language.name}"
        )
    
class UserListeningSentenceProgressModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="sentence_progress_user")
    sentence_data = models.ForeignKey(ListeningSentencesDataModel, on_delete=models.CASCADE, related_name="user_sentence_progress")
    is_listened = models.BooleanField(default=False)  # Whether the user has listened to this sentence
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.sentence_data.sentence} - {self.is_listened}"

class UserListeningTopicProgressModel(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="topic_progress_user")
    listening_sentence_data = models.ForeignKey(ListeningSentencesDataModel, on_delete=models.CASCADE, related_name="listening_story_data_users",null=True)
    progress_percentage = models.FloatField(default=0.0)  # Overall progress percentage for the topic
    completed_sentences = models.IntegerField(default=0)  # Number of sentences completed
    total_sentences = models.IntegerField(default=0)  # Total sentences in the topic
    did_listen_story = models.BooleanField(default=False)  # Whether the user has listened to the story
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.listening_sentence_data.topic} - {self.progress_percentage}%"