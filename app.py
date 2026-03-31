from flask import Flask, request, jsonify
import requests
import os
from google import genai

app = Flask(__name__)

# =========================
# VARIABLES DE ENTORNO
# =========================
VERIFY_TOKEN = os.environ.get("MY_VERIFY_TOKEN")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# =========================
# CONFIGURAR GEMINI NUEVO
# =========================
client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# VERIFICACIÓN WEBHOOK (GET)
# =========================
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Error de verificación", 403


# =========================
# RECIBIR MENSAJES (POST)
# =========================
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    try:
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    if "messages" in value:
                        for message in value["messages"]:
                            if message.get("type") == "text":

                                from_number = message["from"]
                                user_text = message["text"]["body"]

                                print("Mensaje recibido:", user_text)

                                # =========================
                                # RESPUESTA CON GEMINI NUEVO
                                # =========================
                                try:
                                    response = client.models.generate_content(
                                        model="gemini-1.5-flash",
                                        contents=user_text
                                    )

                                    respuesta_final = response.text

                                except Exception as e:
                                    print("Error IA:", e)
                                    respuesta_final = "😅 Ocurrió un error, intenta de nuevo."

                                # =========================
                                # ENVIAR RESPUESTA
                                # =========================
                                send_whatsapp_message(from_number, respuesta_final)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("Error general:", e)
        return jsonify({"status": "error"}), 500


# =========================
# ENVIAR MENSAJE WHATSAPP
# =========================
def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("Respuesta WhatsApp:", response.json())
    except Exception as e:
        print("Error enviando mensaje:", e)


# =========================
# INICIO SERVIDOR
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
