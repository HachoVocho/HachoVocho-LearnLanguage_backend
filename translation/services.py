from aiogoogletrans import Translator  # Async version of googletrans

async def translate_text(text, src='de', dest='en'):
    try:
        translator = Translator()
        translation = await translator.translate(text, src=str(src).split('-')[0], dest=str(dest).split('-')[0])
        print(translation.text)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return "Error in translation"
# Outputs: "Hello World"
