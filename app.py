from flask import Flask, request
import requests
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# =========================
# VARIABLES
# =========================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# =========================
# MENÚ
# =========================
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

# =========================
# MEMORIA (clientes)
# =========================
clientes = {}
sesiones = {}

# =========================
# HORARIO
# =========================
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    return ahora.weekday() >= 1 and ahora.weekday() <= 6 and 12 <= ahora.hour < 23

# =========================
# ENVIAR MENSAJE
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
# MOSTRAR MENÚ
# =========================
def menu():
    return """🍽️ MENÚ

🦪 Almejas $300
🦪 Ostiones $400
🐟 Ceviche $200
🦐 Ceviche camarón $250
🔥 Aguachile $260

🥤 Bebidas:
🍺 Cerveza $40
🍹 Michelada $100
🥤 Refresco $35

Ejemplo: "2 almejas y 1 cerveza"
"""

# =========================
# PROCESAR PEDIDO
# =========================
def procesar(texto, numero):
    texto = texto.lower()
    sesion = sesiones[numero]
    carrito = sesion["carrito"]

    agregado = False

    for producto in MENU:
        matches = re.findall(rf"(\\d+)\s*{producto}", texto)

        for m in matches:
            cantidad = int(m)
            precio = MENU[producto]

            carrito.append({
                "producto": producto,
                "cantidad": cantidad,
                "precio": precio
            })

            agregado = True

    return agregado

# =========================
# TOTAL
# =========================
def total(carrito, domicilio=False):
    t = sum(i["cantidad"] * i["precio"] for i in carrito)
    if domicilio:
        t += 25
    return t

# =========================
# RESUMEN
# =========================
def resumen(numero):
    sesion = sesiones[numero]
    carrito = sesion["carrito"]

    texto = "🧾 TU PEDIDO:\n\n"

    for i in carrito:
        texto += f"- {i['cantidad']} {i['producto']} = ${i['cantidad'] * i['precio']}\n"

    envio = sesion["tipo"] == "domicilio"

    if envio:
        texto += "\n🚚 Envío $25"

    texto += f"\n\n💰 Total: ${total(carrito, envio)}"

    return texto

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok"

        msg = value["messages"][0]["text"]["body"].lower()
        numero = value["messages"][0]["from"]

        # crear sesión
        if numero not in sesiones:
            sesiones[numero] = {
                "carrito": [],
                "nombre": None,
                "direccion": None,
                "tipo": None
            }

        sesion = sesiones[numero]

        # horario
        if not dentro_horario():
            enviar(numero, "⏰ Cerrado. Abrimos de 12 a 11 pm")
            return "ok"

        # cliente conocido
        if numero in clientes and msg in ["hola", "menu"]:
            enviar(numero, f"😄 Hola {clientes[numero]['nombre']}, ¿quieres lo mismo de la última vez?")
            return "ok"

        # saludo
        if msg in ["hola", "menu"]:
            enviar(numero, "👋 Bienvenido 😄\n" + menu())
            return "ok"

        # pedido
        if procesar(msg, numero):
            enviar(numero, "🛒 Agregado. ¿Algo más o escribe finalizar?")
            return "ok"

        # finalizar
        if "finalizar" in msg:
            enviar(numero, resumen(numero))
            enviar(numero, "¿Domicilio o recoger?")
            return "ok"

        # entrega
        if msg in ["domicilio", "recoger"]:
            sesion["tipo"] = msg
            enviar(numero, "¿Tu nombre?")
            return "ok"

        # nombre
        if not sesion["nombre"]:
            sesion["nombre"] = msg
            enviar(numero, "📍 Dirección:")
            return "ok"

        # dirección
        if not sesion["direccion"]:
            sesion["direccion"] = msg

            # guardar cliente
            clientes[numero] = {
                "nombre": sesion["nombre"],
                "ultimo_pedido": sesion["carrito"]
            }

            enviar(numero, resumen(numero))
            enviar(numero, "✅ Pedido confirmado 😎")

            sesiones.pop(numero)

            return "ok"

    except Exception as e:
        print("ERROR:", e)

    return "ok"
