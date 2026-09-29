import os
import time
import asyncio
import speech_recognition as sr
import pygame
import edge_tts
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

#Carga la API Key guardada en el archivo .env e inicializa la conexión con la librería de Gemini.
load_dotenv()
client = genai.Client()

#Prepara el sistema de reproducción de audio
pygame.mixer.init()

VOZ_JARVIS = "es-MX-JorgeNeural" #Define la voz

def hablar(texto):
    print(f"\nJarvis: {texto}\n")
    archivo_audio = "respuesta.mp3"
    
    async def generar_audio():
        communicate = edge_tts.Communicate(texto, VOZ_JARVIS)
        await communicate.save(archivo_audio)

    asyncio.run(generar_audio())

    pygame.mixer.music.load(archivo_audio)
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
        
    pygame.mixer.music.unload()
    if os.path.exists(archivo_audio):
        os.remove(archivo_audio)
        
    time.sleep(0.3)

def escuchar_microfono():
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 1000  
    recognizer.dynamic_energy_threshold = False
    recognizer.pause_threshold = 1.0  

    with sr.Microphone() as source:
        print(" [Escuchando...] (Habla ahora)")
        try:
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
            print(" [Procesando voz...]")
            texto = recognizer.recognize_google(audio, language="es-AR")
            print(f"Tú (Voz): {texto}")
            return texto
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            print("Error conectando con el servicio de reconocimiento de voz.")
            return None

def enviar_mensaje_con_reintentos(chat_session, mensaje, max_reintentos=4):
    """Reintenta si hay demoras o congestión en la API."""
    for intento in range(max_reintentos):
        try:
            response = chat_session.send_message(mensaje)
            return response.text
        except Exception as e:
            print(f" Reintentando respuesta ({intento + 1}/{max_reintentos})... Detalle: {e}")
            time.sleep(2)  # Espera 2 segundos antes de volver a intentar
    return None

# Usamos el modelo requerido por tu API
MODELO = "gemini-3.6-flash"

chat = client.chats.create(
    model=MODELO,
    config={
        "system_instruction": "Eres Jarvis, una IA asistente avanzada. Responde en español latino, en frases breves, concisas y fluidas para voz."
    }
)

hablar("Sistemas de voz operativos. Te escucho señor.")

try:
    while True:
        mensaje_usuario = escuchar_microfono()
        
        if mensaje_usuario:
            if mensaje_usuario.lower() in ["salir", "apágate", "adios", "cancelar", "apagar sistemas"]:
                hablar("Apagando sistemas de voz. Hasta luego.")
                break
                
            respuesta_texto = enviar_mensaje_con_reintentos(chat, mensaje_usuario)
            
            if respuesta_texto:
                hablar(respuesta_texto)
            else:
                hablar("El servidor está muy congestionado. Intenta hacer tu consulta nuevamente.")

except KeyboardInterrupt:
    print("\n[Programa interrumpido por el usuario. Cerrando Jarvis...]")