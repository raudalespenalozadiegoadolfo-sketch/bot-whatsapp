import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

carritos = {}

# ===== MENÚ POR CATEGORÍAS =====
menu = {
    "cervezas": {
        "corona extra": 40,
        "corona light": 40,
        "corona cero": 40,
        "tecate": 35,
        "tecate light": 35,
        "indio": 30,
        "ultra": 30,
        "heineken cero": 35
    },
    "micheladas": {
        "camaron": 100,
        "clamato": 80,
        "tamarindo": 90
    },
    "refrescos": {
        "coca cola": 30,
        "coca cola light": 30,
        "pepsi": 25,
        "sangria": 25,
        "7up": 25
    },
    "aguas1": {
        "arroz": 35,
        "jamaica": 35,
        "piña": 35,
        "limon": 35
    },
    "aguas2": {
        "arroz": 20,
        "jamaica": 20,
        "piña": 20,
        "limon": 20
    },
    "camarones": {
        "diabla": 180,
        "empanizados": 190,
        "ajo": 180,
        "ajillo": 180
    },
    "pulpo": {
        "diabla": 220,
        "empanizado": 220,
        "zarandeado": 220
    },
    "filete": {
        "diabla": 160,
        "empanizado": 170,
        "ajo": 170
    },
    "coctel": {
        "camaron": 190,
        "pulpo": 200,
        "callo": 250,
        "mixto": 220
    },
    "ceviche": {
        "pescado": 180,
        "camaron": 200
    },
    "aguachile": {
        "verde": 190,
        "rojo": 190,
        "negro": 190
    },
    "cortes": {
        "arrachera": 220,
        "tbone": 250,
        "ribeye": 270
    }
}

# ===== ENVIAR =====
def enviar(numero, texto):
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

# ===== BOTONES =====
def botones(numero, texto, opciones):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"

    buttons = []
    for id, title in opciones[:3]:
        buttons.append({
            "type": "reply",
            "reply": {"id": id, "title": title}
        })

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {"buttons": buttons}
        }
    }

    requests.post(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }, json=data)

# ===== LISTA =====
def lista(numero, titulo, items):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"

    rows = []
    for key, precio in items.items():
        rows.append({
            "id": f"{titulo}|{key}",
            "title": key.title(),
            "description": f"${precio}"
        })

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": f"📋 {titulo.title()}"},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Selecciona",
                    "rows": rows[:10]
                }]
            }
        }
    }

    requests.post(url, headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }, json=data)

# ===== RESUMEN =====
def resumen(numero):
    carrito = carritos.get(numero, [])
    total = 0
    texto = "🧾 Tu pedido:\n\n"

    for nombre, precio in carrito:
        total += precio
        texto += f"• {nombre} - ${precio}\n"

    texto += f"\n💵 Total: ${total}"
    return texto

# ===== WEBHOOK =====
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        numero = msg["from"]

        if "text" in msg:
            texto = msg["text"]["body"].lower()

        elif "interactive" in msg:
            if "button_reply" in msg["interactive"]:
                texto = msg["interactive"]["button_reply"]["id"]
            else:
                texto = msg["interactive"]["list_reply"]["id"]

        else:
            return "ok", 200

        # ===== FLUJO =====

        if "hola" in texto:
            botones(numero, "👋 Bienvenido a Marisco Alegre 🦐", [
                ("bebidas", "🍹 Bebidas"),
                ("comida", "🍽 Comida"),
                ("pedido", "🧾 Pedido")
            ])

        elif texto == "bebidas":
            botones(numero, "🍹 Bebidas:", [
                ("cervezas", "🍺 Cervezas"),
                ("micheladas", "🍹 Micheladas"),
                ("refrescos", "🥤 Refrescos")
            ])

        elif texto == "comida":
            botones(numero, "🍽 Comida:", [
                ("camarones", "🍤 Camarones"),
                ("pulpo", "🐙 Pulpo"),
                ("filete", "🐟 Filete")
            ])

        elif texto in menu:
            lista(numero, texto, menu[texto])

        elif "|" in texto:
            categoria, producto = texto.split("|")
            precio = menu[categoria][producto]

            if numero not in carritos:
                carritos[numero] = []

            carritos[numero].append((producto, precio))

            enviar(numero, f"✅ {producto} agregado")
            enviar(numero, resumen(numero))

        elif texto == "pedido":
            enviar(numero, resumen(numero))

        elif "finalizar" in texto:
            enviar(numero, resumen(numero))
            enviar(numero, "🙏 Gracias por su preferencia")
            carritos[numero] = []

        elif "gracias" in texto:
            enviar(numero, "🙏 Gracias a usted por su preferencia")

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(port=10000)
