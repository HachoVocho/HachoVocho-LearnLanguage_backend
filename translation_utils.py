from django.core.cache import cache
from translations.models import TranslationModel, LanguageModel

DEFAULT_LANGUAGE_CODE = "en"

def get_translation(key, language_code):
    """
    Retrieves the translation for a given key and language code.
    Falls back to default language if the specified one is not found.
    Caches the result to improve performance.
    """
    cache_key = f"translation_{key}_{language_code}"
    translation_value = cache.get(cache_key)
    if translation_value:
        return translation_value

    # Try to get the language instance
    language = LanguageModel.objects.filter(code=language_code).first()
    if not language:
        # Fallback to default language if not found
        language = LanguageModel.objects.filter(code=DEFAULT_LANGUAGE_CODE).first()

    # Fetch the translation from the database
    try:
        translation_obj = TranslationModel.objects.get(key=key, language=language)
        translation_value = translation_obj.value
    except TranslationModel.DoesNotExist:
        # If translation not found, you can fallback to a static string or the key itself
        translation_value = key

    # Cache the translation for later calls (for example, cache for 1 hour)
    cache.set(cache_key, translation_value, 3600)
    return translation_value
