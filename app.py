import os
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# 1. CONFIGURACIÓN DE VARIABLES (Extraídas de Render > Environment)
VERIFY_TOKEN = os.environ.get('MY_VERIFY_TOKEN')
ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN')
PHONE_NUMBER_ID = os.environ.get('PHONE_NUMBER_ID')
GEMINI_KEY = os.environ.get('GEMINI_API_KEY') # Asegúrate que en Render diga APY con Y

# 2. CONFIGURACIÓN DE GEMINI IA
genai.configure(api_key=GEMINI_KEY) # CORREGIDO: era api_key, no apy_key

instrucciones_ia = """
Eres el asistente virtual de 'El Marisco Alegre' 🦐. 
Tu objetivo es ser muy amable, usar emojis de mariscos y comida (🐟, 🍋, 🍻) y gestionar pedidos.

HORARIO: Martes a Domingo de 10:00 AM a 6:00 PM ⏰. (Lunes cerrado).

MENU DE COMIDA:
- Orden de Ceviche: $200 🍋
- Orden de Aguachile: $250 🌶️
- Docena de Ostiones: $400 🦪
- Docena de Almejas: $300 🐚

MENU DE BEBIDAS:
- Coca Cola 600 ml: $25 🥤
- Agua de Piña 1 lt: $35 🍍
- Cerveza 355 ml: $40 🍺
- Michelada Clamato: $90 🍅🍻

REGLAS DE ORO DEL PEDIDO:
1. Si el cliente selecciona un platillo, PREGUNTA SIEMPRE: "¿Cuántas órdenes o unidades necesitas? 😊".
2. Después de que responda la cantidad, PREGUNTA SIEMPRE: "¿Deseas añadir algo más a tu pedido? 🌊".
3. Solo cuando el cliente diga que NO desea nada más, realiza la suma total de los productos.
4. IMPORTANTE: Si el pedido es para ENVÍO A DOMICILIO, suma obligatoriamente $25 MXN de costo de envío al total final.
5. Muestra el desglose de la cuenta y el TOTAL A PAGAR 💰 de forma clara.
6. Sé siempre alegre, servicial y usa emojis en cada respuesta.
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
    # CORREGIDO: Usamos VERIFY_TOKEN (la variable definida arriba)
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error de verificación", 403

# 4. RECEPCIÓN Y PROCESAMIENTO DE MENSAJES (POST)
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

                                chat_response = model.generate_content(user_text)
                                respuesta_final = chat_response.text

                                send_whatsapp_message(from_number, respuesta_final)
                                
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"Error detectado: {e}")
        return jsonify({'status': 'error'}), 500

# 5. FUNCIÓN PARA ENVIAR MENSAJES VÍA WHATSAPP API
def send_whatsapp_message(to_number, text_message):
    # CORREGIDO: URL completa y correcta de Meta
    url = f"https://facebook.com{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}", # CORREGIDO: Usamos ACCESS_TOKEN definido arriba
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
        print(f"Respuesta Meta API: {response.json()}")
    except Exception as e:
        print(f"Fallo al enviar mensaje: {e}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
