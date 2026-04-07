import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
ADMIN_PHONE = os.getenv("ADMIN_NUMERO")

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

# ===== ENVIAR MENSAJE =====
def enviar(numero, data):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def texto(numero, mensaje):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    })

# ===== BOTONES INICIO =====
def botones_inicio(numero):
    enviar(numero, {
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
    })

# ===== LISTA MENU =====
def lista_menu(numero):
    rows = []

    for k, v in menu.items():
        rows.append({
            "id": k,
            "title": f"{k} - ${v}"
        })

    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "📋 Selecciona un producto"},
            "action": {
                "button": "Ver menú",
                "sections": [{
                    "title": "Menú",
                    "rows": rows
                }]
            }
        }
    })

# ===== BOTONES CANTIDAD =====
def botones_cantidad(numero, producto):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"¿Cuántos {producto}?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": f"{producto}|1", "title": "1"}},
                    {"type": "reply", "reply": {"id": f"{producto}|2", "title": "2"}},
                    {"type": "reply", "reply": {"id": f"{producto}|3", "title": "3"}}
                ]
            }
        }
    })

# ===== BOTONES FINAL =====
def botones_final(numero):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Deseas agregar algo más?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Agregar"}},
                    {"type": "reply", "reply": {"id": "finalizar", "title": "✅ Finalizar"}}
                ]
            }
        }
    })

# ===== RESUMEN =====
def resumen(numero):
    pedido = usuarios[numero]["pedido"]
    total = 0

    texto_res = "🧾 Tu pedido:\n\n"

    for item, cant in pedido.items():
        subtotal = cant * menu[item]
        total += subtotal
        texto_res += f"{cant} x {item} = ${subtotal}\n"

    texto_res += f"\n💰 Total: ${total}"

    texto(numero, texto_res)

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

        if numero not in usuarios:
            usuarios[numero] = {"pedido": {}, "estado": "inicio"}

        user = usuarios[numero]

        # ===== INTERACTIVO =====
        if msg["type"] == "interactive":

            inter = msg["interactive"]

            # LISTA
            if inter["type"] == "list_reply":
                producto = inter["list_reply"]["id"]
                botones_cantidad(numero, producto)
                return "ok"

            # BOTONES
            if inter["type"] == "button_reply":
                data_btn = inter["button_reply"]["id"]

                if data_btn == "menu":
                    lista_menu(numero)
                    return "ok"

                if data_btn == "pedir":
                    lista_menu(numero)
                    return "ok"

                if data_btn == "seguir":
                    lista_menu(numero)
                    return "ok"

                if data_btn == "finalizar":
                    user["estado"] = "nombre"
                    texto(numero, "📝 Nombre del pedido:")
                    return "ok"

                # agregar producto
                if "|" in data_btn:
                    producto, cantidad = data_btn.split("|")
                    cantidad = int(cantidad)

                    user["pedido"][producto] = user["pedido"].get(producto, 0) + cantidad

                    resumen(numero)
                    botones_final(numero)
                    return "ok"

        # ===== TEXTO NORMAL =====
        if msg["type"] == "text":
            texto_user = msg["text"]["body"].lower()

            if texto_user in ["hola", "hi", "menu"]:
                botones_inicio(numero)
                return "ok"

        # ===== FLUJO FINAL =====
        if user["estado"] == "nombre":
            user["nombre"] = msg["text"]["body"]
            user["estado"] = "direccion"
            texto(numero, "📍 Dirección:")
            return "ok"

        elif user["estado"] == "direccion":
            user["direccion"] = msg["text"]["body"]
            user["estado"] = "telefono"
            texto(numero, "📞 Teléfono:")
            return "ok"

        elif user["estado"] == "telefono":
            user["telefono"] = msg["text"]["body"]

            pedido = user["pedido"]

            resumen_txt = "📦 PEDIDO FINAL\n\n"
            for i, c in pedido.items():
                resumen_txt += f"{c} x {i}\n"

            resumen_txt += f"\n👤 {user['nombre']}"
            resumen_txt += f"\n📍 {user['direccion']}"
            resumen_txt += f"\n📞 {user['telefono']}"

            texto(numero, "✅ Pedido confirmado")
            texto(ADMIN_PHONE, resumen_txt)

            usuarios[numero] = {"pedido": {}, "estado": "inicio"}
            return "ok"

    except Exception as e:
        print("ERROR:", e)

    return "ok"

if __name__ == "__main__":
    app.run()
