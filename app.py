import os
import time #maneja pausas y tiempos de espera
import asyncio 
import subprocess
import datetime
import speech_recognition as sr #libreria para capturar el audio del micro y enviarlo a motores de reconocimiento de voz
import pygame #Librería multimedia que se utiliza exclusivamente por su módulo mixer para reproducir el archivo de audio .mp3
import edge_tts #Librería que se conecta de forma gratuita a los servidores de sintesis de voz de Microsoft Edge para convertir texto a audio sintético
from dotenv import load_dotenv
from google import genai #Módulo principal del SDK oficial de Google para interactuar con los modelos de IA Gemini
from google.genai.errors import APIError

#Carga la API Key guardada en el archivo .env e inicializa la conexión con la librería de Gemini.
load_dotenv()
client = genai.Client()

#Prepara el sistema de reproducción de audio
pygame.mixer.init()

VOZ_JARVIS = "es-MX-JorgeNeural" #Define la voz

#DEFINICIÓN DE HERRAMIENTAS (TOOLS)
# ================================
def obtener_hora_actual() -> str:
    """Devuelve la fecha y hora actual del sistema. Úsala cuando el usuario pregunte la hora o qué día es hoy."""
    #obtenemos la fecha y hora actual
    ahora = datetime.datetime.now()
    return ahora.strftime("Hoy es %A %d de %B de %Y y son las %H:%M.")

def crear_nota(titulo: str, contenido: str) -> str:
    """Crea un archivo de texto con una nota o recordatorio guardado por el usuario..."""
    nombre_archivo = f"{titulo.replace(' ', "_".lower().txt)}"#Limpia el título ingresado por voz para que sea un nombre de archivo válido en Windows
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"Nota '{titulo}' guardada con éxito en {nombre_archivo}."
    except Exception as e:
        return f"Error al guardar la nota: {e}"
    
def abrir_aplicacion(nombre_app: str) -> str:
    """Abre una aplicación instalada en el sistema como bloc de notas, calculadora o navegador.

    Args:
        nombre_app: El nombre de la aplicación a abrir (ej: 'notepad', 'calc', 'chrome', 'vscode').
    """
    app = nombre_app.lower()
    
    try:
        if "notepad" in app or "bloc" in app or "nota" in app:
            subprocess.Popen(["notepad.exe"])
            return "Abriendo el Bloc de Notas."
        elif "calc" in app or "calculadora" in app:
            subprocess.Popen(["calc.exe"])
            return "Abriendo la calculadora."
        elif "OperaGX" in app or "navegador" in app:
            os.system("start operaGX")
            return "Abriendo Opera GX."
        elif "code" in app or "vscode" in app:
            os.system("code")
            return "Abriendo Visual Studio Code."
        else:
            return f"No sé cómo abrir la aplicación '{nombre_app}'."
    except Exception as e:
        return f"Error al intentar abrir {nombre_app}: {e}"


MIS_HERRAMIENTAS = [obtener_hora_actual, crear_nota, abrir_aplicacion]

DICCIONARIO_FUNCIONES = {
    "obtener_hora_actual": obtener_hora_actual,
    "crear_nota": crear_nota,
    "abrir_aplicacion": abrir_aplicacion
}

#FUNCIONES DE AUDIO Y VOZ
#========================
def hablar(texto):
    print(f"\nJarvis: {texto}\n")
    archivo_audio = "respuesta.mp3" #nombre del archivo temporal donde se guardará el audio
    
    async def generar_audio(): 
        communicate = edge_tts.Communicate(texto, VOZ_JARVIS) #Prepara la solicitud enviando el texto y la voz seleccionada
        await communicate.save(archivo_audio) #Descarga el audio generado y lo guarda en el disco duro de forma asíncrona

    asyncio.run(generar_audio()) #Ejecuta la función asíncrona generar_audio() de forma síncrona dentro del flujo principal del programa

    pygame.mixer.music.load(archivo_audio) #Carga el archivo respuesta.mp3 en el reproductor de audio de pygame
    pygame.mixer.music.play() #Inicia la reproducción del audio por los altavoces.
    
    while pygame.mixer.music.get_busy(): #pygame esté reproduciendo sonido (get_busy() == True)
        pygame.time.Clock().tick(10) #el programa pausa la ejecución revisando cada 10 milisegundos. Evita que el código avance mientras Jarvis habla
        
    pygame.mixer.music.unload()
    if os.path.exists(archivo_audio):
        os.remove(archivo_audio)
        
    time.sleep(0.3) #Pausa de 300 milisegundos para asegurar que el eco de los parlantes no sea grabado

def escuchar_microfono():
    recognizer = sr.Recognizer() #Crea un objeto reconocedor de voz de la librería speech_recognition
    recognizer.energy_threshold = 1000  #Cualquier sonido por debajo de esta intensidad será considerado ruido de fondo
    recognizer.dynamic_energy_threshold = False
    recognizer.pause_threshold = 1.0 #Indica que el programa debe esperar 1 segundo completo de silencio continuo para dar por terminada la frase del usuario

    with sr.Microphone() as source: #Abre el micrófono
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

# MANEJO DE PETICIONES Y FUNCTION CALLING
# =======================================

def procesar_mensaje_con_tools(chat_session, mensaje):
    """Envía el mensaje a Gemini y maneja la llamada a herramientas si la IA lo solicita."""
    response = chat_session.send_message(mensaje)
    
    # Verificar si Gemini quiere ejecutar una función/herramienta
    if response.function_calls:
        for call in response.function_calls:
            nombre_funcion = call.name
            argumentos = call.args
            
            print(f"\n[Ejecutando Herramienta Local: {nombre_funcion}({argumentos})]")
            
            # Buscar la función en nuestro diccionario y ejecutarla
            if nombre_funcion in DICCIONARIO_FUNCIONES:
                funcion_local = DICCIONARIO_FUNCIONES[nombre_funcion]
                resultado = funcion_local(**argumentos)
                
                # Le devolvemos el resultado de la función a Gemini para que formule la respuesta final
                respuesta_final = chat_session.send_message(
                    types.Part.from_function_response(
                        name=nombre_funcion,
                        response={"result": resultado}
                    )
                )
                return respuesta_final.text
    
    return response.text

# INICIALIZACIÓN Y BUCLE PRINCIPAL
# ===================================

# Usamos el modelo requerido por tu API
MODELO = "gemini-3.6-flash"

#Inicializa la sesión de chat
chat = client.chats.create(
    model=MODELO,
    config={
        "system_instruction": "Eres Jarvis, una IA asistente avanzada. Responde en español latino, en frases breves, concisas y fluidas para voz.",
        "tools": MIS_HERRAMIENTAS
    }
)

hablar("Sistemas de voz operativos. Te escucho.")

try:
    while True: #Bucle infinito que mantiene a Jarvis activo y escuchando de forma continua.
        mensaje_usuario = escuchar_microfono() #Llama a la función de escucha y guarda el texto
        
        if mensaje_usuario:
            if mensaje_usuario.lower() in ["salir", "apágate", "adios", "cancelar", "apagar sistemas"]:
                hablar("Apagando sistemas. Hasta luego.")
                break
                
            try:
                respuesta_texto = procesar_mensaje_con_tools(chat, mensaje_usuario)
                if respuesta_texto:
                    hablar(respuesta_texto)
            except APIError as e:
                print(f"Error en API: {e}")
                hablar("Hubo un problema de conexión con el servidor.")

except KeyboardInterrupt:#Si el usuario interrumpe la consola presionando Ctrl + C
    print("\n[Programa interrumpido por el usuario. Cerrando Jarvis...]")