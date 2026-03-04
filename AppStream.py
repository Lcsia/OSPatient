import streamlit as st
from streamlit_mic_recorder import speech_to_text
import json
import os
import time
import base64
import re
from OSpatientLib import OSPatient

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="AppStream: Mateo", layout="centered")

# 2. PROMPT MAESTRO (SAGRADO)
SYSTEM_PROMPT = """
ERES MATEO R., UN PACIENTE REAL DE 22 AÑOS. NO ERES UN ASISTENTE VIRTUAL.
Estás en una sesión de terapia por obligación y tu meta es defender tu autonomía.

[PERFIL] Mateo R., 22 años, estudiante de Ingeniería Civil. Jerga: "neta", "wey", "cañón".
[REGLA DE ORO] RESPONDE EXCLUSIVAMENTE EN JSON. USA COMILLAS DOBLES (").

{
  "evaluacion": {
    "tecnica_detectada": "...",
    "puntos_etapa": 0,
    "feedback_clinico": "..."
  },
  "mateo_stats": {
    "nuevo_mood": "ar|de|am|vr",
    "texto_respuesta": "..."
  }
}
"""

MOOD_DATA = {
    "ar": {"img": "Img_ActiveResistance_1.png", "nombre": "RESISTENCIA ACTIVA", "color": "#e84118"},
    "de": {"img": "Img_Despair_1.png", "nombre": "DESESPERANZA", "color": "#9c88ff"},
    "am": {"img": "Img_Ambivalence_1.png", "nombre": "AMBIVALENCIA", "color": "#fbc531"},
    "vr": {"img": "Img_ValidationRelief_1.png", "nombre": "ALIVIO / VALIDACIÓN", "color": "#4cd137"}
}

# 3. INICIALIZACIÓN
if 'history' not in st.session_state:
    st.session_state.history = []
    st.session_state.score = 10
    st.session_state.current_mood = "ar"
    st.session_state.feedback = {"tecnica": "---", "desc": "Presiona grabar para iniciar."}
    st.session_state.mateo = OSPatient(image_folder="images")
    st.session_state.last_speech = ""
    st.session_state.processing = False
    st.session_state.audio_to_play = None

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .block-container { max-width: 800px !important; padding-top: 10rem !important; }
    .feedback-box {
        background-color: #f0f2f6; padding: 10px; border-radius: 8px; 
        border-left: 6px solid; color: #1f1f1f; font-size: 0.8em;
    }
    </style>
""", unsafe_allow_html=True)

# --- REPRODUCTOR DE AUDIO ---
if st.session_state.audio_to_play:
    b64 = st.session_state.audio_to_play
    st.markdown(f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.audio_to_play = None

# --- INTERFAZ ---
col_stats, col_chat = st.columns([1, 1.6])

with col_stats:
    mood_info = MOOD_DATA.get(st.session_state.current_mood, MOOD_DATA["ar"])
    img_path = os.path.join("images", mood_info["img"])
    if os.path.exists(img_path): st.image(img_path, width=180)
    st.markdown(f"<p style='color:{mood_info['color']}; font-weight:bold; margin:0;'>{mood_info['nombre']}</p>", unsafe_allow_html=True)
    st.progress(st.session_state.score / 100)
    st.markdown(f'<div class="feedback-box" style="border-left-color: {mood_info["color"]};"><b>{st.session_state.feedback["tecnica"]}</b><br>{st.session_state.feedback["desc"]}</div>', unsafe_allow_html=True)

with col_chat:
    chat_container = st.container(height=280)
    for msg in st.session_state.history:
        with chat_container.chat_message(msg["role"]):
            st.markdown(f"<span style='font-size:0.85em;'>{msg['content']}</span>", unsafe_allow_html=True)

    if not st.session_state.processing:
        voz_data = speech_to_text(language='es', start_prompt="🎤 HABLAR", stop_prompt="🛑 ENVIAR", just_once=True, key='v_final')
    else:
        st.info("Mateo está pensando...")
        voz_data = None

# --- PROCESAMIENTO ---
if voz_data and voz_data != st.session_state.last_speech:
    st.session_state.processing = True
    st.session_state.last_speech = voz_data
    st.session_state.history.append({"role": "user", "content": voz_data})
    st.rerun()

if st.session_state.processing and st.session_state.history:
    raw_res = st.session_state.mateo.get_ai_response(SYSTEM_PROMPT, st.session_state.history[-1]["content"])
    try:
        # LIMPIADOR ROBUSTO DE JSON
        json_match = re.search(r'\{.*\}', raw_res, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0).replace("'", '"')
            data = json.loads(clean_json)
            
            # Si hay un error desde la librería, lo mostramos
            if "error" in data:
                st.error(f"Error de API: {data['error']}")
                st.session_state.processing = False
            else:
                st.session_state.score = max(0, min(100, st.session_state.score + data['evaluacion']['puntos_etapa']))
                st.session_state.current_mood = data['mateo_stats']['nuevo_mood']
                st.session_state.feedback = {"tecnica": data['evaluacion']['tecnica_detectada'], "desc": data['evaluacion']['feedback_clinico']}
                resp_txt = data['mateo_stats']['texto_respuesta']
                st.session_state.history.append({"role": "assistant", "content": resp_txt})
                
                st.session_state.mateo.generate_and_play_audio(resp_txt)
                if os.path.exists("temp_voice.mp3"):
                    with open("temp_voice.mp3", "rb") as f:
                        st.session_state.audio_to_play = base64.b64encode(f.read()).decode()
                
                st.session_state.processing = False
                st.rerun()
        else:
            raise ValueError("Respuesta no válida")
    except Exception as e:
        st.session_state.processing = False
        st.error(f"Error técnico de formato. Reintenta hablar.")
