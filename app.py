import os
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== MENÚ =====
menu = {
    "almeja": 300,
    "ostion": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# ===== MEMORIA =====
usuarios = {}

# ===== IA INTERPRETAR =====
def interpretar_con_ia(texto):
    prompt = f"""
Eres un sistema que interpreta pedidos de restaurante.

Menú:
{menu}

Devuelve JSON con:
accion: agregar, quitar, ver, finalizar, saludo, datos
items: lista de productos con cantidad

Ejemplo:
"quiero 2 ceviches y 1 cerveza"
→ {{"accion":"agregar","items":[{{"producto":"ceviche","cantidad":2}},{{"producto":"cerveza","cantidad":1}}}]}}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": texto}
        ]
    )

    contenido = response.choices[0].message.content

    try:
        return eval(contenido)
    except:
        return {"accion": "error", "items": []}

# ===== CALCULAR =====
def calcular(pedido):
    total = 0
    texto = "🧾 Tu pedido:\n\n"

    for p, c in pedido.items():
        subtotal = menu[p] * c
        total += subtotal
        texto += f"{c} x {p} = ${subtotal}\n"

    texto += f"\n💰 Total: ${total}"
    return texto

# ===== WHATSAPP =====
def enviar(numero, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    requests.post(url, headers=headers, json=data)

# ===== BOTONES =====
def botones(numero):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": "👋 Bienvenido a Marisco Alegre 🦐"
            },
            "action": {
                "buttons": [
                    {"type": "reply","reply": {"id": "menu","title": "📋 Menú"}},
                    {"type": "reply","reply": {"id": "pedir","title": "🛒 Pedir"}}
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)

# ===== MENÚ =====
def mostrar_menu(numero):
    texto = "📋 MENÚ:\n\n"
    for p, precio in menu.items():
        texto += f"• {p} - ${precio}\n"

    enviar(numero, texto)

# ===== WEBHOOK =====
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        entry = data["entry"][0]["changes"][0]["value"]
        if "messages" not in entry:
            return "ok"

        msg = entry["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {
                "pedido": {},
                "estado": "inicio",
                "nombre": "",
                "direccion": ""
            }

        user = usuarios[numero]

        # ===== BOTONES =====
        if msg.get("type") == "interactive":
            btn = msg["interactive"]["button_reply"]["id"]

            if btn == "menu":
                mostrar_menu(numero)

            elif btn == "pedir":
                enviar(numero, "¿Qué deseas ordenar? 😊")

            return "ok"

        texto = msg["text"]["body"]

        # ===== IA =====
        resultado = interpretar_con_ia(texto)
        accion = resultado.get("accion")

        # ===== ACCIONES =====
        if accion == "saludo":
            botones(numero)

        elif accion == "ver":
            mostrar_menu(numero)

        elif accion == "agregar":
            for item in resultado["items"]:
                p = item["producto"]
                c = item["cantidad"]

                user["pedido"][p] = user["pedido"].get(p, 0) + c

            enviar(numero, calcular(user["pedido"]))
            enviar(numero, "¿Deseas agregar algo más o finalizar?")

        elif accion == "quitar":
            for item in resultado["items"]:
                p = item["producto"]
                c = item["cantidad"]

                if p in user["pedido"]:
                    user["pedido"][p] -= c
                    if user["pedido"][p] <= 0:
                        del user["pedido"][p]

            enviar(numero, calcular(user["pedido"]))

        elif accion == "finalizar":
            user["estado"] = "nombre"
            enviar(numero, "¿A nombre de quién es el pedido? 👤")

        elif user["estado"] == "nombre":
            user["nombre"] = texto
            user["estado"] = "direccion"
            enviar(numero, "📍 ¿Cuál es tu dirección?")

        elif user["estado"] == "direccion":
            user["direccion"] = texto
            user["estado"] = "confirmado"

            enviar(numero,
                f"✅ Pedido confirmado\n\n"
                f"👤 {user['nombre']}\n"
                f"📍 {user['direccion']}\n\n"
                f"{calcular(user['pedido'])}"
            )

        else:
            enviar(numero, "No entendí 😅")

    except Exception as e:
        print("ERROR:", e)

    return "ok"

if __name__ == "__main__":
    app.run(port=10000)
