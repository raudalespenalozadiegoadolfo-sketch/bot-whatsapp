import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

carritos = {}
temp_producto = {}

# ===== MENÚ COMPLETO =====

menu = {
    "comida": {

        "camarones": {
            "a la diabla": 180,
            "empanizados": 190,
            "al ajo": 180,
            "al ajillo": 180
        },

        "pulpo": {
            "a la diabla": 220,
            "empanizado": 220,
            "zarandeado": 220
        },

        "filete": {
            "a la diabla": 160,
            "empanizado": 170,
            "al ajo": 170
        },

        "coctel": {
            "camaron": 190,
            "pulpo": 200,
            "callo": 250,
            "mixto": 220
        },

        # 🔥 NUEVO
        "ceviches": {
            "pescado": 180,
            "camaron": 200
        },

        "aguachiles": {
            "verde": 190,
            "negro": 190,
            "rojo": 190
        },

        "cortes finos": {
            "arrachera": 220,
            "t-bone": 250,
            "rib eye": 270
        }
    },

    "bebidas": {

        "cervezas": {
            "corona extra": 40,
            "corona light": 40,
            "heineken cero": 40,
            "tecate": 35,
            "tecate light": 35,
            "sol clamato": 30,
            "indio": 35,
            "ultra": 40,
            "pacifico": 40
        },

        "refrescos": {
            "coca cola": 30,
            "pepsi": 25,
            "7 up": 25,
            "manzana": 25,
            "sprite": 30,
            "coca light": 30
        },

        "aguas 1lt": {
            "arroz": 30,
            "jamaica": 30,
            "piña": 30,
            "limon": 30,
            "naranja": 30
        },

        "aguas 1/2lt": {
            "arroz": 15,
            "jamaica": 15,
            "piña": 15,
            "limon": 15,
            "naranja": 15
        },

        "micheladas": {
            "camaron": 100,
            "clamato": 80,
            "tamarindo": 90
        },

        "preparadas": {
            "piñada": 80,
            "piña colada": 100,
            "mojito": 80,
            "clerico": 90,
            "margarita": 100,
            "paloma": 85,
            "rusa": 75
        }
    }
}

# ===== FUNCIONES =====

def enviar(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }

    requests.post(url, headers=headers, json=data)


def botones(numero, texto, opciones):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": op[0], "title": op[1]}}
                    for op in opciones[:3]
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)


def lista(numero, texto, opciones):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": texto},
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Menú",
                    "rows": [{"id": op[0], "title": op[1]} for op in opciones]
                }]
            }
        }
    }

    requests.post(url, headers=headers, json=data)


def agregar(numero, producto, precio, cantidad):
    if numero not in carritos:
        carritos[numero] = []

    for _ in range(int(cantidad)):
        carritos[numero].append({"producto": producto, "precio": precio})


def resumen(numero):
    carrito = carritos.get(numero, [])
    total = sum(i["precio"] for i in carrito)

    texto = "🧾 Tu pedido:\n\n"
    for item in carrito:
        texto += f"• {item['producto']} - ${item['precio']}\n"

    texto += f"\n💵 Total: ${total}"
    return texto


# ===== WEBHOOK =====

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error", 403


@app.route("/webhook", methods=["POST"])
def recibir():
    data = request.json

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = msg["from"]

        if "text" in msg:
            texto = msg["text"]["body"].lower()
        else:
            texto = msg["interactive"].get("list_reply", {}).get("id") or \
                    msg["interactive"].get("button_reply", {}).get("id")

    except:
        return "ok", 200

    # ===== MENÚ PRINCIPAL =====
    if texto in ["hola", "menu"]:
        botones(numero, "👋 Bienvenido 🦐", [
            ("comida", "🍽 Comida"),
            ("bebidas", "🍹 Bebidas"),
            ("pedido", "🧾 Pedido")
        ])

    # ===== COMIDA =====
    elif texto == "comida":
        lista(numero, "🍽 Comida:", [
            ("camarones", "🍤 Camarones"),
            ("pulpo", "🐙 Pulpo"),
            ("filete", "🐟 Filete"),
            ("coctel", "🥣 Cóctel"),
            ("ceviches", "🥗 Ceviches"),
            ("aguachiles", "🌶 Aguachiles"),
            ("cortes finos", "🥩 Cortes Finos")
        ])

    # ===== BEBIDAS =====
    elif texto == "bebidas":
        lista(numero, "🍹 Bebidas:", [
            ("cervezas", "🍺 Cervezas"),
            ("refrescos", "🥤 Refrescos"),
            ("aguas 1lt", "🧃 Aguas 1L"),
            ("aguas 1/2lt", "🧃 Aguas 1/2L"),
            ("micheladas", "🍹 Micheladas"),
            ("preparadas", "🍸 Preparadas")
        ])

    # ===== SUBMENÚ DINÁMICO =====
    else:
        for categoria in menu:
            if texto in menu[categoria]:
                opciones = [
                    (f"{texto}|{p}", f"{p.title()} ${menu[categoria][texto][p]}")
                    for p in menu[categoria][texto]
                ]
                lista(numero, texto.title(), opciones)
                return "ok", 200

    # ===== PRODUCTO =====
    if "|" in texto:
        cat, prod = texto.split("|")

        for c in menu:
            if cat in menu[c]:
                precio = menu[c][cat][prod]

        temp_producto[numero] = (prod, precio)

        botones(numero, f"¿Cuántos {prod}?", [
            ("1", "1️⃣"),
            ("2", "2️⃣"),
            ("3", "3️⃣")
        ])

    elif texto in ["1", "2", "3"]:
        prod, precio = temp_producto[numero]
        agregar(numero, prod, precio, texto)

        enviar(numero, f"✅ {texto} {prod} agregado")
        enviar(numero, resumen(numero))

        botones(numero, "¿Qué deseas hacer?", [
            ("seguir", "➕ Seguir"),
            ("finalizar", "✅ Finalizar"),
            ("vaciar", "🗑 Vaciar")
        ])

    elif texto == "pedido":
        enviar(numero, resumen(numero))

    elif texto == "vaciar":
        carritos[numero] = []
        enviar(numero, "🗑 Pedido vaciado")

    elif texto == "seguir":
        botones(numero, "Menú:", [
            ("comida", "🍽 Comida"),
            ("bebidas", "🍹 Bebidas"),
            ("pedido", "🧾 Pedido")
        ])

    elif texto == "finalizar":
        enviar(numero, "🙏 Gracias por su preferencia")

    elif "gracias" in texto:
        enviar(numero, "🙏 Gracias a usted por su preferencia")

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
