from flask import Flask, request
import requests
import os
import json
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
# MEMORIA
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
# IA INTERPRETACIÓN
# ========================
def interpretar_con_ia(texto, historial):

    prompt = f"""
Eres un sistema que convierte mensajes de clientes en acciones JSON.

MENÚ:
{MENU}

Historial actual del pedido:
{historial}

Mensaje del cliente:
"{texto}"

Responde SOLO en JSON con este formato:

{{
 "accion": "agregar | quitar | ver | saludo | otro",
 "items": [
    {{"producto": "almeja", "cantidad": 2}}
 ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    contenido = response.choices[0].message.content

    try:
        return json.loads(contenido)
    except:
        return {"accion": "otro", "items": []}

# ========================
# GENERAR RESPUESTA
# ========================
def generar_resumen(numero):
    pedido = usuarios.get(numero, {})

    if not pedido:
        return "🧾 No tienes pedido aún."

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
# ENVIAR MENSAJE
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
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"]

        print("MENSAJE:", texto)

        if numero not in usuarios:
            usuarios[numero] = {}

        # ========================
        # IA DECIDE
        # ========================
        decision = interpretar_con_ia(texto, usuarios[numero])

        print("IA:", decision)

        accion = decision.get("accion")
        items = decision.get("items", [])

        # ========================
        # ACCIONES
        # ========================

        if accion == "agregar":
            for item in items:
                prod = item["producto"]
                cant = item["cantidad"]

                if prod in MENU:
                    usuarios[numero][prod] = usuarios[numero].get(prod, 0) + cant

            enviar(numero, generar_resumen(numero))

        elif accion == "quitar":
            for item in items:
                prod = item["producto"]

                if prod in usuarios[numero]:
                    usuarios[numero].pop(prod)

            enviar(numero, "❌ Producto eliminado\n\n" + generar_resumen(numero))

        elif accion == "ver":
            enviar(numero, generar_resumen(numero))

        elif accion == "saludo":
            enviar(numero, "👋 ¡Hola! Puedes pedirme mariscos 😎")

        else:
            # RESPUESTA NATURAL IA
            respuesta = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "Eres un mesero mexicano amigable."},
                    {"role": "user", "content": texto}
                ]
            )
            enviar(numero, respuesta.choices[0].message.content)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

# ========================
# RUN
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
