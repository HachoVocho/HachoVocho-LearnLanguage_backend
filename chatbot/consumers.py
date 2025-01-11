# chatbot/consumers.py

import json
import os
import subprocess
import tempfile
import speech_recognition as sr
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from asgiref.sync import sync_to_async

from .services import generate_chatbot_response, generate_conversation_with_topic  # We'll define this
# ... import any other needed modules

class BotConversationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("BotConversationConsumer connected.")

    async def disconnect(self, close_code):
        print("BotConversationConsumer disconnected.")

    async def receive(self, bytes_data=None, text_data=None):
        if text_data:
            data = json.loads(text_data)
            print(data)
            action = data.get('action')

            if action == 'start_conversation':
                # Topic-based conversation start
                topic = data.get('topic')
                if topic:
                    response = await sync_to_async(generate_conversation_with_topic)(
                        user_input=topic,
                        topic=topic,
                        is_first=True
                    )
                    await self.send(json.dumps(response))

            elif action == 'text_message':
                # Continuing topic-based conversation
                user_input = data.get('text')
                topic = data.get('topic')  # Keep track of topic in client if needed
                response = await sync_to_async(generate_conversation_with_topic)(
                    user_input=user_input,
                    topic=topic,
                    is_first=False
                )
                await self.send(json.dumps(response))

        elif bytes_data:
            # Handle audio for topic-based conversation
            try:
                transcription = await self._transcribe_audio(bytes_data)
                # Continue the topic-based conversation using the transcription
                topic = "Your default topic"  # Update if necessary
                response = await sync_to_async(generate_conversation_with_topic)(
                    user_input=transcription,
                    topic=topic,
                    is_first=False
                )
                await self.send(json.dumps(response))
            except Exception as e:
                error_res = {"error": "Audio processing failed."}
                await self.send(json.dumps(error_res))

    @sync_to_async
    def _transcribe_audio(self, bytes_data):
        # same approach as your audio transforms:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
            temp_webm.write(bytes_data)
            webm_file_path = temp_webm.name

        # Convert to WAV
        wav_file_path = webm_file_path.replace(".webm", ".wav")
        subprocess.run(
            [
                "ffmpeg", "-i", webm_file_path,
                "-ar", "16000", "-ac", "1",
                wav_file_path
            ],
            check=True
        )
        os.remove(webm_file_path)

        # Transcribe
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="de-DE")
        os.remove(wav_file_path)
        return text

    async def _generate_bot_reply(self, user_input, topic=None, is_first=False):
        """
        Calls a service that queries GPT with the user's input + topic
        Returns the JSON that your Flutter app expects
        """
        return await sync_to_async(generate_chatbot_response)(user_input, topic, is_first=is_first)
