from flask import Flask, request
import requests
import os
import re
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)

# 🔐 VARIABLES
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🛒 CARRITOS
carritos = {}

# 🍽️ MENÚ
MENU = {
    "almejas": 300,
    "ostiones": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# 🕒 HORARIO
from datetime import datetime
from zoneinfo import ZoneInfo

def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))

    dia = ahora.weekday()  # 0=lunes
    hora = ahora.hour

    return dia >= 1 and dia <= 6 and 12 <= hora < 23

# 📩 WHATSAPP
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
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=data)

# 🧠 IA RESPUESTA
def responder_ia(mensaje):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Eres un mesero amable, divertido, con emojis y enfocado en vender comida."},
                {"role": "user", "content": mensaje}
            ]
        )
        return response.choices[0].message.content
    except:
        return "😅 Hubo un problema, intenta de nuevo."

# 🍽️ MENÚ TEXTO
def menu_texto():
    return """🍽️ MENÚ

🦪 Comida:
* Almejas $300
* Ostiones $400
* Ceviche $200
* Ceviche camarón $250
* Aguachile $260

🥤 Bebidas:
* Cerveza $40
* Michelada $100
* Refresco $35

¿Qué deseas ordenar? 😋"""

# 🛒 PROCESAR PEDIDO INTELIGENTE
def procesar_pedido(texto, carrito):
    encontrado = False

    for item, precio in MENU.items():
        if item in texto:
            match = re.search(rf"(\\d+).*{item}", texto)
            cantidad = int(match.group(1)) if match else 1

            total = cantidad * precio

            carrito["items"].append({
                "producto": item,
                "cantidad": cantidad,
                "total": total
            })

            carrito["total"] += total
            encontrado = True

    return encontrado

# 🌐 VERIFY
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "error", 403

# 🌐 WEBHOOK
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]["text"]["body"].lower()
        numero = value["messages"][0]["from"]

        if numero not in carritos:
            carritos[numero] = {
                "items": [],
                "total": 0,
                "estado": "inicio"
            }

        carrito = carritos[numero]

        # 🕒 horario
        if not dentro_horario():
            enviar(numero, "⏰ Estamos cerrados.\nAbrimos de martes a domingo de 12 a 6 pm 🙏")
            return "ok", 200

        # 👋 saludo
        if carrito["estado"] == "inicio":
            carrito["estado"] = "pedido"
            enviar(numero, f"¡Hola! 😊 Bienvenido\n\n{menu_texto()}")
            return "ok", 200

        # 🛒 pedido
        if carrito["estado"] == "pedido":
            agregado = procesar_pedido(msg, carrito)

            if agregado:
                resumen = "🛒 Tu carrito:\n\n"
                for item in carrito["items"]:
                    resumen += f"- {item['cantidad']} x {item['producto']} = ${item['total']}\n"

                resumen += f"\n💰 Total: ${carrito['total']}"
                resumen += "\n\nEscribe confirmar para finalizar 😄"

                enviar(numero, resumen)
            else:
                # IA responde si no detecta pedido
                respuesta = responder_ia(msg)
                enviar(numero, respuesta)

            return "ok", 200

        # ✅ confirmar
        if "confirmar" in msg:
            carrito["estado"] = "final"
            enviar(numero, "🚚 ¿Es domicilio o recoger?")
            return "ok", 200

        # 🚚 final
        if carrito["estado"] == "final":
            if "domicilio" in msg:
                carrito["total"] += 25
                enviar(numero, f"🧾 Total con envío: ${carrito['total']}\n\nGracias por tu pedido 😄🍽️")
            else:
                enviar(numero, f"🧾 Total: ${carrito['total']}\n\nPasa a recoger 😄")

            carritos[numero] = {"items": [], "total": 0, "estado": "inicio"}
            return "ok", 200

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

if __name__ == "__main__":
    app.run()
