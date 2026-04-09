import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ===== DATA =====
carritos = {}
estado_usuario = {}
datos_usuario = {}

menu = {
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
    "bebidas": {
        "coca cola": 30,
        "pepsi": 25,
        "7 up": 25,
        "manzana": 25,
        "sprite": 30
    }
}

# ===== FUNCIONES =====

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


def botones(numero, texto, opciones):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
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
            "body": {"text": texto},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": op[0],
                            "title": op[1]
                        }
                    } for op in opciones[:3]
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)


def resumen(numero):
    carrito = carritos.get(numero, [])
    if not carrito:
        return "🧾 Tu pedido está vacío"

    texto = "🧾 Tu pedido:\n\n"
    total = 0

    for item in carrito:
        texto += f"• {item['producto']} - ${item['precio']}\n"
        total += item["precio"]

    texto += f"\n💵 Total: ${total}"
    return texto


def agregar(numero, producto, precio):
    if numero not in carritos:
        carritos[numero] = []

    carritos[numero].append({
        "producto": producto,
        "precio": precio
    })


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
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]

        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()
        else:
            texto = mensaje["interactive"]["button_reply"]["id"]

    except:
        return "ok", 200

    # ===== FLUJO DATOS CLIENTE =====

    if estado_usuario.get(numero) == "nombre":
        datos_usuario[numero] = {"nombre": texto}
        estado_usuario[numero] = "direccion"
        enviar(numero, "📍 Escribe tu dirección:")
        return "ok", 200

    elif estado_usuario.get(numero) == "direccion":
        datos_usuario[numero]["direccion"] = texto
        estado_usuario[numero] = "telefono"
        enviar(numero, "📞 Escribe tu teléfono:")
        return "ok", 200

    elif estado_usuario.get(numero) == "telefono":
        datos_usuario[numero]["telefono"] = texto
        estado_usuario[numero] = None

        enviar(numero, "📦 Pedido confirmado:")
        enviar(numero, resumen(numero))

        enviar(numero,
               f"👤 {datos_usuario[numero]['nombre']}\n"
               f"📍 {datos_usuario[numero]['direccion']}\n"
               f"📞 {datos_usuario[numero]['telefono']}"
        )

        enviar(numero, "🙏 Gracias por su preferencia")
        carritos[numero] = []
        return "ok", 200

    # ===== MENÚ PRINCIPAL =====

    if texto in ["hola", "menu", "menú"]:
        botones(numero, "👋 Bienvenido a Marisco Alegre 🦐", [
            ("comida", "🍽 Comida"),
            ("bebidas", "🍹 Bebidas"),
            ("pedido", "🧾 Ver pedido")
        ])

    elif texto == "comida":
        botones(numero, "🍽 Selecciona:", [
            ("camarones", "🍤 Camarones"),
            ("pulpo", "🐙 Pulpo"),
            ("filete", "🐟 Filete")
        ])

    elif texto == "bebidas":
        botones(numero, "🍹 Selecciona:", [
            ("coca cola", "🥤 Coca Cola"),
            ("pepsi", "🥤 Pepsi"),
            ("7 up", "🥤 7 UP")
        ])

    # ===== SUBMENÚ =====

    elif texto in menu:
        opciones = menu[texto]
        lista = [(f"{texto}|{k}", k.title()) for k in opciones]
        botones(numero, f"{texto.title()}:", lista)

    elif "|" in texto:
        categoria, producto = texto.split("|")
        precio = menu[categoria][producto]

        agregar(numero, producto, precio)

        enviar(numero, f"✅ {producto} agregado")
        enviar(numero, resumen(numero))

        botones(numero, "¿Qué deseas hacer?", [
            ("seguir", "➕ Agregar"),
            ("finalizar", "✅ Finalizar"),
            ("vaciar", "🗑 Vaciar")
        ])

    # ===== ACCIONES =====

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
        if not carritos.get(numero):
            enviar(numero, "⚠️ Tu pedido está vacío")
        else:
            estado_usuario[numero] = "nombre"
            enviar(numero, "👤 Escribe tu nombre:")

    elif "gracias" in texto:
        enviar(numero, "🙏 Gracias a usted por su preferencia")

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
