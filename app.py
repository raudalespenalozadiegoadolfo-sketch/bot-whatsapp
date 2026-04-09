import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

carritos = {}
estado_usuario = {}
temp_producto = {}
datos_cliente = {}

# ===== MENÚ =====
menu = {
    "comida": {
        "aguachiles": {
            "verde": 190,
            "negro": 190,
            "rojo": 190
        },
        "ceviches": {
            "pescado": 180,
            "camaron": 200
        },
        "cortes finos": {
            "arrachera": 220,
            "t-bone": 250,
            "rib eye": 270
        }
    },
    "bebidas": {
        "refrescos": {
            "coca cola": 30,
            "pepsi": 25,
            "7 up": 25
        }
    }
}

# ===== ENVIAR =====
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
                    for op in opciones
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


# ===== CARRITO AGRUPADO =====
def agregar(numero, producto, precio, cantidad):
    if numero not in carritos:
        carritos[numero] = {}

    if producto in carritos[numero]:
        carritos[numero][producto]["cantidad"] += cantidad
    else:
        carritos[numero][producto] = {
            "precio": precio,
            "cantidad": cantidad
        }


def resumen(numero):
    carrito = carritos.get(numero, {})
    total = 0

    texto = "🧾 Tu pedido:\n\n"

    for producto, data in carrito.items():
        subtotal = data["precio"] * data["cantidad"]
        total += subtotal

        texto += f"• {data['cantidad']} {producto} - ${subtotal}\n"

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

    # ===== MENÚ =====
    if texto in ["hola", "menu"]:
        botones(numero, "👋 Bienvenido", [
            ("comida", "🍽 Comida"),
            ("bebidas", "🍹 Bebidas"),
            ("pedido", "🧾 Pedido")
        ])

    elif texto == "comida":
        lista(numero, "🍽 Selecciona:", [
            ("aguachiles", "🌶 Aguachiles"),
            ("ceviches", "🥗 Ceviches"),
            ("cortes finos", "🥩 Cortes")
        ])

    elif texto in menu["comida"]:
        opciones = [
            (f"{texto}|{p}", f"{p.title()} ${menu['comida'][texto][p]}")
            for p in menu["comida"][texto]
        ]
        lista(numero, texto.title(), opciones)

    # ===== PRODUCTO =====
    elif "|" in texto:
        cat, prod = texto.split("|")

        precio = menu["comida"][cat][prod]

        temp_producto[numero] = (cat, prod, precio)
        estado_usuario[numero] = "cantidad"

        enviar(numero, f"¿Cuántos {cat} {prod} necesitas?")

    # ===== CANTIDAD =====
    elif estado_usuario.get(numero) == "cantidad":
        try:
            cantidad = int(texto)
            cat, prod, precio = temp_producto[numero]

            agregar(numero, f"{cat} {prod}", precio, cantidad)

            enviar(numero, f"✅ {cantidad} {cat} {prod} agregado")
            enviar(numero, resumen(numero))

            botones(numero, "¿Qué deseas hacer?", [
                ("seguir", "➕ Seguir"),
                ("finalizar", "✅ Finalizar"),
                ("vaciar", "🗑 Vaciar")
            ])

            estado_usuario[numero] = None

        except:
            enviar(numero, "❌ Escribe un número válido")

    # ===== FINALIZAR =====
    elif texto == "finalizar":
        estado_usuario[numero] = "nombre"
        enviar(numero, "🧑 ¿A nombre de quién es el pedido?")

    elif estado_usuario.get(numero) == "nombre":
        datos_cliente[numero] = {"nombre": texto}
        estado_usuario[numero] = "direccion"
        enviar(numero, "📍 Ingresa la dirección de entrega")

    elif estado_usuario.get(numero) == "direccion":
        datos_cliente[numero]["direccion"] = texto
        estado_usuario[numero] = "telefono"
        enviar(numero, "📞 Ingresa tu número telefónico")

    elif estado_usuario.get(numero) == "telefono":
        datos_cliente[numero]["telefono"] = texto
        estado_usuario[numero] = "confirmar"

        resumen_final = resumen(numero)
        info = datos_cliente[numero]

        enviar(numero, resumen_final)
        enviar(numero,
               f"\n📦 Datos:\n👤 {info['nombre']}\n📍 {info['direccion']}\n📞 {info['telefono']}")

        botones(numero, "¿Confirmar pedido?", [
            ("confirmar", "✅ Confirmar")
        ])

    elif texto == "confirmar":
        enviar(numero, "🙏 Gracias por su preferencia")
        estado_usuario[numero] = None

    elif "gracias" in texto:
        enviar(numero, "🙏 Gracias a usted por su preferencia")

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
