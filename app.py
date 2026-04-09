import os
import re
import requests
import unicodedata
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ===== MEMORIA =====
carritos = {}

# ===== MENÚ =====
menu = {
    # REFRESCOS
    "coca cola": 30,
    "coca cola light": 30,
    "pepsi": 25,
    "sangria": 25,
    "7up": 25,

    # AGUAS
    "agua arroz": 35,
    "agua jamaica": 35,
    "agua piña": 35,
    "agua limon": 35,

    "agua arroz 1/2": 20,
    "agua jamaica 1/2": 20,
    "agua piña 1/2": 20,
    "agua limon 1/2": 20,

    # MICHELADAS
    "michelada camaron": 100,
    "michelada clamato": 80,
    "michelada tamarindo": 90,

    # CERVEZAS
    "corona extra": 40,
    "corona light": 40,
    "corona cero": 40,
    "tecate": 35,
    "tecate light": 35,
    "indio": 30,
    "ultra": 30,
    "heineken cero": 35,

    # COMIDA
    "camarones diabla": 180,
    "camarones empanizados": 190,
    "camarones ajo": 180,
    "camarones ajillo": 180,

    "pulpo diabla": 220,
    "pulpo empanizado": 220,
    "pulpo zarandeado": 220,

    "filete diabla": 160,
    "filete empanizado": 170,
    "filete ajo": 170,

    "coctel camaron": 190,
    "coctel pulpo": 200,
    "coctel callo": 250,
    "coctel mixto": 220,

    "ceviche pescado": 180,
    "ceviche camaron": 200,

    "aguachile verde": 190,
    "aguachile rojo": 190,
    "aguachile negro": 190,

    "corte arrachera": 220,
    "corte tbone": 250,
    "corte ribeye": 270
}

# ===== NORMALIZAR TEXTO =====
def normalizar(texto):
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = texto.encode('ascii', 'ignore').decode("utf-8")
    return texto

# ===== ENVIAR MENSAJE =====
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
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    botones = []
    for i, (id_op, title) in enumerate(opciones[:3]):
        botones.append({
            "type": "reply",
            "reply": {"id": id_op, "title": title}
        })

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {"buttons": botones}
        }
    }

    requests.post(url, headers=headers, json=data)

# ===== LISTA =====
def lista(numero, titulo, items):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    rows = []
    for key, precio in items[:10]:
        rows.append({
            "id": key,
            "title": key.title(),
            "description": f"${precio}"
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
                "sections": [{"title": "Menú", "rows": rows}]
            }
        }
    }

    requests.post(url, headers=headers, json=data)

# ===== CATEGORÍAS =====
def categorias(numero):
    botones(numero, "👋 Bienvenido a Marisco Alegre 🦐", [
        ("bebidas", "🍹 Bebidas"),
        ("comida", "🍽 Comida"),
        ("pedido", "🧾 Ver pedido")
    ])

# ===== PROCESAR PEDIDO =====
def procesar_pedido(numero, texto):
    texto = normalizar(texto)

    if numero not in carritos:
        carritos[numero] = []

    items = []

    for producto in menu:
        if producto in texto:
            cantidad = 1
            match = re.search(r'(\d+)\s+' + producto, texto)
            if match:
                cantidad = int(match.group(1))

            items.append((producto, cantidad))

    for producto, cantidad in items:
        carritos[numero].append((producto, cantidad))

    return items

# ===== TOTAL =====
def resumen(numero):
    carrito = carritos.get(numero, [])
    total = 0
    texto = "🧾 Tu pedido:\n\n"

    for producto, cantidad in carrito:
        precio = menu[producto]
        subtotal = precio * cantidad
        total += subtotal
        texto += f"{cantidad} x {producto.title()} = ${subtotal}\n"

    texto += f"\n💵 Total: ${total}"
    return texto

# ===== WEBHOOK =====
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        if token == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.json

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]

        # TEXTO
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

        # BOTÓN / LISTA
        elif "interactive" in mensaje:
            if "button_reply" in mensaje["interactive"]:
                texto = mensaje["interactive"]["button_reply"]["id"]
            else:
                texto = mensaje["interactive"]["list_reply"]["id"]

        else:
            return "ok", 200

        texto = normalizar(texto)

        # ===== RESPUESTAS INTELIGENTES =====

        if "hola" in texto:
            categorias(numero)

        elif "gracias" in texto:
            enviar(numero, "🙏 Gracias a usted por su preferencia")

        elif "finalizar" in texto or "terminar" in texto:
            enviar(numero, resumen(numero))
            enviar(numero, "🙏 Gracias por su preferencia, su pedido está en proceso")
            carritos[numero] = []

        elif texto == "pedido":
            enviar(numero, resumen(numero))

        elif texto == "bebidas":
            enviar(numero, "🍹 Escribe lo que deseas pedir")

        elif texto == "comida":
            enviar(numero, "🍽 Escribe tu pedido")

        else:
            items = procesar_pedido(numero, texto)

            if items:
                enviar(numero, "✅ Agregado a tu pedido")
                enviar(numero, resumen(numero))
                botones(numero, "¿Deseas continuar?", [
                    ("seguir", "➕ Agregar más"),
                    ("pedido", "🧾 Ver pedido"),
                    ("finalizar", "✅ Finalizar")
                ])
            else:
                enviar(numero, "❌ No entendí tu pedido")

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

# ===== RUN =====
if __name__ == "_main_":
    app.run(port=10000)
