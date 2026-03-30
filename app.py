import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuración desde variables de entorno en Render
VERIFY_TOKEN = os.environ.get('my_token_secreto')
ACCESS_TOKEN = os.environ.get('EAAXhxO2OiUsBRC63x4ZBzbfDQMbOniGxLTrgTcFp4xh3uS7nC5T1WD4hz0japFZA6FZCfpPRYAfcPR78VsaX2W5pYG2bPvaey9sMZAzChbqjZAZBZANKVWxUOdZCs7VmnQJc1n2yxLWltLIrhifKT3wafxrZB6AxVf3ObHqZBZCEmB8tsBrQ9Fau9jUzUOhXvKn')
PHONE_NUMBER_ID = os.environ.get('1059311390588707')

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return jsonify({'status': 'error', 'message': 'Token mismatch'}), 403
    return jsonify({'status': 'error', 'message': 'Missing params'}), 400

@app.route('/webhook', methods=['POST'])
def handle_message():
    data = request.get_json()
    print('Evento recibido:', data)

    if data and 'object' in data and 'entry' in data:
        for entry in data['entry']:
            for change in entry['changes']:
                if 'value' in change and 'messages' in change['value']:
                    for message in change['value']['messages']:
                        if message['type'] == 'text':
                            from_number = message['from']
                            print(f"Enviando respuesta a {from_number}...")
                            send_whatsapp_message(from_number, "Hola")

    return jsonify({'status': 'ok'}), 200

def send_whatsapp_message(to_number, text_message):
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'messaging_product': 'whatsapp',
        'to': to_number,
        'type': 'text',
        'text': {'body': text_message}
    }
    
    # URL CORREGIDA: Asegúrate de que tenga las "/" después de .com y v22.0
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    try:
        response = requests.post(url, headers=headers, json=data )
        print('Respuesta de WhatsApp API:', response.json())
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
