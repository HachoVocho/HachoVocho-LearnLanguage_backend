# chatbot/services.py

import google.generativeai as genai
from django.conf import settings
from translation.services import translate_text

async def generate_chatbot_response(transcription,preferred_language,learning_language,learning_language_level,preferred_language_code,learning_language_code):
    try:
        # Configure Gemini AI with your API key from Django settings
        genai.configure(api_key=settings.GEMINI_API_KEY)  # Store API key in settings
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Define parameters for the conversation
        language = learning_language  # Adjust as needed or extract from transcription
        level = learning_language_level  # Example level
        category_id = "general_conversation"  # Example category

        # Create a prompt that asks for a single reply to continue the conversation
        prompt = (
            f"The following input is a statement or question spoken by a person fluent in {language}:\n\n"
            f"Input: {transcription}\n\n"
            f"The person they are speaking to (me) is learning {language}. Please provide a natural and engaging response in {language}, "
            f"suitable for the {level} level, which keeps the conversation going and encourages interaction. "
            f"Format your response as follows:\n\n"
            f"{language}: [Your suggestion in {language}]\n"
            f"{preferred_language}: [The same suggestion translated into {preferred_language}]\n\n"
            f"Ensure the response is appropriate for a language learner and keep it short."
        )

        # Generate content using Gemini AI
        suggestion = model.generate_content(prompt).text
        print(f"Gemini Suggestion: {suggestion}")

        # Extract German and English responses
        learning_language_response, preferred_language_response = parse_suggestion(suggestion,preferred_language,learning_language)
        print(f"Gemini Suggestion 123: {learning_language_response} {preferred_language_response}")
        # Translate transcription for completeness
        translation = await translate_text(transcription, src=learning_language_code, dest=preferred_language_code)
        print(f"Gemini Suggestion 456: {translation}")
        # Structure the response JSON
        response = {
            "transcription": transcription,
            "translation": str(translation),
            "suggestedLearningLanguageResponse": learning_language_response,
            "suggestedPreferredLanguageResponse": preferred_language_response,
            'learning_language_code': learning_language_code,
            'preferred_language_code':preferred_language_code,
        }
        print('response')
        print(response)
        return response

    except Exception as e:
        print(f"Exception in Gemini model: {e}")
        return {
            "transcription": transcription,
            "translation": "",
            "suggestedResponseGerman": "An error occurred while generating a response.",
            "suggestedResponseEnglish": "An error occurred while generating a response.",
        }

def parse_initial_suggestion(suggestion):
    f"""
    Parses the Gemini AI suggestion to extract German, English, and Next Suggestion for the first message.
    Assumes the format:
    German: <response in German>
    English: <translated response in English>
    Next: <what the user should say next in German>
    """
    german_response = ""
    english_response = ""
    explanation = ""
    next_suggestion = ""
    lines = suggestion.strip().split('\n')
    for line in lines:
        if line.startswith("German:"):
            german_response = line.replace("German:", "").strip()
        elif line.startswith("English:"):
            english_response = line.replace("English:", "").strip()
        elif line.startswith("Explanation:"):
            explanation = line.replace("Explanation:", "").strip()
        elif line.startswith("Next:"):
            next_suggestion = line.replace("Next:", "").strip()
    return german_response, english_response,explanation, next_suggestion

def parse_suggestion(suggestion,preferred_language,learning_language):
    f"""
    Parses the Gemini AI suggestion to extract {learning_language} and {preferred_language} responses.
    Assumes the format:
    {learning_language}: <response in {learning_language}>
    {preferred_language}: <translated response in {preferred_language}>
    """
    learning_language_response = ""
    preferred_language_response = ""
    lines = suggestion.strip().split('\n')
    for line in lines:
        if line.startswith(f"{learning_language}:"):
            learning_language_response = line.replace(f"{learning_language}:", "").strip()
        elif line.startswith(f"{preferred_language}:"):
            preferred_language_response = line.replace(f"{preferred_language}:", "").strip()
    return learning_language_response, preferred_language_response

def generate_conversation_with_topic(user_input, topic=None, is_first=False):
    """
    Generates a conversation reply based on a specific topic using Gemini AI.

    :param user_input: The user's input text or audio transcription.
    :param topic: The conversation topic, if provided (used in the first interaction).
    :param is_first: Whether this is the first message of the topic-based conversation.
    :return: A dictionary with German and English responses.
    """
    try:
        # Configure Gemini AI with your API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Define the context for the prompt
        if is_first:
            # Initial conversation with the topic
            context = (
                f"You are an AI engaging in a conversation about the topic '{topic}'. "
                f"Start the conversation by introducing the topic and asking a relevant question. "
            )
        else:
            # Continuing the conversation with the user's input
            context = (
                f"You are continuing a conversation. The user just said: '{user_input}'. "
                f"Respond naturally and suggest what the user should say next. "
            )

        # Build the prompt for Gemini AI
        prompt = (
            f"{context}"
            f"Respond in German and provide a translation in English. "
            f"Then, suggest what the user should say next as part of the conversation. "
            f"Additionally, explain basic rules highlighting the differences between German and English, focusing on structure and key grammatical points to help the user understand how the two languages differ. "
            f"Format the response as:\n\n"
            f"German: [Your response in German. Only in German]\n"
            f"English: [Your response translated into English]\n"
            f"Explanation: [Brief explanation of differences in sentencees you gave for both languages, and also just saying which words means what]\n"
            f"Next: [What the user should say next in German]\n\n"
            f"Keep the response concise and suitable for a language beginner learner."
        )

        # Generate AI response
        suggestion = model.generate_content(prompt).text
        print(f"Gemini AI Suggestion: {suggestion}")

        # Parse the Gemini response
        german_response, english_response, explanation,next_suggestion = parse_initial_suggestion(suggestion)

        # Create the response dictionary
        response = {
            "transcription": german_response,  # AI's German response
            "explanation": explanation,
            "translation": english_response,  # AI's English response
            "suggestedResponseGerman": next_suggestion,  # Suggested next German response
            "suggestedResponseEnglish": translate_text(next_suggestion, src="de", dest="en"),  # Translated next response
        }

        print('response:', response)
        return response

    except Exception as e:
        print(f"Error during conversation generation: {e}")
        return {
            "error": "An error occurred while generating the conversation.",
        }


    except Exception as e:
        print(f"Exception in Gemini model: {e}")
        return {
            "transcription": user_input,
            "translation": "",
            "suggestedResponseGerman": "An error occurred while generating a response.",
            "suggestedResponseEnglish": "An error occurred while generating a response.",
        }
