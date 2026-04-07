from flask import Flask, request
import requests
import os
import re
from openai import OpenAI

app = Flask(__name__)

# ========================
# CONFIG
# ========================
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ========================
# MEMORIA SIMPLE (SaaS base)
# ========================
usuarios = {}

# ========================
# MENÚ
# ========================
MENU = {
    "almeja": 300,
    "ostion": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# ========================
# LIMPIAR TEXTO
# ========================
def limpiar(texto):
    texto = texto.lower()
    texto = texto.replace(",", " y ")
    texto = texto.replace("ó", "o")
    texto = texto.replace("á", "a")
    texto = texto.replace("é", "e")
    texto = texto.replace("í", "i")
    texto = texto.replace("ú", "u")
    return texto

# ========================
# PROCESAR PEDIDO
# ========================
def procesar_pedido(texto, numero):
    texto = limpiar(texto)
    patron = r"(\d+)\s+([a-z\s]+)"
    coincidencias = re.findall(patron, texto)

    if numero not in usuarios:
        usuarios[numero] = {}

    for cantidad, producto in coincidencias:
        producto = producto.strip()

        if producto.endswith("s"):
            producto = producto[:-1]

        if producto in MENU:
            usuarios[numero][producto] = usuarios[numero].get(producto, 0) + int(cantidad)

    return generar_resumen(numero)

# ========================
# MODIFICAR PEDIDO
# ========================
def modificar_pedido(texto, numero):
    texto = limpiar(texto)

    if numero not in usuarios:
        return "No tienes pedido aún."

    if "quita" in texto or "elimina" in texto:
        for producto in MENU:
            if producto in texto:
                usuarios[numero].pop(producto, None)
                return f"❌ Quité {producto} de tu pedido."

    if "agrega" in texto:
        return procesar_pedido(texto, numero)

    return None

# ========================
# RESUMEN
# ========================
def generar_resumen(numero):
    pedido = usuarios.get(numero, {})

    if not pedido:
        return "No tienes pedido aún."

    total = 0
    texto = "🧾 TU PEDIDO:\n\n"

    for producto, cantidad in pedido.items():
        precio = MENU[producto]
        subtotal = precio * cantidad
        total += subtotal

        texto += f"{cantidad} x {producto} = ${subtotal}\n"

    texto += f"\n💰 TOTAL: ${total}"

    return texto

# ========================
# CHAT GPT
# ========================
def responder_ia(mensaje):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Eres un mesero amable de mariscos en México. Responde corto, claro y amigable."},
                {"role": "user", "content": mensaje}
            ]
        )
        return response.choices[0].message.content
    except:
        return "🤖 Ocurrió un error con la IA."

# ========================
# ENVIAR WHATSAPP
# ========================
def enviar(numero, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }

    requests.post(url, headers=headers, json=data)

# ========================
# WEBHOOK
# ========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"]

        print("MENSAJE:", texto)

        # MENÚ
        if "menu" in texto.lower():
            enviar(numero, "📋 Escribe tu pedido\nEj: 2 almejas y 1 cerveza")
            return "ok", 200

        # MODIFICAR
        mod = modificar_pedido(texto, numero)
        if mod:
            enviar(numero, mod)
            return "ok", 200

        # PEDIDO
        pedido = procesar_pedido(texto, numero)
        if pedido:
            enviar(numero, pedido)
            return "ok", 200

        # IA
        respuesta = responder_ia(texto)
        enviar(numero, respuesta)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

# ========================
# RUN
# ========================
if __name__ == "_main_":
    app.run(host="0.0.0.0", port=10000)
