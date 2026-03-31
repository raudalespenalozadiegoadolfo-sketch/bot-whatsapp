from flask import Flask, request
import requests
import os
from google import genai

app = Flask(__name__)

# VARIABLES
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# CONFIG GEMINI NUEVO
client = genai.Client(api_key=GEMINI_API_KEY)


# 🔹 VERIFICACIÓN WEBHOOK
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Error de verificación", 403


# 🔹 RECIBIR MENSAJES
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        texto = mensaje["text"]["body"]
        numero = mensaje["from"]

        print("Mensaje recibido:", texto)

        # 🔥 GEMINI NUEVO (IMPORTANTE)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=texto
        )

        respuesta = response.text

    except Exception as e:
        print("ERROR GEMINI:", e)
        respuesta = "😅 Ocurrió un error, intenta de nuevo."

    enviar_whatsapp(numero, respuesta)
    return "ok", 200


# 🔹 ENVIAR MENSAJE
def enviar_whatsapp(numero, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": mensaje}
    }

    requests.post(url, headers=headers, json=data)


# 🔹 INICIO
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
