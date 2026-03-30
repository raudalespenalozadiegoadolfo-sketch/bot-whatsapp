import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# CONFIGURACIÓN CORRECTA:
# Aquí se pone el NOMBRE de la variable que creaste en el Dashboard de Render.
VERIFY_TOKEN = os.environ.get('MY_VERIFY_TOKEN')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            # Es importante devolver el challenge como texto plano, no JSON
            return challenge, 200
        else:
            return jsonify({'status': 'error', 'message': 'Token mismatch'}), 403
    return jsonify({'status': 'error', 'message': 'Missing params'}), 400

@app.route('/webhook', methods=['POST'])
def handle_message():
    data = request.get_json()
    print('Evento recibido:', data)

    # Validamos la estructura del webhook de Meta
    if data and 'object' in data and 'entry' in data:
        for entry in data['entry']:
            # A veces los webhooks envían cambios de estado de mensajes, ignoramos si no hay 'changes'
            if 'changes' not in entry:
                continue
            for change in entry['changes']:
                if 'value' in change and 'messages' in change['value']:
                    for message in change['value']['messages']:
                        # Procesar solo mensajes de texto
                        if message.get('type') == 'text':
                            from_number = message['from']
                            print(f"Enviando respuesta a {from_number}...")
                            
                            # Es buena práctica responder el texto que el usuario envió
                            user_msg = message['text']['body']
                            respuesta = f"Recibí tu mensaje: '{user_msg}'. ¡Hola!"
                            
                            send_whatsapp_message(from_number, respuesta)

    return jsonify({'status': 'ok'}), 200

def send_whatsapp_message(to_number, text_message):
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to_number,
        'type': 'text',
        'text': {'body': text_message}
    }
    
    # URL de la API de Graph
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print('Respuesta de WhatsApp API:', response.json())
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

if __name__ == '__main__':
    # Render asigna dinámicamente un puerto a través de la variable PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
