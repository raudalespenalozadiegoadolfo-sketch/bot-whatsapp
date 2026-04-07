from flask import Flask, request, jsonify
import requests
import os
import json
from openai import OpenAI

app = Flask(__name__)

# ==============================
# 🔐 VARIABLES DE ENTORNO
# ==============================
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================
# 📋 MENÚ
# ==============================
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

# ==============================
# 🧠 MEMORIA
# ==============================
usuarios = {}

# ==============================
# 📤 ENVIAR MENSAJE
# ==============================
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

# ==============================
# 📋 MOSTRAR MENÚ
# ==============================
def mostrar_menu():
    texto = "📋 MENÚ:\n\n"
    for producto, precio in MENU.items():
        texto += f"• {producto} - ${precio}\n"
    texto += "\nEjemplo: 2 almejas y 1 cerveza"
    return texto

# ==============================
# 🧾 RESUMEN PEDIDO
# ==============================
def generar_resumen(numero):
    pedido = usuarios.get(numero, {})

    if not pedido:
        return "🧾 No tienes pedido aún."

    texto = "🧾 Tu pedido:\n\n"
    total = 0

    for producto, cantidad in pedido.items():
        subtotal = MENU[producto] * cantidad
        total += subtotal
        texto += f"{cantidad} x {producto} = ${subtotal}\n"

    texto += f"\n💰 Total: ${total}"
    return texto

# ==============================
# ❌ CANCELAR PRODUCTOS
# ==============================
def cancelar_pedido(numero, items):
    if numero not in usuarios or not usuarios[numero]:
        return "🧾 No tienes pedido aún."

    for item in items:
        producto = item["producto"].lower()

        if producto in usuarios[numero]:
            del usuarios[numero][producto]

    return generar_resumen(numero)

# ==============================
# 🧠 IA (JSON SEGURO)
# ==============================
def interpretar_mensaje(texto):
    prompt = f"""
Eres un asistente de restaurante.

Menú:
{MENU}

Acciones posibles:
- ordenar
- ver
- saludo
- cancelar
- otro

Responde SOLO en JSON válido:

{{
"accion": "...",
"items": [{{"producto": "...", "cantidad": numero}}]
}}

Mensaje: "{texto}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        contenido = response.choices[0].message.content.strip()
        print("IA:", contenido)

        return json.loads(contenido)

    except Exception as e:
        print("ERROR IA:", e)
        return {"accion": "otro", "items": []}

# ==============================
# 🧠 PROCESAR PEDIDO
# ==============================
def procesar_pedido(numero, items):
    if numero not in usuarios:
        usuarios[numero] = {}

    for item in items:
        producto = item["producto"].lower()
        cantidad = item["cantidad"]

        if producto in MENU:
            usuarios[numero][producto] = usuarios[numero].get(producto, 0) + cantidad

# ==============================
# 🔗 WEBHOOK
# ==============================
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("DATA:", data)

    try:
        entry = data["entry"][0]["changes"][0]["value"]

        if "messages" in entry:
            mensaje = entry["messages"][0]
            numero = mensaje["from"]
            texto = mensaje["text"]["body"]

            print("MENSAJE:", texto)

            ia = interpretar_mensaje(texto)
            accion = ia.get("accion", "otro")
            items = ia.get("items", [])

            # ==========================
            # 🤖 LÓGICA INTELIGENTE
            # ==========================
            if accion == "saludo":
                enviar(numero, "👋 ¡Hola! Bienvenido a Marisco Alegre 🦐\n¿Quieres ver el menú?")

            elif accion == "ver":
                if numero in usuarios and usuarios[numero]:
                    enviar(numero, generar_resumen(numero))
                else:
                    enviar(numero, mostrar_menu())

            elif accion == "ordenar":
                procesar_pedido(numero, items)
                enviar(numero, generar_resumen(numero))

            elif accion == "cancelar":
                respuesta = cancelar_pedido(numero, items)
                enviar(numero, respuesta)

            else:
                enviar(numero, "🤖 Puedes pedirme el menú o hacer un pedido.")

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"status": "ok"})
