from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# =========================
# 🔐 CONFIGURACIÓN
# =========================

VERIFY_TOKEN = "mi_token_verificacion"
WHATSAPP_TOKEN = "TU_TOKEN_DE_META"
PHONE_NUMBER_ID = "TU_PHONE_NUMBER_ID"

# =========================
# 📤 ENVIAR MENSAJE
# =========================

def enviar(numero, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {
            "body": texto
        }
    }

    try:
        r = requests.post(url, headers=headers, json=data)
        print("RESPUESTA WHATSAPP:", r.status_code, r.text)
    except Exception as e:
        print("ERROR ENVÍO:", e)

# =========================
# 📥 WEBHOOK VERIFY
# =========================

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Error de verificación", 403

# =========================
# 📩 WEBHOOK MENSAJES
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("DATA RECIBIDA:", data)

        if data and "entry" in data:
            for entry in data["entry"]:
                for change in entry["changes"]:
                    value = change["value"]

                    if "messages" in value:
                        for mensaje in value["messages"]:
                            numero = mensaje["from"]

                            if "text" in mensaje:
                                texto = mensaje["text"]["body"]
                                print("MENSAJE:", texto)

                                # =========================
                                # 🤖 RESPUESTA INTELIGENTE BÁSICA
                                # =========================

                                texto_lower = texto.lower()

                                if "hola" in texto_lower:
                                    respuesta = "👋 ¡Bienvenido al Marisco Alegre 🦐!\n¿Te gustaría ver el menú?"
                                
                                elif "menu" in texto_lower or "menú" in texto_lower:
                                    respuesta = """📋 MENÚ:

🦐 Almejas $300
🦪 Ostiones $400
🐟 Ceviche $200
🍤 Ceviche camarón $250
🔥 Aguachile $260

🍺 Cerveza $40
🍹 Michelada $100
🥤 Refresco $35

Ejemplo: 2 almejas y 1 cerveza"""
                                
                                elif "gracias" in texto_lower:
                                    respuesta = "😊 ¡Gracias a ti! Aquí seguimos para cuando gustes 🦐🍺"

                                else:
                                    respuesta = "🤖 Estoy listo para tomar tu pedido.\nEjemplo: 2 almejas y 1 cerveza"

                                # =========================
                                # 📤 RESPONDER
                                # =========================

                                enviar(numero, respuesta)

        return "ok", 200

    except Exception as e:
        print("ERROR WEBHOOK:", e)
        return "error", 500


# =========================
# 🚀 INICIALIZACIÓN
# =========================

print("🚀 Bot iniciado correctamente")
