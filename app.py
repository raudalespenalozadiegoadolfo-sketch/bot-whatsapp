from flask import Flask, request, jsonify
import requests
import os
import google.generativeai as genai

app = Flask(__name__)

# ==============================
# 1. VARIABLES DE ENTORNO
# ==============================
VERIFY_TOKEN = os.environ.get('MY_VERIFY_TOKEN')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# ==============================
# 2. CONFIGURAR GEMINI
# ==============================
genai.configure(api_key=GEMINI_KEY)

instrucciones_ia = """
Eres el asistente virtual de 'El Marisco Alegre' 🦐.
Tu objetivo es ser muy amable, usar emojis de mariscos y comida y gestionar pedidos.

HORARIO:
Martes a Domingo de 10:00 AM a 6:00 PM (Lunes cerrado).

MENÚ:
- Ceviche: $200 🥭
- Aguachile: $250 🌶️
- Ostiones: $400 🦪
- Almejas: $300 🐚

BEBIDAS:
- Coca Cola: $25 🥤
- Agua de Piña: $35 🍍
- Cerveza: $40 🍺
- Michelada: $90 🍺🍅

REGLAS:
1. Pregunta cantidades siempre.
2. Pregunta si desea algo más.
3. Calcula total solo al final.
4. Envío: +$25
5. Muestra total claro.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=instrucciones_ia
)

# ==============================
# 3. VERIFICACIÓN WEBHOOK
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
# 4. RECIBIR MENSAJES
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

                                # 👉 Generar respuesta con IA
                                try:
                                    response = model.generate_content(user_text)
                                    respuesta_final = response.text
                                except Exception as e:
                                    print(f"Error IA: {e}")
                                    respuesta_final = "😅 Ocurrió un error, intenta de nuevo."

                                # 👉 Enviar respuesta
                                send_whatsapp_message(from_number, respuesta_final)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error detectado: {e}")
        return jsonify({"status": "error"}), 500

# ==============================
# 5. ENVIAR MENSAJE WHATSAPP
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
        print(f"Error enviando mensaje: {e}")

# ==============================
# 6. INICIAR APP
# ==============================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
