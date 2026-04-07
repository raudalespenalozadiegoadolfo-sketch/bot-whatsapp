import os
import json
import re
import unicodedata
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
ADMIN_PHONE = os.getenv("ADMIN_NUMERO")

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

# ===== UTILIDADES =====
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode("utf-8")
    return texto

def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
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
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "menu", "title": "📋 Ver menú"}},
                    {"type": "reply", "reply": {"id": "pedir", "title": "🛒 Pedir"}}
                ]
            }
        }
    }
    requests.post(url, headers=headers, json=data)

def mostrar_menu(numero):
    texto = "📋 MENÚ:\n\n"
    for item, precio in menu.items():
        texto += f"• {item} - ${precio}\n"
    texto += "\nEjemplo: 2 ceviche camaron y 1 refresco"
    enviar_mensaje(numero, texto)

# ===== IA =====
def interpretar(texto):
    prompt = f"""
Interpreta pedidos de comida.

Menú:
{menu}

Devuelve SOLO JSON válido:

{{
 "accion": "agregar | quitar | ver | finalizar | saludo",
 "items": [{{"producto":"ceviche","cantidad":2}}]
}}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": texto}
        ]
    )

    contenido = response.choices[0].message.content.strip()
    contenido = contenido.replace("json", "").replace("", "").strip()

    try:
        return json.loads(contenido)
    except:
        return {"accion": "error", "items": []}

# ===== PEDIDOS =====
def procesar(numero, data):
    if numero not in usuarios:
        usuarios[numero] = {"pedido": {}, "estado": "inicio"}

    user = usuarios[numero]

    if data["accion"] == "saludo":
        botones(numero)

    elif data["accion"] == "ver":
        mostrar_menu(numero)

    elif data["accion"] == "agregar":
        for item in data["items"]:
            prod = normalizar(item["producto"])
            cant = int(item["cantidad"])

            # buscar coincidencia en menú
            encontrado = None
            for m in menu:
                if prod in m:
                    encontrado = m
                    break

            if not encontrado:
                enviar_mensaje(numero, f"No existe: {prod}")
                continue

            user["pedido"][encontrado] = user["pedido"].get(encontrado, 0) + cant

        resumen(numero)

    elif data["accion"] == "quitar":
        for item in data["items"]:
            prod = normalizar(item["producto"])
            cant = int(item["cantidad"])

            for m in list(user["pedido"]):
                if prod in m:
                    user["pedido"][m] -= cant
                    if user["pedido"][m] <= 0:
                        del user["pedido"][m]

        resumen(numero)

    elif data["accion"] == "finalizar":
        user["estado"] = "nombre"
        enviar_mensaje(numero, "📝 Nombre del pedido:")

# ===== RESUMEN =====
def resumen(numero):
    pedido = usuarios[numero]["pedido"]

    if not pedido:
        enviar_mensaje(numero, "Tu pedido está vacío.")
        return

    texto = "🧾 Tu pedido:\n\n"
    total = 0

    for item, cant in pedido.items():
        subtotal = cant * menu[item]
        total += subtotal
        texto += f"{cant} x {item} = ${subtotal}\n"

    texto += f"\n💰 Total: ${total}"
    texto += "\n\n¿Deseas agregar algo, quitar o finalizar?"

    enviar_mensaje(numero, texto)

# ===== WEBHOOK =====
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error"

@app.route("/webhook", methods=["POST"])
def recibir():
    data = request.get_json()

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        if "messages" not in entry:
            return "ok"

        msg = entry["messages"][0]
        numero = msg["from"]

        if msg["type"] == "interactive":
            texto = msg["interactive"]["button_reply"]["id"]

        else:
            texto = msg["text"]["body"]

        texto = normalizar(texto)

        user = usuarios.get(numero, {"estado": "inicio"})

        # flujo de datos
        if user["estado"] == "nombre":
            user["nombre"] = texto
            user["estado"] = "direccion"
            enviar_mensaje(numero, "📍 Dirección:")
            return "ok"

        elif user["estado"] == "direccion":
            user["direccion"] = texto
            user["estado"] = "telefono"
            enviar_mensaje(numero, "📞 Teléfono:")
            return "ok"

        elif user["estado"] == "telefono":
            user["telefono"] = texto
            user["estado"] = "confirmar"

            pedido = user["pedido"]
            texto_final = "📦 PEDIDO FINAL\n\n"

            for i, c in pedido.items():
                texto_final += f"{c} x {i}\n"

            texto_final += f"\n👤 {user['nombre']}"
            texto_final += f"\n📍 {user['direccion']}"
            texto_final += f"\n📞 {user['telefono']}"

            enviar_mensaje(numero, "✅ Pedido confirmado")
            enviar_mensaje(ADMIN_PHONE, texto_final)

            usuarios[numero] = {"pedido": {}, "estado": "inicio"}
            return "ok"

        # IA
        data_ia = interpretar(texto)
        procesar(numero, data_ia)

    except Exception as e:
        print("ERROR:", e)

    return "ok"

if __name__ == "__main__":
    app.run()
