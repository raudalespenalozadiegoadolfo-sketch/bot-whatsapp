import os
import requests
from flask import Flask, request
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo
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
            "historial": [],
            "estado": "inicio"
        }
    return usuarios[numero]

# 🕒 HORARIO
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    return 11 <= ahora.hour < 23

# 📤 ENVIAR MENSAJE
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

# 🤖 GPT RESPUESTA SEGURA
def responder_gpt(usuario, mensaje):
    try:
        historial = usuario["historial"][-10:]

        mensajes = [
            {
                "role": "system",
                "content": """
Eres un asistente del restaurante "Mariscos El Alegre".

- Habla natural como humano
- Sé amable y breve
- Puedes ayudar a pedir comida
- Responde también a mensajes normales (gracias, hola, etc)
"""
            }
        ]

        for h in historial:
            mensajes.append(h)

        mensajes.append({"role": "user", "content": mensaje})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=mensajes
        )

        respuesta = response.choices[0].message.content

        usuario["historial"].append({"role": "user", "content": mensaje})
        usuario["historial"].append({"role": "assistant", "content": respuesta})

        return respuesta

    except Exception as e:
        print("ERROR GPT:", e)
        return "😅 Ocurrió un error, intenta de nuevo"

# 🧠 INTERPRETAR PEDIDO CON GPT
def interpretar_pedido(texto):
    try:
        prompt = f"""
Convierte este pedido a JSON:

"{texto}"

Menú:
{MENU}

Ejemplo:
{{"almeja":2,"cerveza":1}}

Solo responde JSON válido.
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:
        print("ERROR INTERPRETAR:", e)
        return {}

# 🔄 WEBHOOK
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # 🔐 VERIFICACIÓN META
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

    # 🚫 FUERA DE HORARIO
    if not dentro_horario():
        enviar(numero, "🕒 Estamos cerrados. Abrimos de 11am a 11pm 🙏")
        return "ok"

    # 👋 BIENVENIDA
    if usuario["estado"] == "inicio":
        enviar(numero, "👋 Bienvenido a Mariscos El Alegre 😎\n\n¿Te muestro el menú?")
        usuario["estado"] = "menu"
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

¿Deseas modificar algo o continuar? 😎""")

        return "ok"

    # 🤖 RESPUESTA NORMAL
    respuesta = responder_gpt(usuario, texto)

    if not respuesta:
        respuesta = "😅 No entendí bien, ¿puedes repetirlo?"

    enviar(numero, respuesta)

    return "ok"

# 🚀 ARRANQUE CORRECTO EN RENDER
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
