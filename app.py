from flask import Flask, request, jsonify
import requests
import os
from google import genai

app = Flask(__name__)

# ==============================
# VARIABLES DE ENTORNO
# ==============================
VERIFY_TOKEN = os.environ.get('MY_VERIFY_TOKEN')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# ==============================
# CONFIGURAR GEMINI (SDK NUEVO)
# ==============================
client = genai.Client(api_key=GEMINI_KEY)

# ==============================
# INSTRUCCIONES DEL BOT
# ==============================
instrucciones_ia = """
Eres el asistente virtual de 'El Marisco Alegre' 🦐.
Sé amable, usa emojis y ayuda a tomar pedidos.

MENÚ:
- Ceviche $200 🥭
- Aguachile $250 🌶️
- Ostiones $400 🦪
- Almejas $300 🐚

BEBIDAS:
- Coca Cola $25 🥤
- Agua de piña $35 🍍
- Cerveza $40 🍺
- Michelada $90 🍺🍅

REGLAS:
- Pregunta cantidades
- Pregunta si desea algo más
- Calcula total al final
- Envío +$25
"""

# ==============================
# FUNCIÓN IA (NUEVA FORMA)
# ==============================
def generar_respuesta(texto_usuario):
    try:
        prompt = instrucciones_ia + "\nCliente: " + texto_usuario

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        print("Error IA:", e)
        return "😅 Ocurrió un error, intenta de nuevo."

# ==============================
# VERIFICACIÓN WEBHOOK (GET)
# ==============================
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error de verificación", 403

# ==============================
# RECIBIR MENSAJES (POST)
# ==============================
@app.route('/webhook', methods=['POST'])
def handle_message():
    try:
        data = request.get_json()

        if data.get('object') == 'whatsapp_business_account':
            for entry in data['entry']:
                for change in entry['changes']:
                    value = change.get('value')

                    if value and 'messages' in value:
                        for message in value['messages']:

                            if message['type'] == 'text':
                                from_number = message['from']
                                user_text = message['text']['body']

                                # 👉 RESPUESTA IA
                                respuesta_final = generar_respuesta(user_text)

                                # 👉 ENVIAR A WHATSAPP
                                send_whatsapp_message(from_number, respuesta_final)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error general:", e)
        return jsonify({"status": "error"}), 500

# ==============================
# ENVIAR MENSAJE WHATSAPP
# ==============================
def send_whatsapp_message(to_number, text_message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text_message}
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("Respuesta WhatsApp:", response.json())
    except Exception as e:
        print("Error enviando mensaje:", e)

# ==============================
# INICIAR SERVIDOR
# ==============================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
