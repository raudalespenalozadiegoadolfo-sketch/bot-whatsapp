import os
import re
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("TOKEN_WHATSAPP")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
ADMIN_PHONE = os.getenv("ADMIN_PHONE")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===== MEMORIA =====
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

# ===== UTIL =====
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


def enviar_botones(numero):
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
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu", "title": "📋 Ver menú"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🛒 Pedir"}}
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)


def mostrar_menu():
    texto = "📋 MENÚ:\n\n"
    for k, v in menu.items():
        texto += f"• {k} - ${v}\n"
    texto += "\nEjemplo: 2 ceviche camaron y 1 refresco"
    return texto


# ===== NORMALIZAR TEXTO =====
def normalizar(texto):
    texto = texto.lower()

    reemplazos = {
        "almejas": "almeja",
        "ostiones": "ostion",
        "refrescos": "refresco",
        "cervezas": "cerveza",
        "micheladas": "michelada",
        "camarones": "camaron",
        "ceviche de camaron": "ceviche camaron",
        "ceviche de camarón": "ceviche camaron",
    }

    for k, v in reemplazos.items():
        texto = texto.replace(k, v)

    return texto


# ===== IA =====
def interpretar(texto):
    texto = normalizar(texto)

    prompt = f"""
Convierte pedidos a JSON.

Menu:
{menu}

Texto:
"{texto}"

Responde SOLO JSON:
{{
"accion":"pedido|menu|confirmar|otro",
"items":[{{"producto":"...", "cantidad":1}}]
}}
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        contenido = resp.choices[0].message.content.strip()
        return eval(contenido)

    except:
        return {"accion": "otro", "items": []}


# ===== LÓGICA =====
def procesar(numero, texto):

    print("MENSAJE:", texto)

    if numero not in usuarios:
        usuarios[numero] = {
            "pedido": [],
            "estado": "inicio",
            "datos": {}
        }

    user = usuarios[numero]
    ia = interpretar(texto)

    accion = ia["accion"]
    items = ia["items"]

    # ===== MENU =====
    if accion == "menu" or texto in ["menu", "menú", "ver menu"]:
        enviar_mensaje(numero, mostrar_menu())
        return

    # ===== PEDIDO =====
    if accion == "pedido" and items:
        for item in items:
            user["pedido"].append(item)

        total = 0
        detalle = "🧾 Tu pedido:\n\n"

        for p in user["pedido"]:
            subtotal = menu[p["producto"]] * p["cantidad"]
            total += subtotal
            detalle += f"{p['cantidad']} x {p['producto']} = ${subtotal}\n"

        detalle += f"\n💰 Total: ${total}"
        detalle += "\n\nEscribe confirmar o agrega más productos"

        user["estado"] = "pedido"

        enviar_mensaje(numero, detalle)
        return

    # ===== CONFIRMAR =====
    if "confirmar" in texto:
        user["estado"] = "nombre"
        enviar_mensaje(numero, "👤 Nombre del pedido:")
        return

    # ===== DATOS =====
    if user["estado"] == "nombre":
        user["datos"]["nombre"] = texto
        user["estado"] = "direccion"
        enviar_mensaje(numero, "📍 Dirección:")
        return

    if user["estado"] == "direccion":
        user["datos"]["direccion"] = texto
        user["estado"] = "telefono"
        enviar_mensaje(numero, "📞 Teléfono:")
        return

    if user["estado"] == "telefono":
        user["datos"]["telefono"] = texto

        resumen = "🚚 PEDIDO NUEVO\n\n"
        total = 0

        for p in user["pedido"]:
            subtotal = menu[p["producto"]] * p["cantidad"]
            total += subtotal
            resumen += f"{p['cantidad']} x {p['producto']}\n"

        resumen += f"\n💰 Total: ${total}"
        resumen += f"\n👤 {user['datos']['nombre']}"
        resumen += f"\n📍 {user['datos']['direccion']}"
        resumen += f"\n📞 {user['datos']['telefono']}"

        enviar_mensaje(numero, "✅ Pedido confirmado 🚀")
        enviar_mensaje(ADMIN_PHONE, resumen)

        usuarios[numero] = {"pedido": [], "estado": "inicio", "datos": {}}
        return

    # ===== DEFAULT =====
    enviar_botones(numero)


# ===== WEBHOOK (CORREGIDO) =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return jsonify({"ok": True})

        msg = value["messages"][0]
        numero = msg["from"]

        if msg["type"] == "text":
            texto = msg["text"]["body"]

        elif msg["type"] == "interactive":
            texto = msg["interactive"]["button_reply"]["id"]

        else:
            return jsonify({"ok": True})

        procesar(numero, texto)

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"ok": True})


@app.route("/")
def home():
    return "Bot activo 🔥"


if __name__ == "__main__":
    app.run(port=5000)
