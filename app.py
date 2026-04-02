from flask import Flask, request
import requests
import os
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# =========================
# CONFIG
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
# MEMORIA DE USUARIOS
# =========================
usuarios = {}

# =========================
# HORARIO (México real)
# =========================
def dentro_horario():
    ahora = datetime.now(ZoneInfo("America/Mexico_City"))
    dia = ahora.weekday()  # 0=lunes
    hora = ahora.hour
    return dia >= 1 and dia <= 6 and 11 <= hora < 23

# =========================
# NORMALIZAR TEXTO
# =========================
def limpiar_texto(texto):
    texto = texto.lower()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    return texto

# =========================
# PROCESADOR AVANZADO
# =========================
def procesar_pedido(texto, pedido_actual):
    texto = limpiar_texto(texto)
    partes = re.split(r'[,\n\.]+', texto)

    resultado = pedido_actual.copy()

    for parte in partes:
        parte = parte.strip()

        # CAMBIAR
        cambio = re.search(r'cambia\s*(\d+)\s*([a-z\s]+)\s*por\s*(\d+)', parte)
        if cambio:
            _, producto, nueva = cambio.groups()
            for item in MENU:
                if item in producto:
                    resultado[item] = int(nueva)

        # QUITAR
        quitar = re.search(r'(quita|elimina|borra)\s*(\d+)\s*([a-z\s]+)', parte)
        if quitar:
            _, cantidad, producto = quitar.groups()
            for item in MENU:
                if item in producto:
                    resultado[item] = max(0, resultado.get(item, 0) - int(cantidad))

        # AGREGAR
        agregar = re.search(r'(\d+)\s*(?:orden(?:es)?\s*de\s*)?([a-z\s]+)', parte)
        if agregar:
            cantidad, producto = agregar.groups()
            for item in MENU:
                if item in producto:
                    resultado[item] = resultado.get(item, 0) + int(cantidad)

    return resultado

# =========================
# CALCULAR TOTAL
# =========================
def calcular_total(pedido):
    total = 0
    detalle = ""

    for item, cantidad in pedido.items():
        if cantidad > 0:
            precio = MENU[item]
            subtotal = precio * cantidad
            total += subtotal
            detalle += f"• {cantidad} x {item} = ${subtotal}\n"

    return total, detalle

# =========================
# DETECTAR INTENCIÓN
# =========================
def detectar_intencion(texto):
    texto = limpiar_texto(texto)

    if any(x in texto for x in ["menu"]):
        return "menu"

    if any(x in texto for x in ["gracias", "ok", "perfecto"]):
        return "agradecimiento"

    if any(x in texto for x in ["hola", "oye", "recomiendas"]):
        return "conversacion"

    if any(x in texto for x in ["modificar", "cambiar", "agrega", "quita", "falto"]):
        return "pedido"

    return "pedido"

# =========================
# RESPUESTA CONVERSACIONAL
# =========================
def respuesta_ia(texto):
    texto = limpiar_texto(texto)

    if "recomiendas" in texto:
        return "🔥 Te recomiendo el aguachile y una michelada, es lo más pedido 😎"

    if "hola" in texto:
        return "👋 ¡Bienvenido a Mariscos El Alegre! ¿Qué se te antoja hoy? 😋"

    if "gracias" in texto:
        return "😊 ¡Gracias a ti! Aquí estamos para cuando quieras más mariscos 🦐🍻"

    return "🤔 No entendí del todo, pero puedo ayudarte a ordenar. ¿Qué deseas?"

# =========================
# ENVIAR MENSAJE
# =========================
def enviar(numero, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=data)

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        texto = mensaje["text"]["body"]
        numero = mensaje["from"]
    except:
        return "ok"

    if numero not in usuarios:
        usuarios[numero] = {
            "pedido": {},
            "estado": "inicio",
            "nombre": "",
            "direccion": ""
        }

    sesion = usuarios[numero]

    # =========================
    # HORARIO
    # =========================
    if not dentro_horario():
        enviar(numero, "⏰ Estamos cerrados. Abrimos de martes a domingo de 11 AM a 11 PM 🙏")
        return "ok"

    intencion = detectar_intencion(texto)

    # =========================
    # MENÚ
    # =========================
    if sesion["estado"] == "inicio":
        enviar(numero, """👋 Bienvenido a Mariscos El Alegre 😄

🍽 MENÚ:
* Almeja $300
* Ostion $400
* Ceviche $200
* Ceviche camarón $250
* Aguachile $260

🥤 Bebidas:
* Cerveza $40
* Michelada $100
* Refresco $35

✍ Escribe tu pedido:
Ej: "2 almejas y 1 cerveza"
""")
        sesion["estado"] = "ordenando"
        return "ok"

    # =========================
    # PEDIDO / MODIFICACIÓN
    # =========================
    nuevo_pedido = procesar_pedido(texto, sesion["pedido"])

    if nuevo_pedido != sesion["pedido"]:
        sesion["pedido"] = nuevo_pedido

        total, detalle = calcular_total(sesion["pedido"])

        enviar(numero, f"""🧾 TU PEDIDO:

{detalle}

💰 Total: ${total}""")

        if sesion["estado"] == "ordenando":
            enviar(numero, "🚚 ¿Es domicilio o recoger?")
            sesion["estado"] = "tipo_entrega"

        return "ok"

    # =========================
    # ENTREGA
    # =========================
    if sesion["estado"] == "tipo_entrega":
        if "domicilio" in texto.lower():
            sesion["estado"] = "direccion"
            enviar(numero, "📍 Envíame tu dirección")
        else:
            sesion["estado"] = "nombre"
            enviar(numero, "🙏 ¿Tu nombre?")
        return "ok"

    # =========================
    # DIRECCIÓN
    # =========================
    if sesion["estado"] == "direccion":
        sesion["direccion"] = texto
        sesion["estado"] = "nombre"
        enviar(numero, "🙏 ¿Tu nombre?")
        return "ok"

    # =========================
    # NOMBRE
    # =========================
    if sesion["estado"] == "nombre":
        sesion["nombre"] = texto

        total, detalle = calcular_total(sesion["pedido"])

        envio = 25 if sesion["direccion"] else 0
        total += envio

        enviar(numero, f"""🧾 TU PEDIDO FINAL:

{detalle}
🚚 Envío: ${envio}

💰 TOTAL: ${total}

👤 Nombre: {sesion["nombre"]}
📍 Dirección: {sesion["direccion"] or "Recoger en sucursal"}

✅ Pedido confirmado 😎""")

        usuarios[numero] = {
            "pedido": {},
            "estado": "inicio",
            "nombre": "",
            "direccion": ""
        }

        return "ok"

    # =========================
    # CONVERSACIÓN
    # =========================
    respuesta = respuesta_ia(texto)
    enviar(numero, respuesta)

    return "ok"


@app.route("/", methods=["GET"])
def home():
    return "Bot activo 🚀"
