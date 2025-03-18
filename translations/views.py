from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import LanguageModel, TranslationModel
from .serializers import TranslationSerializer, TranslationListSerializer, LanguageSerializer
from googletrans import Translator
from django.core.cache import cache

@api_view(["POST"])
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
def get_translations(request):
    """
    API endpoint to fetch translations for a specific language code.
    Expected JSON payload:
    {
        "language_code": "en"
    }
    """
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


@api_view(["POST"])
def get_languages(request):
    """
    API endpoint to fetch all available languages.
    Each language object will include a key "hello" fetched from TranslationModel using key 'hello_label'.
    """
    cache_key = "languages_all"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Update the 'hello' key for each cached language using the TranslationModel.
        for lang in cached_data:
            # Assuming each language object has an 'id' field.
            translation = TranslationModel.objects.filter(language_id=lang['id'], key='helloLabel').first()
            lang["hello"] = translation.value if translation else "Hello"
        return Response({
            "success": True,
            "message": "Languages fetched successfully (from cache).",
            "data": cached_data
        }, status=status.HTTP_200_OK)
    
    # Fetch languages fresh if not cached.
    languages = LanguageModel.objects.all()
    serializer = LanguageSerializer(languages, many=True, context={'request': request})
    data = serializer.data

    # For each language, get the translation for "hello" using key 'hello_label'
    for lang in data:
        translation = TranslationModel.objects.filter(language_id=lang['id'], key='helloLabel').first()
        lang["hello"] = translation.value if translation else "Hello"
    
    # Cache the complete data (including the hello translation) for 1 hour.
    cache.set(cache_key, data, timeout=60 * 60)
    
    return Response({
        "success": True,
        "message": "Languages fetched successfully.",
        "data": data
    }, status=status.HTTP_200_OK)