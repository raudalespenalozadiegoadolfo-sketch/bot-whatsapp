import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración desde variables de entorno (Render)
TOKEN_VERIFICACION = os.environ.get("TOKEN_VERIFICACION", "my_token_secreto_123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

@app.route('/')
def home():
    return "Servidor del Bot de WhatsApp Activo", 200

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    # Meta envía estos parámetros para validar tu servidor
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Comparamos el token que envía Meta con el que tú configuraste
    if token == TOKEN_VERIFICACION:
        return str(challenge), 200
    
    # Siempre retornamos algo para evitar el error 'did not return a valid response'
    return "Token de verificación incorrecto", 403

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    try:
        data = request.get_json()
        
        # Log para ver en Render qué nos está enviando Meta exactamente
        print(f"Evento recibido: {data}")

        # Estructura de WhatsApp para extraer el mensaje
        if 'entry' in data:
            for entry in data['entry']:
                for change in entry.get('changes', []):
                    value = change.get('value', {})
                    if 'messages' in value:
                        for message in value['messages']:
                            numero = message['from']
                            texto_usuario = message.get('text', {}).get('body', '')
                            
                            if texto_usuario:
                                print(f"Enviando respuesta a {numero}...")
                                enviar_mensaje(numero, f"¡Hola! Recibí tu mensaje: {texto_usuario}")

        # Meta requiere que respondamos con un 200 OK para confirmar recepción
        return "EVENT_RECEIVED", 200
        
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return "Error interno", 500

def enviar_mensaje(numero, texto):
    # Usamos la versión v21.0 de la API (la más reciente en 2026)
    url = f"https://graph.facebook.com{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"Respuesta de Meta API: {response.status_code} - {response.text}")
    return response.json()

if __name__ == '__main__':
    # Render asigna el puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
