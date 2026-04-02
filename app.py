import os
import requests
from flask import Flask, request
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import re

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

# 🧠 MEMORIA GLOBAL
usuarios = {}

def obtener_usuario(numero):
    if numero not in usuarios:
        usuarios[numero] = {
            "pedido": {},
            "historial": [],
            "estado": "inicio"
        }
    return usuarios[numero]

# 🕒 HORARIO
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    return 11 <= ahora.hour < 23

# 📤 ENVIAR WHATSAPP
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

# 🧾 CALCULAR TOTAL
def calcular_total(pedido):
    total = 0
    detalle = ""

    for item, cantidad in pedido.items():
        precio = MENU.get(item, 0)
        subtotal = precio * cantidad
        total += subtotal
        detalle += f"• {cantidad} x {item} = ${subtotal}\n"

    return total, detalle

# 🤖 GPT RESPUESTA CON MEMORIA
def responder_gpt(usuario, mensaje):
    historial = usuario["historial"][-10:]  # últimas 10 interacciones

    mensajes = [
        {"role": "system", "content": f"""
Eres un asistente de restaurante llamado "Mariscos El Alegre".

FUNCIONES:
- Conversar como humano (natural)
- Tomar pedidos
- Modificar pedidos
- Ser amable y vendedor

MENÚ:
{MENU}

PEDIDO ACTUAL:
{usuario["pedido"]}

INSTRUCCIONES:
- Si el cliente pide comida → interpreta
- Si quiere modificar → actualiza
- Si habla normal → responde natural
- Si dice "gracias" → responde humano
- NO repitas el pedido innecesariamente
"""}
    ]

    # Agregar historial
    for h in historial:
        mensajes.append(h)

    mensajes.append({"role": "user", "content": mensaje})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=mensajes
    )

    respuesta = response.choices[0].message.content

    # Guardar memoria
    usuario["historial"].append({"role": "user", "content": mensaje})
    usuario["historial"].append({"role": "assistant", "content": respuesta})

    return respuesta

# 🧠 INTERPRETAR PEDIDO CON GPT
def interpretar_pedido(texto):
    prompt = f"""
Convierte este pedido a JSON:

"{texto}"

Menú:
{MENU}

Ejemplo salida:
{{"almeja":2,"cerveza":1}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {}

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

    usuario = obtener_usuario(numero)

    # 🚫 FUERA DE HORARIO
    if not dentro_horario():
        enviar(numero, "🕒 Estamos cerrados. Abrimos de 11am a 11pm 🙏")
        return "ok"

    # 👋 PRIMER MENSAJE
    if usuario["estado"] == "inicio":
        enviar(numero, "👋 Bienvenido a Mariscos El Alegre 😎\n\n¿Te muestro el menú?")
        usuario["estado"] = "menu"
        return "ok"

    # 🧾 INTENTAR INTERPRETAR PEDIDO
    pedido_detectado = interpretar_pedido(texto)

    if pedido_detectado:
        for k, v in pedido_detectado.items():
            usuario["pedido"][k] = usuario["pedido"].get(k, 0) + v

        total, detalle = calcular_total(usuario["pedido"])

        enviar(numero, f"""🧾 TU PEDIDO:

{detalle}

💰 Total: ${total}

¿Deseas modificar algo o continuamos? 😎""")

        return "ok"

    # 🤖 RESPUESTA GPT
    respuesta = responder_gpt(usuario, texto)
    enviar(numero, respuesta)

    return "ok"

if __name__ == "__main__":
    app.run(port=5000)
