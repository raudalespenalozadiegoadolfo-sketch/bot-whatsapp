from flask import Flask, request
import requests
import os
import google.generativeai as genai

app = Flask(__name__)

# 🔑 CONFIGURACIÓN
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")


# 📩 FUNCIÓN PARA ENVIAR MENSAJES
def enviar_whatsapp(numero, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    response = requests.post(url, headers=headers, json=data)
    print("Respuesta WhatsApp:", response.text)


# 🔐 VERIFICACIÓN DEL WEBHOOK (META)
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Error de verificación", 403


# 📥 RECEPCIÓN DE MENSAJES
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # 🚫 Ignorar eventos sin mensajes (statuses, etc.)
        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"]

        print("Mensaje recibido:", texto)

        # 🤖 RESPUESTA CON GEMINI
        response = genai.GenerativeModel("gemini-2.0-flash").generate_content(texto)
        respuesta = response.text

        # 📤 Enviar respuesta
        enviar_whatsapp(numero, respuesta)

    except Exception as e:
        print("ERROR:", e)
        return "error", 200

    return "ok", 200


# 🚀 INICIO DEL SERVIDOR
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
