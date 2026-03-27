import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración desde variables de entorno
TOKEN_VERIFICACION = os.environ.get("TOKEN_VERIFICACION", "my_token_secreto_123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

@app.route('/')
def home():
    return "Servidor del Bot de WhatsApp Activo", 200

@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    # Meta envía estos parámetros para validar tu webhook
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if token == TOKEN_VERIFICACION:
        return str(challenge), 200
    
    return "Token de verificación incorrecto", 403

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    try:
        data = request.get_json()
        # Imprime en los logs para que veas qué llega
        print(f"Datos recibidos: {data}")

        # Verificamos si hay mensajes en la petición
        if 'entry' in data and data['entry'][0]['changes'][0]['value'].get('messages'):
            mensaje_obj = data['entry'][0]['changes'][0]['value']['messages'][0]
            numero = mensaje_obj['from']
            texto_usuario = mensaje_obj.get('text', {}).get('body', '')
            
            if texto_usuario:
                enviar_mensaje(numero, f"Hola! Recibí tu mensaje: {texto_usuario}")

        return "EVENT_RECEIVED", 200
    except Exception as e:
        print(f"Error procesando: {e}")
        return "Error interno", 500

def enviar_mensaje(numero, texto):
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
    print(f"Respuesta de Meta: {response.status_code} - {response.text}")
    return response.json()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
