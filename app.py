import os
import requests
from flask import Flask, request
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import json

app = Flask(__name__)

# 🔑 CONFIG
VERIFY_TOKEN = "tu_token"
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧾 MENÚ
MENU = {
    "almeja": 300,
    "ostion": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# 🧠 MEMORIA
usuarios = {}

def obtener_usuario(numero):
    if numero not in usuarios:
        usuarios[numero] = {
            "pedido": {},
            "estado": "inicio"
        }
    return usuarios[numero]

# 🕒 HORARIO
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    return 11 <= ahora.hour < 23

# 📤 ENVIAR
def enviar(numero, texto):
    try:
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
    except Exception as e:
        print("ERROR ENVIANDO:", e)

# 🧾 TOTAL
def calcular_total(pedido):
    total = 0
    detalle = ""

    for item, cantidad in pedido.items():
        precio = MENU.get(item, 0)
        subtotal = precio * cantidad
        total += subtotal
        detalle += f"• {cantidad} x {item} = ${subtotal}\n"

    return total, detalle

# 🛡 PARSER ULTRA (SIN GPT)
def interpretar_pedido(texto):
    texto = texto.lower()

    # normalizar
    texto = texto.replace(",", " ")
    texto = texto.replace("\n", " ")

    pedido = {}

    for item in MENU.keys():
        patron = rf"(\d+)\s*(?:orden(?:es)?\s*de\s*)?{item}"
        matches = re.findall(patron, texto)

        for m in matches:
            cantidad = int(m)
            pedido[item] = pedido.get(item, 0) + cantidad

    return pedido

# 🤖 GPT SOLO CONVERSACIÓN (SEGURO)
def responder_gpt(texto):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente amable de restaurante mexicano"
                },
                {"role": "user", "content": texto}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("ERROR GPT:", e)
        return "😅 No entendí bien, ¿puedes repetirlo?"

# 🔄 WEBHOOK
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error"

    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"].lower()
    except:
        return "ok"

    print("MENSAJE:", texto)

    usuario = obtener_usuario(numero)

    # 🚫 HORARIO
    if not dentro_horario():
        enviar(numero, "🕒 Estamos cerrados. Abrimos de 11am a 11pm 🙏")
        return "ok"

    # 👋 INICIO
    if usuario["estado"] == "inicio":
        enviar(numero, "👋 Bienvenido a Mariscos El Alegre 😎\n\nEscribe tu pedido (ej: 2 almejas y 1 cerveza)")
        usuario["estado"] = "activo"
        return "ok"

    # 🔁 MODIFICAR PEDIDO
    if "modificar" in texto or "cambiar" in texto:
        usuario["pedido"] = {}
        enviar(numero, "✏️ Listo, dime tu nuevo pedido")
        return "ok"

    # 🧾 DETECTAR PEDIDO
    pedido_detectado = interpretar_pedido(texto)

    if pedido_detectado:
        for k, v in pedido_detectado.items():
            usuario["pedido"][k] = usuario["pedido"].get(k, 0) + v

        total, detalle = calcular_total(usuario["pedido"])

        enviar(numero, f"""🧾 TU PEDIDO:

{detalle}

💰 Total: ${total}

¿Algo más o confirmamos? 😎""")

        return "ok"

    # 💬 CONVERSACIÓN
    if any(x in texto for x in ["hola", "gracias", "menu", "qué hay"]):
        respuesta = responder_gpt(texto)
        enviar(numero, respuesta)
        return "ok"

    # 🛟 FALLBACK
    enviar(numero, "😅 No entendí bien. Ejemplo: 2 almejas y 1 cerveza")
    return "ok"

# 🚀 RENDER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
