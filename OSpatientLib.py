import edge_tts
import asyncio
import os
import nest_asyncio
import time
from openai import OpenAI
import streamlit as st
import json

# Intentar importar librerías de audio local (PC)
try:
    import pygame
    pygame_disponible = True
except (ImportError, NotImplementedError):
    pygame = None
    pygame_disponible = False

class OSPatient:
    def __init__(self, image_folder="images"):
        nest_asyncio.apply()
        self.image_folder = image_folder
        self.temp_audio = "temp_voice.mp3"
        
        # Protección de inicialización para el servidor
        if pygame_disponible and pygame:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except:
                pass
            
        self.voices = {"male": "es-MX-JorgeNeural", "female": "es-MX-DaliaNeural"}

    def _load_api_key(self):
        # Prioridad 1: Secrets de Streamlit (Nube)
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
        # Prioridad 2: Archivo local (PC)
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

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(_save())
        except:
            time.sleep(0.2)
            loop.run_until_complete(_save())
        return 5.0

    def get_ai_response(self, system_prompt, student_text):
        api_key = self._load_api_key()
        if not api_key: 
            return json.dumps({"error": "No API Key"})
        
        client = OpenAI(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": student_text}
                ],
                response_format={ "type": "json_object" }
            )
            return response.choices[0].message.content
        except Exception as e:
            # Línea 75 Corregida: Evita SyntaxError usando json.dumps
            return json.dumps({"error": str(e)})
