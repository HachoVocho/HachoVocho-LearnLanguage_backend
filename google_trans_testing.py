from aiogoogletrans import Translator  # Async version of googletrans
import asyncio

async def main():
    # Initialize translator
    translator = Translator()

    # Translate text
    translation = await translator.translate("Hello, world!", src="en", dest="es")
    print(translation.text)  # Prints: Hola, mundo!

# Run the async function
asyncio.run(main())
