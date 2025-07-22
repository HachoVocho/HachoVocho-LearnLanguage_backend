from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from landlord.models import LandlordDetailsModel
from tenant.models import TenantDetailsModel
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated
from .models import LanguageModel, TranslationModel
from .serializers import LandlordLanguageUpdateSerializer, TenantLanguageUpdateSerializer, TranslationSerializer, TranslationListSerializer, LanguageSerializer
from googletrans import Translator
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

@api_view(["POST"])
#@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def add_translation(request):
    """
    API endpoint to add one or multiple translations and automatically translate to all languages.
    Expected JSON payload can be a single object:
    {
        "key": "first_name",
        "language_code": "en",
        "value": "First Name"
    }
    
    or a list of objects:
    [
      {
        "key": "first_name",
        "language_code": "en",
        "value": "First Name"
      },
      {
        "key": "last_name",
        "language_code": "en",
        "value": "Last Name"
      }
    ]
    
    For each payload, the provided 'value' for the given language_code (source language) is used as-is,
    and then translated into every other language available in LanguageModel.
    If a translation already exists for a specific key and language, that translation is skipped.
    """
    data = request.data
    # Allow a single object or a list of objects.
    if not isinstance(data, list):
        data = [data]
    
    overall_results = {}
    translator = Translator()
    
    for item in data:
        serializer = TranslationSerializer(data=item)
        if not serializer.is_valid():
            # Skip invalid payloads; you might alternatively collect errors.
            overall_results[item.get("key", "unknown")] = {
                "error": serializer.errors
            }
            continue

        key = serializer.validated_data['key']
        source_language_code = serializer.validated_data['language_code']
        source_value = serializer.validated_data['value']
        
        try:
            source_language = LanguageModel.objects.get(code=source_language_code)
        except LanguageModel.DoesNotExist:
            overall_results[key] = {"error": f"Source language '{source_language_code}' not found."}
            continue
        
        # Prepare a dict to store translation results for this key.
        translation_results = {}
        
        # Get all languages from the database.
        languages = LanguageModel.objects.all()
        
        for language in languages:
            # Check if a translation for this key and language already exists.
            if TranslationModel.objects.filter(key=key, language=language).exists():
                translation_results[language.code] = "skipped (exists)"
                continue
            
            if language.code == source_language_code:
                # Use the provided value for the source language.
                translated_text = source_value
            else:
                # Translate from the source language into the target language.
                try:
                    translation = translator.translate(source_value, src=source_language_code, dest=language.code)
                    translated_text = translation.text
                except Exception as e:
                    translated_text = ""  # Alternatively, you can log or handle errors differently.
            
            # Create the translation record.
            TranslationModel.objects.create(key=key, language=language, value=translated_text)
            translation_results[language.code] = translated_text
            cache_key = f"translations_{language.code}"
            cache.delete(cache_key)
        overall_results[key] = translation_results

    return Response({
        "success": True,
        "message": "Translations processed.",
        "data": overall_results
    }, status=status.HTTP_201_CREATED)

@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def get_translations(request):
    """
    API endpoint to fetch translations for a specific language code.
    Expected JSON payload:
    {
        "language_code": "en"
    }
    """
    print(f'request.datadd {request.data}')
    language_code = request.data.get('language_code')
    if not language_code:
        return Response({
            "success": False,
            "message": "language_code parameter is required."
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate a unique cache key for the language code
    #cache_key = f"translations_{language_code}"
    
    # Try to fetch translations from the cache
    #cached_data = cache.get(cache_key)
    
    #if cached_data:
        # If cached data exists, return it
        return Response({
            "success": True,
            "message": "Translations fetched successfully (from cache).",
            "data": cached_data
        }, status=status.HTTP_200_OK)
    
    try:
        # Fetch the language from the database
        language = LanguageModel.objects.get(code=language_code)
    except LanguageModel.DoesNotExist:
        return Response({
            "success": False,
            "message": "Language not found."
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Fetch translations from the database
    translations = TranslationModel.objects.filter(language=language)
    serializer = TranslationListSerializer(translations, many=True, context={'request': request})
    
    # Cache the translations for future requests
    #cache.set(cache_key, serializer.data, timeout=60 * 60)  # Cache for 1 hour (adjust as needed)
    
    return Response({
        "success": True,
        "message": "Translations fetched successfully.",
        "data": serializer.data
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_language(request):
    """
    API endpoint to add a new language.
    Expected JSON payload:
    {
        "code": "en",
        "name": "English"
    }
    """
    serializer = LanguageSerializer(data=request.data)
    if serializer.is_valid():
        language = serializer.save()
        # Invalidate languages cache after adding a new language.
        cache.delete("languages_all")
        return Response({
            "success": True,
            "message": "Language added successfully.",
            "data": LanguageSerializer(language).data
        }, status=status.HTTP_201_CREATED)
    return Response({
        "success": False,
        "message": "Error adding language.",
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([AllowAny])
def get_languages(request):
    """
    Public endpoint that optionally personalizes based on a valid JWT.
    """
    try:
        # Get cached languages
        cache_key = "languages_all"
        data = cache.get(cache_key)
        if data is None:
            languages = LanguageModel.objects.all()
            data = LanguageSerializer(languages, many=True).data
            cache.set(cache_key, data, 60 * 60)

        # Enrich translations
        for lang in data:
            t = TranslationModel.objects.filter(
                language_id=lang["id"],
                key="helloLabel"
            ).first()
            lang["hello"] = t.value if t else "Hello"

        # Handle authenticated users
        user = getattr(request, 'user', None)
        pref_code = None

        if user and user.is_authenticated:
            try:
                user_email = user.email

                # Check if user is a tenant
                tenant = TenantDetailsModel.objects.filter(email=user_email).first()
                if tenant and tenant.preferred_language:
                    pref_code = tenant.preferred_language.code

                # Check if user is a landlord (if tenant not found or no lang)
                if not pref_code:
                    landlord = LandlordDetailsModel.objects.filter(email=user_email).first()
                    if landlord and landlord.preferred_language:
                        pref_code = landlord.preferred_language.code

            except Exception as e:
                print(f"Error determining preferred language: {e}")

        return Response({
            "success": True,
            "message": "Languages fetched successfully.",
            "data": data,
            "preferred_language": pref_code if pref_code else None
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def set_tenant_language(request):
    """
    API endpoint to update a tenant's preferred language.
    Expected JSON payload:
    {
      "tenant_id": 123,
      "language_code": "en"
    }
    """
    serializer = TenantLanguageUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "message": "Invalid parameters.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    tenant_id = serializer.validated_data["tenant_id"]
    lang_code = serializer.validated_data["language_code"]

    # fetch instances
    tenant = TenantDetailsModel.objects.get(id=tenant_id)
    language = LanguageModel.objects.get(code=lang_code)

    # update and save
    # assumes TenantDetailsModel has a ForeignKey or CharField named `preferred_language`
    tenant.preferred_language = language
    tenant.save()

    # clear any tenant‐specific cache if you have one:
    cache.delete(f"tenant_{tenant_id}_profile")

    return Response({
        "success": True,
        "message": "Tenant language updated successfully.",
        "data": {
            "tenant_id": tenant_id,
            "language_code": lang_code
        }
    }, status=status.HTTP_200_OK)
    
    
@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def set_landlord_language(request):
    """
    API endpoint to update a tenant's preferred language.
    Expected JSON payload:
    {
      "tenant_id": 123,
      "language_code": "en"
    }
    """
    print(f'request.datadd {request.data}')
    serializer = LandlordLanguageUpdateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            "success": False,
            "message": "Invalid parameters.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    landlord_id = serializer.validated_data["landlord_id"]
    lang_code = serializer.validated_data["language_code"]

    # fetch instances
    landlord = LandlordDetailsModel.objects.get(id=landlord_id)
    language = LanguageModel.objects.get(code=lang_code)

    # update and save
    # assumes TenantDetailsModel has a ForeignKey or CharField named `preferred_language`
    landlord.preferred_language = language
    landlord.save()

    # clear any tenant‐specific cache if you have one:
    cache.delete(f"landlord_{landlord_id}_profile")

    return Response({
        "success": True,
        "message": "landlord language updated successfully.",
        "data": {
            "landlord_id": landlord_id,
            "language_code": lang_code
        }
    }, status=status.HTTP_200_OK)