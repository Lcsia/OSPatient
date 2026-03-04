import edge_tts
import pygame
import asyncio
import os
import nest_asyncio
import time
import speech_recognition as sr
import pyaudio
import wave
from openai import OpenAI # Ensure you have: pip install openai

class OSPatient:
    def __init__(self, image_folder="images"):
        """
        Initializes the patient library.
        :param image_folder: Path to the directory containing avatar images.
        """
        # Patch for asyncio loops in interactive environments like Anaconda/Jupyter
        nest_asyncio.apply()
        
        # Initialize pygame mixer for audio playback
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        self.image_folder = image_folder
        self.temp_audio = "temp_voice.mp3"
        self.recognizer = sr.Recognizer()
        
        # Mapping 2-letter codes to actual folder naming conventions
        self.mood_map = {
            "ar": "ActiveResistance",
            "de": "Despair",
            "am": "Ambivalence",
            "vr": "ValidationRelief"
        }

        # Voice configuration for Microsoft Edge TTS
        self.voices = {
            "male": "es-MX-JorgeNeural",
            "female": "es-MX-DaliaNeural"
        }
        
        # Audio stream settings for manual recording
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio_frames = []
        self.is_recording = False

    def generate_and_play_audio(self, text, gender="male"):
        """
        Converts text to speech, saves it to a temp file, and plays it.
        :param text: Text to be spoken.
        :param gender: 'male' or 'female'.
        :return: Duration of the generated audio in seconds.
        """
        voice = self.voices.get(gender, self.voices["male"])
        
        async def _save():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(self.temp_audio)

        # Stop and unload any existing music to prevent PermissionError (file lock)
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() 
        
        # Run async generation in the current event loop
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(_save())
        except PermissionError:
            # Brief wait if file is still locked by the OS
            time.sleep(0.3)
            loop.run_until_complete(_save())
        
        # Load and play the generated file
        pygame.mixer.music.load(self.temp_audio)
        audio_info = pygame.mixer.Sound(self.temp_audio)
        duration = audio_info.get_length()
        
        pygame.mixer.music.play()
        return duration

    def get_avatar_assets(self, mood_code, is_speaking=False):
        """
        Retrieves the appropriate image paths based on the mood and activity.
        :param mood_code: 2-letter string ('ar', 'de', 'am', 'vr').
        :param is_speaking: Boolean to toggle between static and mouth animation.
        :return: List of image file paths.
        """
        # Resolve full mood name from the map (defaults to ActiveResistance)
        mood_name = self.mood_map.get(mood_code.lower(), "ActiveResistance")
        prefix = os.path.join(self.image_folder, f"Img_{mood_name}")
        
        if is_speaking:
            # Returns a list of 2 images for alternating animation
            return [f"{prefix}_1.png", f"{prefix}_2.png"]
        else:
            # Returns a list with a single image for static display
            return [f"{prefix}_1.png"]

    # --- MANUAL RAM-BASED RECORDING METHODS ---

    def start_manual_listening(self):
        """
        Opens the microphone stream and prepares the buffer for manual capture.
        """
        self.audio_interface = pyaudio.PyAudio()
        self.audio_stream = self.audio_interface.open(
            format=self.audio_format, 
            channels=self.channels,
            rate=self.rate, 
            input=True, 
            frames_per_buffer=self.chunk
        )
        self.audio_frames = []
        self.is_recording = True

    def record_audio_chunk(self):
        """
        Reads a single chunk of data from the mic stream. 
        Should be called inside a loop while recording is active.
        """
        if self.is_recording:
            try:
                data = self.audio_stream.read(self.chunk)
                self.audio_frames.append(data)
            except Exception as e:
                print(f"Error recording chunk: {e}")

    def stop_and_transcribe_manual(self):
        """
        Stops the microphone stream and transcribes the cached RAM buffer.
        :return: Transcribed text string or error message.
        """
        self.is_recording = False
        
        # Safely close the stream and PyAudio interface
        if hasattr(self, 'audio_stream'):
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_interface.terminate()

        if not self.audio_frames:
            return "Error: No audio captured"

        # Concatenate frames and convert to AudioData for SpeechRecognition
        audio_data_bytes = b''.join(self.audio_frames)
        audio_segment = sr.AudioData(audio_data_bytes, self.rate, 2) # 2 bytes per sample for 16-bit
        
        try:
            # Use Google Web Speech API for transcription
            return self.recognizer.recognize_google(audio_segment, language="es-MX")
        except sr.UnknownValueError:
            return "Error: Speech not understood"
        except sr.RequestError:
            return "Error: Speech service unavailable"
        


# --- Inside OSPatient Class ---

    def _load_api_key(self):
        """
        Private method to read the API key from keys.txt.
        """
        try:
            # Assumes keys.txt is in the same directory
            with open("keys.txt", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            print("Error: 'keys.txt' file not found.")
            return None

    def get_ai_response(self, system_prompt, student_text):
        """
        Sends the system instruction and the user text to ChatGPT.
        :param system_prompt: The personality and rules for Mateo.
        :param student_text: What the student said.
        :return: String with the AI response.
        """
        # Lazy initialization of the OpenAI client
        if not hasattr(self, 'client'):
            api_key = self._load_api_key()
            if not api_key:
                return "Error: No API Key found in keys.txt"
            self.client = OpenAI(api_key=api_key)

        try:
            # Request to OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": student_text}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error connecting to OpenAI: {e}"