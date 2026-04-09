import os
import re
import requests
import unicodedata
from flask import Flask, request

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ===== MEMORIA =====
carritos = {}

# ===== MENÚ =====
menu = {
    # BEBIDAS
    "coca cola": 30,
    "coca cola light": 30,
    "pepsi": 25,
    "sangria": 25,
    "7up": 25,

    "agua arroz": 35,
    "agua jamaica": 35,
    "agua pina": 35,
    "agua limon": 35,

    "agua arroz 1/2": 20,
    "agua jamaica 1/2": 20,
    "agua pina 1/2": 20,
    "agua limon 1/2": 20,

    "michelada camaron": 100,
    "michelada clamato": 80,
    "michelada tamarindo": 90,

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
    "aguachile negro": 190
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

# ===== PROCESAR PEDIDO =====
def procesar_pedido(numero, texto):
    texto = normalizar(texto)

    if numero not in carritos:
        carritos[numero] = []

    lineas = texto.split("\n")
    encontrados = []

    for linea in lineas:
        for producto in menu:
            if producto in linea:
                cantidad = 1

                match = re.search(r'(\d+)', linea)
                if match:
                    cantidad = int(match.group(1))

                encontrados.append((producto, cantidad))

    for item in encontrados:
        carritos[numero].append(item)

    return encontrados

# ===== RESUMEN =====
def resumen(numero):
    carrito = carritos.get(numero, [])

    if not carrito:
        return "🧾 Tu pedido está vacío"

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

    # VALIDACIÓN META
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # 🔥 EVITA ERROR 'messages'
        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]

        # TEXTO NORMAL
        if "text" in mensaje:
            texto = mensaje["text"]["body"]

        # BOTONES / LISTAS
        elif "interactive" in mensaje:
            if "button_reply" in mensaje["interactive"]:
                texto = mensaje["interactive"]["button_reply"]["id"]
            else:
                texto = mensaje["interactive"]["list_reply"]["id"]

        else:
            return "ok", 200

        texto = normalizar(texto)

        # ===== LÓGICA =====

        if "hola" in texto:
            enviar(numero, "👋 Bienvenido a Marisco Alegre 🦐\nEscribe tu pedido o escribe 'ver pedido'")

        elif "gracias" in texto:
            enviar(numero, "🙏 Gracias a usted por su preferencia")

        elif "ver pedido" in texto or texto == "pedido":
            enviar(numero, resumen(numero))

        elif "finalizar" in texto:
            enviar(numero, resumen(numero))
            enviar(numero, "🙏 Gracias por su preferencia, su pedido está en proceso")
            carritos[numero] = []

        else:
            items = procesar_pedido(numero, texto)

            if items:
                enviar(numero, "✅ Pedido agregado correctamente")
                enviar(numero, resumen(numero))
                enviar(numero, "¿Deseas agregar más o escribir 'finalizar'?")
            else:
                enviar(numero, "❌ No entendí tu pedido, intenta de nuevo")

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

# ===== RUN =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
