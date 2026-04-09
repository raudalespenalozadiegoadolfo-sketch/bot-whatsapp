import os
import requests
from flask import Flask, request

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
ADMIN_PHONE = os.getenv("ADMIN_NUMERO")

# ===== DATA =====
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

# ===== SEND =====
def enviar(numero, data):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def texto(numero, msg):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": msg}
    })

# ===== UI =====
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
                    {"type": "reply", "reply": {"id": "menu", "title": "📋 Menú"}},
                    {"type": "reply", "reply": {"id": "carrito", "title": "🛒 Carrito"}}
                ]
            }
        }
    })

def lista_categorias(numero):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "📂 Categorías"},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Opciones",
                    "rows": [
                        {"id": "mariscos", "title": "🦐 Mariscos"},
                        {"id": "bebidas", "title": "🍺 Bebidas"}
                    ]
                }]
            }
        }
    })

def lista_mariscos(numero):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🦐 Mariscos"},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Productos",
                    "rows": [
                        {"id": "almeja", "title": "Almeja"},
                        {"id": "ostion", "title": "Ostion"},
                        {"id": "ceviche", "title": "Ceviche"},
                        {"id": "volver", "title": "⬅️ Volver"}
                    ]
                }]
            }
        }
    })

def lista_bebidas(numero):
    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🍺 Bebidas"},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Productos",
                    "rows": [
                        {"id": "cerveza", "title": "Cerveza"},
                        {"id": "michelada", "title": "Michelada"},
                        {"id": "refresco", "title": "Refresco"},
                        {"id": "volver", "title": "⬅️ Volver"}
                    ]
                }]
            }
        }
    })

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

def carrito(numero):
    pedido = usuarios[numero]["pedido"]

    if not pedido:
        texto(numero, "🛒 Carrito vacío")
        return

    total = 0
    msg = "🛒 CARRITO:\n\n"

    for item, cant in pedido.items():
        subtotal = cant * menu[item]
        total += subtotal
        msg += f"{cant} x {item} = ${subtotal}\n"

    msg += f"\n💰 Total: ${total}"

    texto(numero, msg)

    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Opciones"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Agregar"}},
                    {"type": "reply", "reply": {"id": "finalizar", "title": "✅ Finalizar"}},
                    {"type": "reply", "reply": {"id": "cancelar", "title": "🗑 Vaciar"}}
                ]
            }
        }
    })

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
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok"

        msg = value["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": {}, "estado": "inicio"}

        user = usuarios[numero]

        # ===== INTERACTIVO =====
        if msg["type"] == "interactive":
            inter = msg["interactive"]

            if inter["type"] == "list_reply":
                opcion = inter["list_reply"]["id"]

                if opcion == "mariscos":
                    lista_mariscos(numero)
                    return "ok"

                if opcion == "bebidas":
                    lista_bebidas(numero)
                    return "ok"

                if opcion == "volver":
                    lista_categorias(numero)
                    return "ok"

                botones_cantidad(numero, opcion)
                return "ok"

            if inter["type"] == "button_reply":
                data_btn = inter["button_reply"]["id"]

                if data_btn == "menu":
                    lista_categorias(numero)
                    return "ok"

                if data_btn == "carrito":
                    carrito(numero)
                    return "ok"

                if data_btn == "seguir":
                    lista_categorias(numero)
                    return "ok"

                if data_btn == "cancelar":
                    usuarios[numero]["pedido"] = {}
                    texto(numero, "🗑 Carrito vacío")
                    return "ok"

                if data_btn == "finalizar":
                    user["estado"] = "nombre"
                    texto(numero, "📝 Nombre:")
                    return "ok"

                if "|" in data_btn:
                    prod, cant = data_btn.split("|")
                    cant = int(cant)

                    user["pedido"][prod] = user["pedido"].get(prod, 0) + cant

                    carrito(numero)
                    return "ok"

        # ===== TEXTO =====
        if msg["type"] == "text":
            texto_user = msg["text"]["body"].lower()

            if texto_user in ["hola", "hi"]:
                botones_inicio(numero)
                return "ok"

        # ===== DATOS =====
        if user["estado"] == "nombre":
            user["nombre"] = msg["text"]["body"]
            user["estado"] = "direccion"
            texto(numero, "📍 Dirección:")
            return "ok"

        if user["estado"] == "direccion":
            user["direccion"] = msg["text"]["body"]
            user["estado"] = "telefono"
            texto(numero, "📞 Teléfono:")
            return "ok"

        if user["estado"] == "telefono":
            user["telefono"] = msg["text"]["body"]

            resumen = "📦 PEDIDO\n\n"
            for i, c in user["pedido"].items():
                resumen += f"{c} x {i}\n"

            resumen += f"\n👤 {user['nombre']}"
            resumen += f"\n📍 {user['direccion']}"
            resumen += f"\n📞 {user['telefono']}"

            texto(numero, "✅ Pedido confirmado")
            texto(ADMIN_PHONE, resumen)

            usuarios[numero] = {"pedido": {}, "estado": "inicio"}
            return "ok"

    except Exception as e:
        print("ERROR:", e)

    return "ok"

if __name__ == "__main__":
    app.run(port=10000)
