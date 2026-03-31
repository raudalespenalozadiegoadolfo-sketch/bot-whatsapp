import os
import google.generativeai as genai # Nueva librería
from flask import Flask, request, jsonify
import requests

# Configuración de Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Configuramos el "carácter" de tu bot
model = genai.GenerativeModel('gemini-1.5-flash', 
    system_instruction="Eres el asistente virtual de 'El Marisco Alegre'. Eres amable, servicial y experto en mariscos. Responde siempre de forma breve.")

def obtener_respuesta_gemini(texto_usuario):
    try:
        response = model.generate_content(texto_usuario)
        return response.text
    except Exception as e:
        print(f"Error en Gemini: {e}")
        return "Lo siento, estoy teniendo un problema técnico. ¿En qué más puedo ayudarte?"

@app.route('/webhook', methods=['POST'])
def handle_message():
    data = request.get_json()
    if data and 'object' in data:
        for entry in data['entry']:
            for change in entry['changes']:
                if 'value' in change and 'messages' in change['value']:
                    for message in change['value']['messages']:
                        if message.get('type') == 'text':
                            from_number = message['from']
                            user_text = message['text']['body']
                            
                            # Llamamos a Gemini para que piense la respuesta
                            respuesta_ia = obtener_respuesta_gemini(user_text)
                            
                            # Enviamos la respuesta de la IA a WhatsApp
                            send_whatsapp_message(from_number, respuesta_ia)
                            
    return jsonify({'status': 'ok'}), 200

# ... (Tu función send_whatsapp_message se mantiene igual)
