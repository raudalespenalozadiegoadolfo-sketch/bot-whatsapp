import os
import re
import requests
import unicodedata
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===== CONFIG =====
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

# ===== MENÚ =====
menu = {
    "almeja": 300,
    "ostion": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# ===== MEMORIA SIMPLE =====
usuarios = {}

# ===== NORMALIZACIÓN =====
def normalizar(texto):
    texto = texto.lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto

def singular(palabra):
    if palabra.endswith("es"):
        return palabra[:-2]
    if palabra.endswith("s"):
        return palabra[:-1]
    return palabra

# ===== INTERPRETAR PEDIDO =====
def interpretar_pedido(texto):
    texto = normalizar(texto)
    texto = texto.replace(",", " ").replace("\n", " ")

    palabras = texto.split()
    pedido = {}
    numero_actual = None

    for i, palabra in enumerate(palabras):

        if palabra.isdigit():
            numero_actual = int(palabra)
            continue

        palabra = singular(palabra)

        # detectar productos compuestos
        if i < len(palabras) - 1:
            combinado = palabra + " " + singular(palabras[i+1])
            if combinado in menu:
                if numero_actual is None:
                    numero_actual = 1
                pedido[combinado] = pedido.get(combinado, 0) + numero_actual
                numero_actual = None
                continue

        for producto in menu:
            if palabra in producto:
                if numero_actual is None:
                    numero_actual = 1

                pedido[producto] = pedido.get(producto, 0) + numero_actual
                numero_actual = None
                break

    return pedido

# ===== CALCULAR TOTAL =====
def calcular_total(pedido):
    total = 0
    mensaje = "🧾 Tu pedido:\n\n"

    for producto, cantidad in pedido.items():
        precio = menu[producto]
        subtotal = precio * cantidad
        total += subtotal

        mensaje += f"{cantidad} x {producto} = ${subtotal}\n"

    mensaje += f"\n💰 Total: ${total}"
    return mensaje, total

# ===== ENVIAR MENSAJE =====
def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
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
def enviar_botones(numero):
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
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
            "body": {
                "text": "👋 Bienvenido a Marisco Alegre 🦐\n¿Qué deseas hacer?"
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "menu", "title": "📋 Ver menú"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "pedir", "title": "🛒 Pedir"}
                    }
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=data)

# ===== MENÚ TEXTO =====
def mostrar_menu(numero):
    texto = "📋 MENÚ:\n\n"
    for producto, precio in menu.items():
        texto += f"• {producto} - ${precio}\n"

    texto += "\nEjemplo: 2 ceviche camaron y 1 refresco"
    enviar_mensaje(numero, texto)

# ===== WEBHOOK VERIFY =====
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    return "Error"

# ===== WEBHOOK MENSAJES =====
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        if "messages" not in entry:
            return "ok"

        mensaje = entry["messages"][0]
        numero = mensaje["from"]

        # ===== BOTONES =====
        if mensaje.get("type") == "interactive":
            boton = mensaje["interactive"]["button_reply"]["id"]

            if boton == "menu":
                mostrar_menu(numero)

            elif boton == "pedir":
                enviar_mensaje(numero, "Escribe tu pedido 😊")

            return "ok"

        # ===== TEXTO =====
        texto = mensaje["text"]["body"]
        texto_norm = normalizar(texto)

        # SALUDO
        if texto_norm in ["hola", "buenas", "hey"]:
            enviar_botones(numero)
            return "ok"

        # VER MENÚ
        if "menu" in texto_norm:
            mostrar_menu(numero)
            return "ok"

        # PROCESAR PEDIDO
        pedido = interpretar_pedido(texto)

        if pedido:
            usuarios[numero] = pedido
            mensaje_txt, total = calcular_total(pedido)

            enviar_mensaje(numero, mensaje_txt)
            enviar_mensaje(numero,
                "¿Deseas agregar algo más, modificar o finalizar tu pedido? 🤔"
            )
        else:
            enviar_mensaje(numero,
                "No entendí 😅\nEjemplo: 2 almejas y 1 cerveza"
            )

    except Exception as e:
        print("ERROR:", e)

    return "ok"

# ===== RUN =====
if __name__ == "__main__":
    app.run(port=10000)
