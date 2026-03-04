import edge_tts
import asyncio
import os
import nest_asyncio
import time
from openai import OpenAI
import streamlit as st

# Intentar importar librerías locales, si no existen (en la nube), no rompen el código
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

class OSPatient:
    def __init__(self, image_folder="images"):
        nest_asyncio.apply()
        
        # Inicializar mixer solo si existe la librería (Local)
        if pygame and not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except:
                pass
            
        self.image_folder = image_folder
        self.temp_audio = "temp_voice.mp3"
        self.mood_map = {
            "ar": "ActiveResistance",
            "de": "Despair",
            "am": "Ambivalence",
            "vr": "ValidationRelief"
        }
        self.voices = {"male": "es-MX-JorgeNeural", "female": "es-MX-DaliaNeural"}

    def _load_api_key(self):
        # Primero busca en Secrets (Nube), luego en archivo local
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
        try:
            with open("keys.txt", "r") as f:
                return f.read().strip()
        except:
            return None

    def generate_and_play_audio(self, text, gender="male"):
        voice = self.voices.get(gender, self.voices["male"])
        
        async def _save():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(self.temp_audio)

        # Detener audio previo si pygame existe
        if pygame and pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload() 
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(_save())
        except:
            time.sleep(0.3)
            loop.run_until_complete(_save())
        
        return 5.0 # Duración estimada

    def get_ai_response(self, system_prompt, student_text):
        api_key = self._load_api_key()
        if not api_key: return "Error: No API Key found."
        
        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
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

