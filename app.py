import os
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

# ===== MENÚ =====
menu = {
    "corona extra": 40,
    "corona light": 40,
    "heineken cero": 40,
    "tecate": 35,
    "tecate light": 35,
    "sol clamato": 30,
    "indio": 35,
    "ultra": 40,
    "pacifico": 40,

    "michelada camaron": 100,
    "michelada clamato": 80,
    "michelada tamarindo": 90,

    "coca cola": 30,
    "pepsi": 25,
    "7up": 25,
    "manzana": 25,
    "sprite": 30,
    "coca light": 30,

    "agua arroz": 30,
    "agua jamaica": 30,
    "agua piña": 30,
    "agua limon": 30,
    "agua naranja": 30,

    "agua arroz 1/2": 15,
    "agua jamaica 1/2": 15,
    "agua piña 1/2": 15,
    "agua limon 1/2": 15,
    "agua naranja 1/2": 15,

    "piñada": 80,
    "piña colada": 100,
    "mojito": 80,
    "clerico": 90,
    "margarita": 100,
    "paloma": 85,
    "rusa": 75
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
def inicio(numero):
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

# ===== LISTAS =====
def lista(numero, titulo, items):
    rows = [{"id": k, "title": f"{k} - ${v}"} for k, v in items]
    rows.append({"id": "volver", "title": "⬅️ Volver"})

    enviar(numero, {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": titulo},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Opciones",
                    "rows": rows[:10]
                }]
            }
        }
    })

# ===== MENÚ =====
def categorias(numero):
    lista(numero, "📂 Categorías", [("bebidas", "")])

def bebidas(numero):
    lista(numero, "🍹 Bebidas", [
        ("cervezas", ""),
        ("micheladas", ""),
        ("refrescos", ""),
        ("aguas1", ""),
        ("aguas05", ""),
        ("preparadas", "")
    ])

def cervezas(numero):
    lista(numero, "🍺 Cervezas", [(k, v) for k, v in menu.items() if k in [
        "corona extra","corona light","heineken cero","tecate","tecate light","sol clamato","indio","ultra","pacifico"
    ]])

def micheladas(numero):
    lista(numero, "🍹 Micheladas", [(k, v) for k, v in menu.items() if "michelada" in k])

def refrescos(numero):
    lista(numero, "🥤 Refrescos", [(k, v) for k, v in menu.items() if k in [
        "coca cola","pepsi","7up","manzana","sprite","coca light"
    ]])

def aguas1(numero):
    lista(numero, "🧃 Aguas 1L", [(k, v) for k, v in menu.items() if "agua" in k and "1/2" not in k])

def aguas05(numero):
    lista(numero, "🧃 Aguas 1/2L", [(k, v) for k, v in menu.items() if "1/2" in k])

def preparadas(numero):
    lista(numero, "🍸 Preparadas", [(k, v) for k, v in menu.items() if k in [
        "piñada","piña colada","mojito","clerico","margarita","paloma","rusa"
    ]])

# ===== CANTIDAD =====
def cantidad(numero, producto):
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

# ===== CARRITO =====
def carrito(numero):
    pedido = usuarios[numero]["pedido"]

    if not pedido:
        texto(numero, "🛒 Carrito vacío")
        return

    total = 0
    msg = "🛒 CARRITO:\n\n"

    for p, c in pedido.items():
        subtotal = menu[p] * c
        total += subtotal
        msg += f"{c} x {p} = ${subtotal}\n"

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
                    {"type": "reply", "reply": {"id": "vaciar", "title": "🗑 Vaciar"}}
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

        # ===== INTERACTIVE =====
        if msg["type"] == "interactive":
            inter = msg["interactive"]

            if inter["type"] == "list_reply":
                op = inter["list_reply"]["id"]

                if op == "bebidas": bebidas(numero)
                elif op == "cervezas": cervezas(numero)
                elif op == "micheladas": micheladas(numero)
                elif op == "refrescos": refrescos(numero)
                elif op == "aguas1": aguas1(numero)
                elif op == "aguas05": aguas05(numero)
                elif op == "preparadas": preparadas(numero)
                elif op == "volver": bebidas(numero)
                else: cantidad(numero, op)

                return "ok"

            if inter["type"] == "button_reply":
                btn = inter["button_reply"]["id"]

                if btn == "menu": categorias(numero)
                elif btn == "carrito": carrito(numero)
                elif btn == "seguir": categorias(numero)
                elif btn == "vaciar":
                    user["pedido"] = {}
                    texto(numero, "🗑 Carrito vacío")

                elif btn == "finalizar":
                    user["estado"] = "nombre"
                    texto(numero, "📝 Nombre:")

                elif "|" in btn:
                    p, c = btn.split("|")
                    user["pedido"][p] = user["pedido"].get(p, 0) + int(c)
                    carrito(numero)

                return "ok"

        # ===== TEXTO =====
        if msg["type"] == "text":
            txt = msg["text"]["body"].lower()

            if txt in ["hola", "menu"]:
                inicio(numero)
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
            for p, c in user["pedido"].items():
                resumen += f"{c} x {p}\n"

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
