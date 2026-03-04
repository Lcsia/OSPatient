import edge_tts
import asyncio
import os
import nest_asyncio
import time
from openai import OpenAI
import streamlit as st  # Importamos streamlit para leer los secrets

# --- IMPORTS PROTEGIDOS PARA LA NUBE ---
try:
    import pygame
except ImportError:
    pygame = None

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import wave
except ImportError:
    wave = None

class OSPatient:
    def __init__(self, image_folder="images"):
        nest_asyncio.apply()
        
        # 1. FIX DE AUDIO: Evitar error si pygame no inicia o no hay tarjeta de sonido
        if pygame and not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except:
                pass # Ignoramos el fallo en la nube
            
        self.image_folder = image_folder
        self.temp_audio = "temp_voice.mp3"
        
        # 2. FIX DE RECONOCEDOR: Solo si sr existe
        self.recognizer = sr.Recognizer() if sr else None
        
        self.mood_map = {
            "ar": "ActiveResistance",
            "de": "Despair",
            "am": "Ambivalence",
            "vr": "ValidationRelief"
        }

        self.voices = {
            "male": "es-MX-JorgeNeural",
            "female": "es-MX-DaliaNeural"
        }
        
        # Configuraciones de PyAudio (se quedan como valores, no causan error)
        self.audio_format = 8 # pyaudio.paInt16 por defecto
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.audio_frames = []
        self.is_recording = False

    def generate_and_play_audio(self, text, gender="male"):
        voice = self.voices.get(gender, self.voices["male"])
        
        async def _save():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(self.temp_audio)

        # 3. FIX DE PLAYBACK: Solo usar pygame si está disponible e iniciado
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() 
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(_save())
        except PermissionError:
            time.sleep(0.3)
            loop.run_until_complete(_save())
        
        # En la nube esto fallará, pero no importa porque AppStream usará Base64
        if pygame and pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(self.temp_audio)
                pygame.mixer.music.play()
            except:
                pass
        
        return 5.0 # Duración dummy para evitar errores de retorno

    def get_avatar_assets(self, mood_code, is_speaking=False):
        mood_name = self.mood_map.get(mood_code.lower(), "ActiveResistance")
        prefix = os.path.join(self.image_folder, f"Img_{mood_name}")
        if is_speaking:
            return [f"{prefix}_1.png", f"{prefix}_2.png"]
        else:
            return [f"{prefix}_1.png"]

    # --- CARGA SEGURA DE API KEY ---
    def _load_api_key(self):
        # 4. FIX DE LLAVE: Primero intenta leer de Streamlit Secrets (Nube)
        # Si no existe, intenta leer de keys.txt (Local)
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
        
        try:
            with open("keys.txt", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def get_ai_response(self, system_prompt, student_text):
        if not hasattr(self, 'client'):
            api_key = self._load_api_key()
            if not api_key:
                return "Error: No API Key found."
            self.client = OpenAI(api_key=api_key)

        try:
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

