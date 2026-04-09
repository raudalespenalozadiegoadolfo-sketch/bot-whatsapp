import os
import requests
from flask import Flask, request

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

carritos = {}
estado = {}
temp = {}
datos = {}
contador_orden = 1

# ===== MENÚ =====
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
        "cocteles": {
            "camaron": 190,
            "pulpo": 200,
            "callo": 250,
            "mixto": 220
        },
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
        "micheladas": {
            "camaron": 100,
            "clamato": 80,
            "tamarindo": 90
        },
        "refrescos": {
            "coca cola": 30,
            "coca light": 30,
            "pepsi": 25,
            "7 up": 25,
            "manzana": 25,
            "sprite": 30
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

# ===== UTIL =====
def enviar(numero, texto):
    requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": texto}
        }
    )

def botones(numero, texto, opciones):
    requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": texto},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": o[0], "title": o[1]}}
                        for o in opciones
                    ]
                }
            }
        }
    )

def lista(numero, texto, opciones):
    requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
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
                        "rows": [{"id": o[0], "title": o[1]} for o in opciones]
                    }]
                }
            }
        }
    )

# ===== CARRITO =====
def agregar(numero, producto, precio, cantidad):
    if numero not in carritos:
        carritos[numero] = {}

    if producto in carritos[numero]:
        carritos[numero][producto]["cant"] += cantidad
    else:
        carritos[numero][producto] = {
            "precio": precio,
            "cant": cantidad
        }

def resumen(numero):
    total = 0
    texto = "🧾 Tu pedido:\n\n"

    for p, d in carritos.get(numero, {}).items():
        sub = d["precio"] * d["cant"]
        total += sub
        texto += f"• {d['cant']} {p} - ${sub}\n"

    texto += f"\n💵 Total: ${total}"
    return texto

# ===== WEBHOOK =====
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "error", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    global contador_orden

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
    if texto in ["hola", "menu", "seguir"]:
        botones(numero, "👋 ¿Qué deseas pedir?", [
            ("comida", "🍽 Comida"),
            ("bebidas", "🍹 Bebidas"),
            ("pedido", "🧾 Ver pedido")
        ])

    # ===== CATEGORÍAS =====
    elif texto in menu:
        lista(numero, "Selecciona categoría:", [
            (sub, sub.title()) for sub in menu[texto]
        ])
        estado[numero] = texto

    # ===== SUBCATEGORÍA =====
    elif estado.get(numero) in menu and texto in menu[estado[numero]]:
        cat = estado[numero]

        lista(numero, texto.title(), [
            (f"{cat}|{texto}|{p}", f"{p.title()} ${menu[cat][texto][p]}")
            for p in menu[cat][texto]
        ])

    # ===== PRODUCTO =====
    elif "|" in texto:
        cat, sub, prod = texto.split("|")
        precio = menu[cat][sub][prod]

        nombre = f"{sub.title()} {prod.title()}"

        temp[numero] = (nombre, precio)
        estado[numero] = "cantidad"

        enviar(numero, f"¿Cuántos {nombre} necesitas?")

    # ===== CANTIDAD =====
    elif estado.get(numero) == "cantidad":
        try:
            cantidad = int(texto)
            nombre, precio = temp[numero]

            agregar(numero, nombre, precio, cantidad)

            enviar(numero, f"✅ {cantidad} {nombre} agregado")
            enviar(numero, resumen(numero))

            botones(numero, "¿Qué deseas hacer?", [
                ("seguir", "➕ Seguir"),
                ("finalizar", "✅ Finalizar"),
                ("vaciar", "🗑 Vaciar")
            ])

            estado[numero] = None

        except:
            enviar(numero, "❌ Escribe un número válido")

    # ===== VACIAR =====
    elif texto == "vaciar":
        carritos[numero] = {}
        enviar(numero, "🗑 Pedido vacío")

    # ===== FINALIZAR =====
    elif texto == "finalizar":
        estado[numero] = "nombre"
        enviar(numero, "🧑 Nombre del cliente:")

    elif estado.get(numero) == "nombre":
        datos[numero] = {"nombre": texto}
        estado[numero] = "direccion"
        enviar(numero, "📍 Dirección:")

    elif estado.get(numero) == "direccion":
        datos[numero]["direccion"] = texto
        estado[numero] = "telefono"
        enviar(numero, "📞 Teléfono:")

    elif estado.get(numero) == "telefono":
        datos[numero]["telefono"] = texto

        orden = f"ORD-{str(contador_orden).zfill(4)}"
        contador_orden += 1

        datos[numero]["orden"] = orden

        enviar(numero, f"🧾 Orden: {orden}")
        enviar(numero, resumen(numero))

        botones(numero, "Confirmar pedido", [
            ("confirmar", "✅ Confirmar")
        ])

        estado[numero] = "confirmar"

    elif texto == "confirmar":
        info = datos[numero]

        enviar(numero,
               f"✅ Pedido confirmado\n\n"
               f"🧾 {info['orden']}\n"
               f"👤 {info['nombre']}\n"
               f"📍 {info['direccion']}\n"
               f"📞 {info['telefono']}")

        enviar(numero, "🙏 Gracias por su preferencia")

        estado[numero] = None

    elif "gracias" in texto:
        enviar(numero, "🙏 Gracias a usted por su preferencia")

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
