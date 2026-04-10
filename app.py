from flask import Flask, request
import requests
import os
import unicodedata

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
# MENÚ COMPLETO
# =========================

menu = {
    "comida": {
        "Camarones": {
            "Camarones a la diabla": 180,
            "Camarones empanizados": 190,
            "Camarones al ajo": 180,
            "Camarones al ajillo": 180
        },
        "Pulpo": {
            "Pulpo a la diabla": 220,
            "Pulpo empanizado": 220,
            "Pulpo zarandeado": 220
        },
        "Filete": {
            "Filete a la diabla": 160,
            "Filete empanizado": 170,
            "Filete al ajo": 170
        },
        "Cortes Finos": {
            "Arrachera": 220,
            "T-Bone": 250,
            "Rib Eye": 270
        },
        "Ceviches": {
            "Ceviche pescado": 180,
            "Ceviche camaron": 200
        },
        "Aguachiles": {
            "Aguachile verde": 190,
            "Aguachile rojo": 190,
            "Aguachile negro": 190
        }
    },
    "bebidas": {
        "Cervezas": {
            "Corona Extra": 40,
            "Corona Light": 40,
            "Heineken Cero": 40,
            "Tecate": 35,
            "Tecate Light": 35,
            "Sol Clamato": 30,
            "Indio": 35,
            "Ultra": 40,
            "Pacifico": 40
        },
        "Micheladas": {
            "Michelada Camaron": 100,
            "Michelada Clamato": 80,
            "Michelada Tamarindo": 90
        },
        "Refrescos": {
            "Coca Cola": 30,
            "Pepsi": 25,
            "7UP": 25,
            "Manzana": 25,
            "Sprite": 30,
            "Coca Light": 30
        },
        "Aguas 1L": {
            "Agua arroz 1L": 30,
            "Agua jamaica 1L": 30,
            "Agua piña 1L": 30,
            "Agua limon 1L": 30,
            "Agua naranja 1L": 30
        },
        "Aguas 1/2L": {
            "Agua arroz 1/2L": 15,
            "Agua jamaica 1/2L": 15,
            "Agua piña 1/2L": 15,
            "Agua limon 1/2L": 15,
            "Agua naranja 1/2L": 15
        }
    }
}

usuarios = {}

# =========================
# INTERFACES
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
                    "link": "https://i.ibb.co/MxLwfTvY/Whats-App-Image-2026-04-09-at-6-29-58-PM.jpg"
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
                    "title": "Menú",
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

    try:
        cambios = data["entry"][0]["changes"][0]["value"]

        if "messages" not in cambios:
            return "ok"

        msg = cambios["messages"][0]
        numero = msg["from"]

    except:
        return "ok"

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

            for _ in range(cantidad):
                u["pedido"].append(u["estado"])

            enviar({
                "messaging_product": "whatsapp",
                "to": numero,
                "text": {"body": f"✅ {cantidad} {u['estado']['nombre']} agregado"}
            })

            mostrar_pedido(numero, u)
            u["estado"] = None

    # INTERACTIVO
    if "interactive" in msg:
        inter = msg["interactive"]

        if inter["type"] == "button_reply":
            id = inter["button_reply"]["id"]

            if id in ["comida", "bebidas"]:
                lista(numero, "Selecciona categoría:", menu[id].keys(), id)

            elif id == "pedido":
                mostrar_pedido(numero, u)

        elif inter["type"] == "list_reply":
            id = inter["list_reply"]["id"]
            tipo, nombre = id.split("_", 1)

            if tipo in ["comida", "bebidas"]:
                lista(numero, nombre, menu[tipo][nombre].keys(), f"prod|{tipo}|{nombre}")

            elif tipo.startswith("prod|"):
                _, cat, sub = tipo.split("|")

                precio = menu[cat][sub][nombre]

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

    return "ok"

if __name__ == "__main__":
    app.run()
