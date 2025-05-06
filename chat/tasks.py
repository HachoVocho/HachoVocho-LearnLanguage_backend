# chat/tasks.py

from deep_translator import GoogleTranslator
from .models import ChatMessageModel, ChatMessageTranslationModel
from tenant.models import TenantDetailsModel
from landlord.models import LandlordDetailsModel

def translate_and_store(chat_id):
    """
    RQ task: Translate a chat message into its receiver’s preferred language
    using deep-translator (lightweight), and persist the result.
    """
    print(f"[translate_and_store] START chat_id={chat_id}")

    # 1) Fetch the ChatMessage
    try:
        chat = ChatMessageModel.objects.get(pk=chat_id)
        print(f"[translate_and_store] Fetched ChatMessage(id={chat.id})")
    except ChatMessageModel.DoesNotExist:
        print(f"[translate_and_store] ChatMessage(id={chat_id}) not found")
        return

    # 2) Resolve the receiver
    role, pk = chat._parse_reference(chat.receiver)
    print(f"[translate_and_store] Receiver role={role}, pk={pk}")
    user = None
    if role == "tenant":
        user = TenantDetailsModel.objects.filter(pk=pk).first()
    elif role == "landlord":
        user = LandlordDetailsModel.objects.filter(pk=pk).first()
    print(f"[translate_and_store] Resolved user={user!r}")
    if not user or not user.preferred_language:
        print("[translate_and_store] No preferred_language—aborting")
        return

    target_code = user.preferred_language.code
    print(f"[translate_and_store] Translating to '{target_code}'")

    # 3) Perform translation with a timeout under the hood
    try:
        translated_text = GoogleTranslator(
            source="auto", target=target_code
        ).translate(chat.message)
        print(f"[translate_and_store] Translated: {translated_text!r}")
    except Exception as e:
        print(f"[translate_and_store] Translation failed: {e!r}")
        return

    # 4) Persist (or skip if already exists)
    try:
        obj, created = ChatMessageTranslationModel.objects.get_or_create(
            message=chat,
            language_code=target_code,
            defaults={"translated_text": translated_text}
        )
        action = "Created" if created else "Exists"
        print(f"[translate_and_store] {action} Translation(id={obj.id})")
    except Exception as e:
        print(f"[translate_and_store] DB save error: {e!r}")

    print(f"[translate_and_store] DONE chat_id={chat_id}")
