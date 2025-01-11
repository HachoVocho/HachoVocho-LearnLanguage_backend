# audio_processing/consumers.py

import json
import os
import subprocess
import tempfile
import django
import speech_recognition as sr
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
# Import services from other apps
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HachoVocho_learn_language_backend.settings')
django.setup()
from language_data.models import LanguageModel

from chatbot.services import generate_chatbot_response

class AudioStreamConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.accept()
        print("Client connected.")

    async def disconnect(self, close_code):
        print("Client disconnected.")

    async def receive(self, bytes_data=None):
        if bytes_data:
            try:
                # Separate metadata and audio
                data_parts = bytes_data.split(b'|', 1)
                if len(data_parts) != 2:
                    raise ValueError("Invalid data format: Expected metadata and audio data.")

                metadata_bytes, audio_data = data_parts
                metadata = json.loads(metadata_bytes.decode('utf-8'))
                preferred_language = metadata.get('preferredLanguage')
                learning_language = metadata.get('learningLanguage')
                learning_language_level = metadata.get('learningLanguageLevel')

                # Fetch the learning language code from the database
                learning_language_code = await self.get_language_code(learning_language)
                preferred_language_code = await self.get_language_code(preferred_language)
                if not learning_language_code:
                    raise ValueError(f"Language '{learning_language}' not found in database.")

                # Save the received bytes as a temporary WebM file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
                    temp_webm.write(audio_data)
                    webm_file_path = temp_webm.name

                # Convert WebM to WAV using FFmpeg
                wav_file_path = webm_file_path.replace(".webm", ".wav")
                subprocess.run(
                    [
                        "ffmpeg",
                        "-i", webm_file_path,  # Input file
                        "-ar", "16000",        # Resample to 16 kHz
                        "-ac", "1",            # Convert to mono
                        wav_file_path,
                    ],
                    check=True,
                    stderr=subprocess.DEVNULL,  # Suppress FFmpeg errors
                    stdout=subprocess.DEVNULL,  # Suppress FFmpeg output
                )
                print(f"Audio successfully converted to {wav_file_path}")

                # Transcribe the audio using the speech_recognition library
                transcription = await self.transcribe_audio(wav_file_path, language=learning_language_code)
                print(f"Transcription: {transcription}")

                # Clean up temporary files
                os.remove(webm_file_path)
                os.remove(wav_file_path)

                # Generate chatbot response asynchronously
                response_json = await self.generate_chatbot_response_async(transcription,preferred_language,learning_language,learning_language_level,preferred_language_code,learning_language_code)
                
                # Send the response back to Flutter frontend
                await self.send(json.dumps(response_json))

            except subprocess.CalledProcessError as e:
                print(f"FFmpeg error: {e}")
                error_response = {"error": "Unable to process audio."}
                await self.send(json.dumps(error_response))
            except sr.UnknownValueError:
                error_response = {"error": "Could not understand the audio."}
                await self.send(json.dumps(error_response))
            except sr.RequestError as e:
                error_response = {"error": f"Speech recognition request failed; {e}."}
                await self.send(json.dumps(error_response))
            except Exception as e:
                print(f"Unexpected error: {e}")
                error_response = {"error": "Unexpected processing error."}
                await self.send(json.dumps(error_response))

    @sync_to_async
    def transcribe_audio(self, wav_file_path, language="de-DE"):
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)  # Read the entire audio file
            transcription = recognizer.recognize_google(audio_data, language=language)
            return transcription

    async def generate_chatbot_response_async(self, transcription,preferred_language,learning_language,learning_language_level,preferred_language_code,learning_language_code):
        return await generate_chatbot_response(transcription,preferred_language,learning_language,learning_language_level,preferred_language_code,learning_language_code)

    @sync_to_async
    def get_language_code(self, language_name):
        try:
            language = LanguageModel.objects.get(name=language_name)
            return language.translation_code
        except ObjectDoesNotExist:
            return None