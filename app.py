from flask import Flask, request
import requests
import os
import uuid

app = Flask(__name__)

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

LOGO_URL = "https://i.ibb.co/MxLwfTvY/Whats-App-Image-2026-04-09-at-6-29-58-PM.jpg"

usuarios = {}

# =========================
# MENÚ
# =========================
menu = {
    "camarones": {
        "Camarones a la Diabla": 180,
        "Camarones Empanizados": 190,
        "Camarones al Ajo": 180,
        "Camarones al Ajillo": 180
    },
    "pulpo": {
        "Pulpo a la Diabla": 220,
        "Pulpo Empanizado": 220,
        "Pulpo Zarandeado": 220
    },
    "filete": {
        "Filete a la Diabla": 160,
        "Filete Empanizado": 170,
        "Filete al Ajo": 170
    },
    "cortes": {
        "Arrachera": 220,
        "T-Bone": 250,
        "Rib Eye": 270
    },

    # 🔥 BEBIDAS CON SUBMENÚ
    "bebidas": {
        "refrescos": {
            "Coca Cola 600ml": 30,
            "Coca Cola Light 600ml": 30,
            "Pepsi 600ml": 25,
            "Sangría 600ml": 25,
            "7UP 600ml": 25
        },
        "aguas1L": {
            "Agua Horchata 1L": 35,
            "Agua Jamaica 1L": 35,
            "Agua Piña 1L": 35,
            "Agua Limón 1L": 35
        },
        "aguas500": {
            "Agua Horchata 500ml": 20,
            "Agua Jamaica 500ml": 20,
            "Agua Piña 500ml": 20,
            "Agua Limón 500ml": 20
        },
        "micheladas": {
            "Michelada Camarón 1L": 100,
            "Michelada Clamato 1L": 80,
            "Michelada Tamarindo 1L": 90
        },
        "cervezas": {
            "Corona Extra": 40,
            "Corona Light": 40,
            "Corona Cero": 40,
            "Tecate": 35,
            "Tecate Light": 35,
            "Indio": 30,
            "Ultra": 30,
            "Heineken 0.0": 35
        }
    }
}

# =========================
# ENVIAR
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

# =========================
# MENÚ PRINCIPAL
# =========================
def menu_principal(numero, logo=True):

    if logo:
        enviar({
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "image",
            "image": {"link": LOGO_URL}
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐\n\n¿Qué deseas pedir?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽️ Comida"}},
                    {"type": "reply", "reply": {"id": "bebidas", "title": "🍹 Bebidas"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    })

# =========================
# MENÚ SEGUIR
# =========================
def menu_seguir(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas añadir?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽️ Comida"}},
                    {"type": "reply", "reply": {"id": "bebidas", "title": "🍹 Bebidas"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    })

# =========================
# CATEGORÍAS
# =========================
def mostrar_categorias(numero):
    rows = []

    for cat in menu:
        if cat != "bebidas":
            rows.append({"id": cat, "title": cat.capitalize()})

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona categoría"},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Menú", "rows": rows}]
            }
        }
    })

# =========================
# SUBCATEGORÍAS BEBIDAS
# =========================
def mostrar_subcategorias_bebidas(numero):
    nombres = {
        "refrescos": "🥤 Refrescos",
        "aguas1L": "💧 Aguas 1L",
        "aguas500": "💧 Aguas 500ml",
        "micheladas": "🍺 Micheladas",
        "cervezas": "🍻 Cervezas"
    }

    rows = []

    for key in menu["bebidas"]:
        rows.append({
            "id": f"beb_{key}",
            "title": nombres[key]
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona tu bebida 🍹"},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Bebidas", "rows": rows}]
            }
        }
    })

# =========================
# PRODUCTOS
# =========================
def mostrar_productos(numero, categoria):
    items = menu[categoria]
    rows = []

    for nombre, precio in items.items():
        rows.append({
            "id": f"prod_{nombre}",
            "title": nombre[:24],
            "description": f"${precio}"
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": categoria.upper()},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Productos", "rows": rows}]
            }
        }
    })

# =========================
# PRODUCTOS BEBIDAS
# =========================
def mostrar_productos_bebidas(numero, sub):
    items = menu["bebidas"][sub]
    rows = []

    for nombre, precio in items.items():
        rows.append({
            "id": f"prod_{nombre}",
            "title": nombre[:24],
            "description": f"${precio}"
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": sub.upper()},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Bebidas", "rows": rows}]
            }
        }
    })

# =========================
# PEDIDO
# =========================
def mostrar_pedido(numero, u):
    if not u["pedido"]:
        texto = "🧾 Tu pedido está vacío"
    else:
        texto = "🧾 Tu pedido:\n\n"
        total = 0

        for item in u["pedido"]:
            subtotal = item["cantidad"] * item["precio"]
            texto += f"• {item['cantidad']} {item['nombre']} - ${subtotal}\n"
            total += subtotal

        texto += f"\n💰 Total: ${total}"

    enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": texto}})
    acciones(numero)

# =========================
# BOTONES
# =========================
def acciones(numero):
    enviar({
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
    })

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": [], "bienvenida": False}

        u = usuarios[numero]

        # TEXTO
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

            if texto in ["hola", "menu", "inicio"]:
                if not u["bienvenida"]:
                    menu_principal(numero, True)
                    u["bienvenida"] = True
                else:
                    menu_seguir(numero)
                return "ok", 200

            if u.get("esperando_cantidad"):
                cantidad = int(texto)

                nombre = u["producto"]["nombre"]
                precio = u["producto"]["precio"]

                u["pedido"].append({
                    "nombre": nombre,
                    "precio": precio,
                    "cantidad": cantidad
                })

                u["esperando_cantidad"] = False

                enviar({
                    "messaging_product": "whatsapp",
                    "to": numero,
                    "text": {"body": f"✅ {cantidad} {nombre} agregado"}
                })

                mostrar_pedido(numero, u)
                return "ok", 200

        # INTERACTIVOS
        if "interactive" in mensaje:
            inter = mensaje["interactive"]

            if inter["type"] == "button_reply":
                id = inter["button_reply"]["id"]

                if id == "comida":
                    mostrar_categorias(numero)

                elif id == "bebidas":
                    mostrar_subcategorias_bebidas(numero)

                elif id == "pedido":
                    mostrar_pedido(numero, u)
                    menu_seguir(numero)

                elif id == "seguir":
                    menu_seguir(numero)

                elif id == "vaciar":
                    u["pedido"] = []
                    enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "🗑️ Carrito vacío"}})
                    menu_seguir(numero)

            elif inter["type"] == "list_reply":
                id = inter["list_reply"]["id"]

                if id in menu:
                    mostrar_productos(numero, id)

                elif id.startswith("beb_"):
                    sub = id.replace("beb_", "")
                    mostrar_productos_bebidas(numero, sub)

                elif id.startswith("prod_"):
                    nombre = id.replace("prod_", "")

                    for cat in menu:
                        if cat == "bebidas":
                            for sub in menu["bebidas"]:
                                if nombre in menu["bebidas"][sub]:
                                    precio = menu["bebidas"][sub][nombre]
                        else:
                            if nombre in menu[cat]:
                                precio = menu[cat][nombre]

                    u["producto"] = {"nombre": nombre, "precio": precio}
                    u["esperando_cantidad"] = True

                    enviar({
                        "messaging_product": "whatsapp",
                        "to": numero,
                        "text": {"body": f"¿Cuántos {nombre} necesitas?"}
                    })

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000)
