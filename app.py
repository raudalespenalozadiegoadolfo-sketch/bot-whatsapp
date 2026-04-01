from flask import Flask, request
import requests
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 📌 DATOS DEL NEGOCIO
MENU = """
🍽️ MENÚ

🦪 Comida:
- Orden de almejas $300
- Docena de ostiones $400
- Orden de ceviche $200
- Ceviche de camarón $250
- Aguachile $260

🥤 Bebidas:
- Cerveza 355 ml $40
- Michelada de clamato $100
- Refresco $35
"""

HORARIO = "🕒 Martes a Domingo de 12:00 PM a 6:00 PM"

# 📌 ENVIAR MENSAJE
def enviar_whatsapp(numero, mensaje):
    url = f"https://graph.facebook.com/v17.0/{os.environ.get('PHONE_NUMBER_ID')}/messages"
    
    headers = {
        "Authorization": f"Bearer {os.environ.get('WHATSAPP_ACCESS_TOKEN')}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    requests.post(url, headers=headers, json=data)

# 📌 WEBHOOK VERIFY
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == os.environ.get("MY_VERIFY_TOKEN"):
        return request.args.get("hub.challenge")
    return "Error", 403

# 📌 WEBHOOK MENSAJES
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
        numero = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

        print("Mensaje:", mensaje)

        # 🧠 PROMPT DEL BOT
        prompt = f"""
Eres un bot de restaurante amable con emojis.

Este es el menú:
{MENU}

Horario:
{HORARIO}

Reglas:
- Muestra el menú si te lo piden
- Ayuda a tomar pedidos
- Pregunta si desea algo más
- Pide nombre y dirección
- Calcula total
- Si es domicilio agrega $25
- Responde con emojis y amable

Cliente dice: {mensaje}
"""

        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente de pedidos de comida"},
                {"role": "user", "content": prompt}
            ]
        )

        texto = respuesta.choices[0].message.content

        enviar_whatsapp(numero, texto)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run()
