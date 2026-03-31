import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. CARGA DE VARIABLES DESDE RENDER (Environment Variables)
VERIFY_TOKEN = os.environ.get('MY_VERIFY_TOKEN')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY')

# 2. CONFIGURACIÓN DE LA IA (GEMINI)
genai.configure(api_key=GEMINI_KEY)

instrucciones_ia = """
Eres el asistente virtual de 'El Marisco Alegre' 🦐.
Tu objetivo es ser muy amable, usar emojis de mariscos y comida (🐟, 🍋, 🍻) y gestionar pedidos.

HORARIO: Martes a Domingo de 10:00 AM a 6:00 PM ⏰. (Lunes cerrado).

MENÚ DE COMIDA:
- Orden de Ceviche: $200 🍋
- Orden de Aguachile: $250 🌶️
- Docena de Ostiones: $400 🦪
- Docena de Almejas: $300 🐚

MENU DE BEBIDAS:
- Coca Cola 600 ml: $25 🥤
- Agua de Piña 1 lt: $35 🍍
- Cerveza 355 ml: $40 🍺
- Michelada Clamato: $90 🍅🍻

REGLAS DE ATENCIÓN:
1. Siempre pregunta cuántas órdenes o unidades necesita de cada platillo que el cliente mencione.
2. Después de que el cliente elija algo, pregunta SIEMPRE: "¿Deseas añadir algo más a tu pedido? 😊".
3. Si el cliente dice que NO desea nada más, realiza la suma total de los productos.
4. Si el pedido es para ENVÍO A DOMICILIO, suma obligatoriamente $25 MXN por concepto de envío al total.
5. Muestra el desglose de la cuenta de forma clara y el TOTAL A PAGAR 💰.
6. Sé siempre alegre y servicial.
"""

model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=instrucciones_ia
)

# 3. VERIFICACIÓN DEL WEBHOOK (GET)
@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error de token", 403

# 4. RECEPCIÓN DE MENSAJES (POST)
@app.route('/webhook', methods=['POST'])
def handle_message():
    data = request.get_json()
    try:
        if data.get('object') == 'whatsapp_business_account':
            for entry in data['entry']:
                for change in entry['changes']:
                    value = change.get('value')
                    if value and 'messages' in value:
                        for message in value['messages']:
                            if message['type'] == 'text':
                                from_number = message['from']
                                user_text = message['text']['body']

                                # La IA genera la respuesta basada en el historial (contexto)
                                chat_response = model.generate_content(user_text)
                                respuesta_final = chat_response.text

                                send_whatsapp_message(from_number, respuesta_final)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

# 5. FUNCIÓN DE ENVÍO A WHATSAPP
def send_whatsapp_message(to_number, text_message):
    url = f"https://facebook.com{PHONE_NUMBER_ID}/messages"
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
        requests.post(url, json=payload, headers=headers)
    except Exception as e:
        print(f"Error al enviar: {e}")

if __name__ == '__main__':
    # Render usa el puerto 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
