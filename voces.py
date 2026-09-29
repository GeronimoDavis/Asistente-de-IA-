import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

for i, voice in enumerate(voices):
    print(f"Índice: {i} | Nombre: {voice.name} | ID: {voice.id} | Idiomas: {voice.languages}")