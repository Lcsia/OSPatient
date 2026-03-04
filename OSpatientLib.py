import edge_tts
import asyncio
import os
import nest_asyncio
import time
from openai import OpenAI
import streamlit as st

# Intentar importar librerías de audio local
try:
    import pygame
    # Intentamos una inicialización falsa para ver si falla
    pygame_disponible = True
except (ImportError, NotImplementedError):
    pygame = None
    pygame_disponible = False

class OSPatient:
    def __init__(self, image_folder="images"):
        nest_asyncio.apply()
        
        self.image_folder = image_folder
        self.temp_audio = "temp_voice.mp3"
        
        # --- PROTECCIÓN DE PYGAME EN EL INIT ---
        if pygame_disponible and pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception:
                # Si falla aquí, desactivamos pygame para el resto de la sesión
                global pygame_disponible
                pygame_disponible = False
            
        self.mood_map = {
            "ar": "ActiveResistance",
            "de": "Despair",
            "am": "Ambivalence",
            "vr": "ValidationRelief"
        }
        self.voices = {"male": "es-MX-JorgeNeural", "female": "es-MX-DaliaNeural"}

    def _load_api_key(self):
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

        # Solo usamos pygame si está disponible
        if pygame_disponible and pygame and pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload() 
            except:
                pass
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(_save())
        except:
            time.sleep(0.3)
            loop.run_until_complete(_save())
        
        # En la nube no cargamos el archivo en pygame, 
        # solo lo dejamos guardado para que AppStream lo lea con Base64
        if pygame_disponible and pygame and pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(self.temp_audio)
                pygame.mixer.music.play()
            except:
                pass
        
        return 5.0

    def get_ai_response(self, system_prompt, student_text):
        api_key = self._load_api_key()
        if not api_key: return "Error: No API Key."
        
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
            return f"Error: {e}"


