from flask import Flask, request
import requests
import os
import unicodedata
import uuid

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

# =========================
# UTILIDADES
# =========================

def limpiar(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')
    return texto

def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

# =========================
# MENÚ
# =========================

menu = {
    "camarones": {
        "A la diabla": 180,
        "Empanizados": 190,
        "Al ajo": 180,
        "Al ajillo": 180
    },
    "filete": {
        "A la diabla": 160,
        "Empanizado": 170,
        "Al ajo": 170
    }
}

usuarios = {}

# =========================
# UI
# =========================

def menu_principal(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "image",
                "image": {
                    # 🔥 CAMBIA ESTA IMAGEN SI QUIERES
                    "link": "https://images.unsplash.com/photo-1559847844-5315695dadae"
                }
            },
            "body": {
                "text": "👋 Bienvenido a Marisco Alegre 🦐\n¿Qué deseas pedir?"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽️ Comida"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    })

def lista(numero, titulo, opciones, tipo):
    rows = []
    for o in opciones:
        rows.append({
            "id": f"{tipo}_{o}",
            "title": o[:24]
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": titulo},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Opciones",
                    "rows": rows
                }]
            }
        }
    })

def mostrar_pedido(numero, u):
    texto = "🧾 Tu pedido:\n"
    total = 0
    resumen = {}

    for item in u["pedido"]:
        nombre = item["nombre"]
        resumen.setdefault(nombre, {"cantidad": 0, "precio": item["precio"]})
        resumen[nombre]["cantidad"] += 1

    for nombre, data in resumen.items():
        subtotal = data["cantidad"] * data["precio"]
        total += subtotal
        texto += f"• {data['cantidad']} {nombre} - ${subtotal}\n"

    texto += f"\n💵 Total: ${total}"

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error"

    data = request.json
    print("DATA:", data)

    # 🔥 SOLUCIÓN ERROR 'messages'
    try:
        if "entry" not in data:
            return "ok"

        cambios = data["entry"][0]["changes"][0]["value"]

        if "messages" not in cambios:
            return "ok"

        msg = cambios["messages"][0]
        numero = msg["from"]

    except:
        return "ok"

    # =========================

    if numero not in usuarios:
        usuarios[numero] = {"pedido": [], "estado": None}

    u = usuarios[numero]

    # TEXTO
    if "text" in msg:
        texto = limpiar(msg["text"]["body"])

        if texto == "hola":
            menu_principal(numero)

        elif texto.isdigit() and isinstance(u["estado"], dict):
            cantidad = int(texto)
            nombre = u["estado"]["nombre"]
            precio = u["estado"]["precio"]

            for _ in range(cantidad):
                u["pedido"].append({
                    "nombre": nombre,
                    "precio": precio
                })

            enviar({
                "messaging_product": "whatsapp",
                "to": numero,
                "text": {"body": f"✅ {cantidad} {nombre} agregado"}
            })

            mostrar_pedido(numero, u)
            u["estado"] = None

    # BOTONES / LISTAS
    if "interactive" in msg:
        inter = msg["interactive"]

        if inter["type"] == "button_reply":
            id = inter["button_reply"]["id"]

            if id == "comida":
                lista(numero, "Selecciona categoría:", list(menu.keys()), "cat")

            elif id == "pedido":
                mostrar_pedido(numero, u)

        elif inter["type"] == "list_reply":
            id = inter["list_reply"]["id"]

            # CATEGORÍA
            if id.startswith("cat_"):
                cat = id.replace("cat_", "")
                lista(numero, cat, list(menu[cat].keys()), "prod")

            # PRODUCTO
            elif id.startswith("prod_"):
                prod = id.replace("prod_", "")

                # 🔥 SOLUCIÓN BUG DUPLICADO
                for cat in menu:
                    if prod in menu[cat]:
                        precio = menu[cat][prod]
                        nombre = f"{cat.capitalize()} {prod}"

                        u["estado"] = {
                            "nombre": nombre,
                            "precio": precio
                        }

                        enviar({
                            "messaging_product": "whatsapp",
                            "to": numero,
                            "text": {
                                "body": f"¿Cuántos {nombre} necesitas?"
                            }
                        })
                        break  # 👈 ESTO ARREGLA EL DOBLE MENSAJE

    return "ok"

# =========================

if __name__ == "__main__":
    app.run()
