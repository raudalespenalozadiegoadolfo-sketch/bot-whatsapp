from flask import Flask, request
import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from openai import OpenAI

app = Flask(__name__)

# =========================
# CONFIG
# =========================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# MEMORIA (SESIONES)
# =========================
sesiones = {}

# =========================
# MENÚ
# =========================
MENU = {
    "almejas": 300,
    "ostiones": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# =========================
# HORARIO (MÉXICO)
# =========================
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    dia = ahora.weekday()  # 0 lunes
    hora = ahora.hour
    return dia >= 1 and dia <= 6 and 12 <= hora < 23

# =========================
# ENVIAR WHATSAPP
# =========================
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

# =========================
# IA CONVERSACIONAL PRO
# =========================
def responder_ia(texto):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """
Eres un asistente del restaurante "Marisco Alegre".

Hablas como humano, amable, mexicano y con emojis.

Puedes:
- conversar natural
- recomendar platillos
- responder dudas
- bromear ligeramente

NO generes pedidos.
NO cobres.
Solo conversación.

Respuestas cortas, claras y amigables.
"""
            },
            {"role": "user", "content": texto}
        ]
    )
    return res.choices[0].message.content

# =========================
# MOSTRAR MENÚ
# =========================
def mostrar_menu(numero):
    texto = "🦐 Bienvenido a Marisco Alegre 😄\n\n🍽️ MENÚ\n\n"
    for item, precio in MENU.items():
        texto += f"• {item.title()} ${precio}\n"
    texto += "\nEjemplo: 2 almejas y 1 cerveza 🍻"
    enviar(numero, texto)

# =========================
# PROCESAR PEDIDO
# =========================
def procesar_pedido(texto):
    pedido = {}
    texto = texto.lower()

    for item in MENU:
        if item in texto:
            palabras = texto.split()
            cantidad = 1
            for i, p in enumerate(palabras):
                if p.isdigit() and i+1 < len(palabras) and item in texto:
                    cantidad = int(p)
            pedido[item] = pedido.get(item, 0) + cantidad

    return pedido

# =========================
# TOTAL
# =========================
def calcular_total(pedido):
    total = 0
    detalle = ""
    for item, cantidad in pedido.items():
        precio = MENU[item]
        subtotal = precio * cantidad
        total += subtotal
        detalle += f"• {cantidad} x {item} = ${subtotal}\n"
    return total, detalle

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error"

    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"].lower()
    except:
        return "ok"

    if numero not in sesiones:
        sesiones[numero] = {
            "estado": "inicio",
            "pedido": {},
            "nombre": "",
            "direccion": ""
        }

    sesion = sesiones[numero]

    # =========================
    # AGRADECIMIENTO (NO REINICIA)
    # =========================
    if "gracias" in texto:
        enviar(numero, "😊 ¡Gracias a ti! Aquí seguimos para cuando gustes 🦐🍻")
        sesion["estado"] = "finalizado"
        return "ok"

    # =========================
    # SI YA TERMINÓ → CHAT IA
    # =========================
    if sesion["estado"] == "finalizado":
        respuesta = responder_ia(texto)
        enviar(numero, respuesta)
        return "ok"

    # =========================
    # HORARIO
    # =========================
    if not dentro_horario():
        enviar(numero, "⏰ Estamos cerrados.\nAbrimos de martes a domingo de 12 pm a 11 pm 🙏")
        return "ok"

    # =========================
    # INICIO
    # =========================
    if sesion["estado"] == "inicio":
        mostrar_menu(numero)
        sesion["estado"] = "ordenando"
        return "ok"

    # =========================
    # PEDIDO
    # =========================
    if sesion["estado"] == "ordenando":
        pedido = procesar_pedido(texto)

        if pedido:
            for k, v in pedido.items():
                sesion["pedido"][k] = sesion["pedido"].get(k, 0) + v

            total, detalle = calcular_total(sesion["pedido"])

            enviar(numero, f"🧾 TU PEDIDO:\n\n{detalle}\n💰 Total: ${total}")
            enviar(numero, "🚚 ¿Es domicilio o recoger?")
            sesion["estado"] = "tipo_entrega"
        else:
            respuesta = responder_ia(texto)
            enviar(numero, respuesta)

        return "ok"

    # =========================
    # ENTREGA
    # =========================
    if sesion["estado"] == "tipo_entrega":
        if "domicilio" in texto:
            sesion["domicilio"] = True
            enviar(numero, "📍 Envíame tu dirección")
            sesion["estado"] = "direccion"
        else:
            sesion["domicilio"] = False
            enviar(numero, "🙏 ¿Tu nombre?")
            sesion["estado"] = "nombre"
        return "ok"

    # =========================
    # DIRECCIÓN
    # =========================
    if sesion["estado"] == "direccion":
        sesion["direccion"] = texto
        enviar(numero, "🙏 ¿Tu nombre?")
        sesion["estado"] = "nombre"
        return "ok"

    # =========================
    # NOMBRE
    # =========================
    if sesion["estado"] == "nombre":
        sesion["nombre"] = texto

        total, detalle = calcular_total(sesion["pedido"])

        if sesion.get("domicilio"):
            total += 25
            detalle += "\n🚚 Envío $25"

        enviar(numero, f"""🧾 TU PEDIDO:

{detalle}

💰 TOTAL: ${total}

👤 Nombre: {sesion['nombre']}
📍 Dirección: {sesion.get('direccion','Recoger en tienda')}

✅ Pedido confirmado 😎""")

        sesion["estado"] = "finalizado"
        return "ok"

    return "ok"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(port=5000)
