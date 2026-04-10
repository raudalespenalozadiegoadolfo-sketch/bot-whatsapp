from flask import Flask, request, jsonify
import requests
import os
import unicodedata
import uuid

app = Flask(__name__)

TOKEN = "TU_TOKEN"
PHONE_ID = "TU_PHONE_ID"
VERIFY_TOKEN = "123456"

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
# MENÚ COMPLETO
# =========================

menu = {
    "camarones": {
        "A la diabla": 180,
        "Empanizados": 190,
        "Al ajo": 180,
        "Al ajillo": 180
    },
    "pulpo": {
        "A la diabla": 220,
        "Empanizado": 220,
        "Zarandeado": 220
    },
    "filete": {
        "A la diabla": 160,
        "Empanizado": 170,
        "Al ajo": 170
    },
    "cortes finos": {
        "Arrachera": 220,
        "T-Bone": 250,
        "Rib Eye": 270
    },
    "ceviche": {
        "Pescado": 180,
        "Camarón": 200
    },
    "aguachile": {
        "Verde": 190,
        "Rojo": 190,
        "Negro": 190
    }
}

bebidas = {
    "cervezas": {
        "Corona extra": 40,
        "Corona light": 40,
        "Heineken cero": 40,
        "Tecate": 35,
        "Tecate light": 35,
        "Indio": 35,
        "Ultra": 40,
        "Pacífico": 40
    },
    "refrescos": {
        "Coca Cola": 30,
        "Pepsi": 25,
        "7UP": 25,
        "Manzana": 25,
        "Sprite": 30
    }
}

usuarios = {}

# =========================
# MENSAJES UI
# =========================

def menu_principal(numero):
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {
                "type": "image",
                "image": {
                    "link": "https://i.imgur.com/6Xb6K5K.jpg"
                }
            },
            "body": {
                "text": "👋 Bienvenido a Marisco Alegre 🦐\n¿Qué deseas pedir?"
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽️ Comida"}},
                    {"type": "reply", "reply": {"id": "bebidas", "title": "🍹 Bebidas"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    }
    enviar(data)

def lista(numero, titulo, opciones, tipo):
    rows = []
    for o in opciones:
        rows.append({
            "id": f"{tipo}_{o}",
            "title": o[:24]
        })

    data = {
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
    }
    enviar(data)

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

    acciones(numero)

def acciones(numero):
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas hacer?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Seguir"}},
                    {"type": "reply", "reply": {"id": "finalizar", "title": "✅ Finalizar"}},
                    {"type": "reply", "reply": {"id": "vaciar", "title": "🗑️ Vaciar"}}
                ]
            }
        }
    }
    enviar(data)

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error"

    data = request.json

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": [], "estado": None}

        u = usuarios[numero]

        # TEXTO
        if "text" in msg:
            texto = limpiar(msg["text"]["body"])

            if texto == "hola":
                menu_principal(numero)

            elif texto.isdigit() and u["estado"]:
                cantidad = int(texto)
                nombre = u["estado"]["nombre"]
                precio = u["estado"]["precio"]

                for _ in range(cantidad):
                    u["pedido"].append({"nombre": nombre, "precio": precio})

                enviar({
                    "messaging_product": "whatsapp",
                    "to": numero,
                    "text": {"body": f"✅ {cantidad} {nombre} agregado"}
                })

                mostrar_pedido(numero, u)
                u["estado"] = None

        # BOTONES
        if "interactive" in msg:
            btn = msg["interactive"]

            if btn["type"] == "button_reply":
                id = btn["button_reply"]["id"]

                if id == "comida":
                    lista(numero, "🍽️ Selecciona categoría:", list(menu.keys()), "cat")

                elif id == "bebidas":
                    lista(numero, "🍹 Selecciona bebida:", list(bebidas.keys()), "beb")

                elif id == "pedido":
                    mostrar_pedido(numero, u)

                elif id == "seguir":
                    menu_principal(numero)

                elif id == "vaciar":
                    u["pedido"] = []
                    enviar({
                        "messaging_product": "whatsapp",
                        "to": numero,
                        "text": {"body": "🗑️ Pedido vaciado"}
                    })

                elif id == "finalizar":
                    u["estado"] = "nombre"
                    enviar({
                        "messaging_product": "whatsapp",
                        "to": numero,
                        "text": {"body": "👤 Nombre:"}
                    })

            elif btn["type"] == "list_reply":
                id = btn["list_reply"]["id"]

                if id.startswith("cat_"):
                    cat = id.replace("cat_", "")
                    lista(numero, cat, list(menu[cat].keys()), "prod")

                elif id.startswith("prod_"):
                    prod = id.replace("prod_", "")

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

    except Exception as e:
        print("ERROR:", e)

    return "ok"

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run()
