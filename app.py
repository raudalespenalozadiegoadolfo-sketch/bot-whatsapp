import os
import re
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN_WHATSAPP")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_PHONE = os.getenv("ADMIN_PHONE")  # Tu número
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== BASE DE DATOS EN MEMORIA =====
usuarios = {}

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

# ===== UTILIDADES =====
def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=data)


def enviar_botones(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
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
            "body": {"text": texto},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu", "title": "📋 Ver menú"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🛒 Hacer pedido"}}
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)


def mostrar_menu():
    texto = "📋 MENÚ:\n\n"
    for k, v in menu.items():
        texto += f"• {k} - ${v}\n"
    texto += "\nEjemplo: 2 almejas y 1 cerveza"
    return texto


# ===== IA =====
def interpretar_con_ia(texto):
    prompt = f"""
Eres un sistema que convierte pedidos en JSON.

Menú:
{menu}

Texto del cliente:
"{texto}"

Responde SOLO JSON así:
{{
  "accion": "pedido | menu | cancelar | confirmar | datos | otro",
  "items": [{{"producto":"...", "cantidad":1}}]
}}
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    contenido = resp.choices[0].message.content.strip()

    try:
        return eval(contenido)
    except:
        return {"accion": "otro", "items": []}


# ===== LÓGICA =====
def procesar(numero, texto):

    if numero not in usuarios:
        usuarios[numero] = {
            "pedido": [],
            "estado": "inicio",
            "datos": {}
        }

    user = usuarios[numero]

    ia = interpretar_con_ia(texto)
    accion = ia["accion"]
    items = ia["items"]

    # ===== MENÚ =====
    if accion == "menu":
        enviar_mensaje(numero, mostrar_menu())
        return

    # ===== PEDIDO =====
    if accion == "pedido" and items:
        for item in items:
            user["pedido"].append(item)

        total = 0
        detalle = "🧾 Tu pedido:\n\n"

        for p in user["pedido"]:
            precio = menu[p["producto"]]
            subtotal = precio * p["cantidad"]
            total += subtotal
            detalle += f"{p['cantidad']} x {p['producto']} = ${subtotal}\n"

        detalle += f"\n💰 Total: ${total}"
        detalle += "\n\n¿Deseas agregar algo más o confirmar?"

        user["estado"] = "pedido"
        enviar_mensaje(numero, detalle)
        return

    # ===== CONFIRMAR =====
    if accion == "confirmar":
        user["estado"] = "datos_nombre"
        enviar_mensaje(numero, "👤 ¿A nombre de quién es el pedido?")
        return

    # ===== DATOS =====
    if user["estado"] == "datos_nombre":
        user["datos"]["nombre"] = texto
        user["estado"] = "datos_direccion"
        enviar_mensaje(numero, "📍 Ingresa tu dirección:")
        return

    if user["estado"] == "datos_direccion":
        user["datos"]["direccion"] = texto
        user["estado"] = "datos_telefono"
        enviar_mensaje(numero, "📞 Ingresa tu número:")
        return

    if user["estado"] == "datos_telefono":
        user["datos"]["telefono"] = texto

        resumen = "🚚 NUEVO PEDIDO\n\n"

        total = 0
        for p in user["pedido"]:
            subtotal = menu[p["producto"]] * p["cantidad"]
            total += subtotal
            resumen += f"{p['cantidad']} x {p['producto']}\n"

        resumen += f"\n💰 Total: ${total}"
        resumen += f"\n👤 {user['datos']['nombre']}"
        resumen += f"\n📍 {user['datos']['direccion']}"
        resumen += f"\n📞 {user['datos']['telefono']}"

        # Enviar al cliente
        enviar_mensaje(numero, "✅ Pedido confirmado, en camino 🚀")

        # Enviar al admin (tú)
        enviar_mensaje(ADMIN_PHONE, resumen)

        # Reset
        usuarios[numero] = {"pedido": [], "estado": "inicio", "datos": {}}
        return

    # ===== DEFAULT =====
    enviar_botones(numero, "👋 Bienvenido a Marisco Alegre 🦐")


# ===== WEBHOOK =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = msg["from"]

        if msg["type"] == "text":
            texto = msg["text"]["body"]
        elif msg["type"] == "interactive":
            texto = msg["interactive"]["button_reply"]["id"]
        else:
            return jsonify({"ok": True})

        procesar(numero, texto)

    except:
        pass

    return jsonify({"ok": True})


@app.route("/")
def home():
    return "Bot corriendo 🔥"


if __name__ == "__main__":
    app.run(port=5000)
