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
# MEMORIA
# =========================
clientes = {}
sesiones = {}

# =========================
# HORARIO MÉXICO
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
# MENÚ TEXTO
# =========================
def menu_texto():
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

✍️ Ejemplo:
"2 almejas y 1 cerveza"
"dos aguachiles y tres micheladas"
"""

# =========================
# 🧠 NORMALIZAR TEXTO
# =========================
def normalizar(texto):
    texto = texto.lower()

    # plural → singular
    reemplazos = {
        "almejas": "almeja",
        "ostiones": "ostion",
        "cervezas": "cerveza",
        "micheladas": "michelada",
        "refrescos": "refresco",
        "ceviches": "ceviche",
        "aguachiles": "aguachile"
    }

    for k, v in reemplazos.items():
        texto = texto.replace(k, v)

    # texto → número
    numeros = {
        "uno": "1", "una": "1",
        "dos": "2",
        "tres": "3",
        "cuatro": "4",
        "cinco": "5",
        "seis": "6",
        "siete": "7",
        "ocho": "8",
        "nueve": "9",
        "diez": "10"
    }

    for palabra, numero in numeros.items():
        texto = re.sub(rf"\b{palabra}\b", numero, texto)

    return texto

# =========================
# 🛒 PROCESAR PEDIDO IA
# =========================
def procesar(texto, numero):
    texto = normalizar(texto)
    sesion = sesiones[numero]
    carrito = sesion["carrito"]

    agregado = False

    for producto in MENU:
        patron = rf"(\d+)\s*{producto}"
        matches = re.findall(patron, texto)

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
# 💰 TOTAL
# =========================
def total(carrito, domicilio=False):
    t = sum(i["cantidad"] * i["precio"] for i in carrito)
    if domicilio:
        t += 25
    return t

# =========================
# 🧾 RESUMEN
# =========================
def resumen(numero):
    sesion = sesiones[numero]
    carrito = sesion["carrito"]

    texto = "🧾 TU PEDIDO:\n\n"

    for i in carrito:
        texto += f"• {i['cantidad']} x {i['producto']} = ${i['cantidad'] * i['precio']}\n"

    envio = sesion["tipo"] == "domicilio"

    if envio:
        texto += "\n🚚 Envío $25"

    texto += f"\n\n💰 TOTAL: ${total(carrito, envio)}"

    return texto

# =========================
# 🌐 WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok"

        msg_data = value["messages"][0]
        numero = msg_data["from"]
        mensaje = msg_data["text"]["body"].lower()

        print("Mensaje:", mensaje)

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
            enviar(numero, "⏰ Estamos cerrados.\nAbrimos de martes a domingo de 12 pm a 11 pm 🙏")
            return "ok"

        # cliente frecuente
        if numero in clientes and mensaje in ["hola", "menu"]:
            enviar(numero, f"😄 Hola {clientes[numero]['nombre']}, ¿quieres lo mismo de la última vez?")
            return "ok"

        # saludo
        if mensaje in ["hola", "menu", "menú"]:
            enviar(numero, "👋 Bienvenido 😄\n" + menu_texto())
            return "ok"

        # pedido IA
        if procesar(mensaje, numero):
            enviar(numero, "🛒 Pedido agregado 😎")
            enviar(numero, "¿Algo más o escribe finalizar?")
            return "ok"

        # finalizar
        if "finalizar" in mensaje:
            if not sesion["carrito"]:
                enviar(numero, "Tu carrito está vacío 😅")
                return "ok"

            enviar(numero, resumen(numero))
            enviar(numero, "\n¿Es domicilio o recoger? 🚚🏪")
            return "ok"

        # tipo entrega
        if mensaje in ["domicilio", "envio"]:
            sesion["tipo"] = "domicilio"
            enviar(numero, "📍 Envíame tu dirección")
            return "ok"

        if mensaje in ["recoger", "tienda"]:
            sesion["tipo"] = "recoger"
            enviar(numero, "¿A nombre de quién?")
            return "ok"

        # dirección
        if sesion["tipo"] == "domicilio" and not sesion["direccion"]:
            sesion["direccion"] = mensaje
            enviar(numero, "🙏 ¿Tu nombre?")
            return "ok"

        # nombre
        if not sesion["nombre"]:
            sesion["nombre"] = mensaje

            # guardar cliente
            clientes[numero] = {
                "nombre": sesion["nombre"],
                "ultimo_pedido": sesion["carrito"]
            }

            texto = resumen(numero)
            texto += f"\n\n👤 Nombre: {sesion['nombre']}"

            if sesion["tipo"] == "domicilio":
                texto += f"\n📍 Dirección: {sesion['direccion']}"

            texto += "\n\n✅ Pedido confirmado 😎"

            enviar(numero, texto)

            sesiones.pop(numero)
            return "ok"

    except Exception as e:
        print("ERROR:", e)

    return "ok"

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(port=5000
