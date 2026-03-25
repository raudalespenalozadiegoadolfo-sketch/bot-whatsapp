from flask import Flask, request
import requests

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    else:
        return "Error", 403
        
# 🔑 CONFIG
ACCESS_TOKEN = "EAAXhxO2OiUsBRC63x4ZBzbfDQMbOniGxLTrgTcFp4xh3uS7nC5T1WD4hz0japFZA6FZCfpPRYAfcPR78VsaX2W5pYG2bPvaey9sMZAzChbqjZAZBZANKVWxUOdZCs7VmnQJc1n2yxLWltLIrhifKT3wafxrZB6AxVf3ObHqZBZCEmB8tsBrQ9Fau9jUzUOhXvKn"
PHONE_NUMBER_ID = "1059311390588707"
VERIFY_TOKEN = "my_token_secreto"
ADMIN_NUMBER = "523171234529"

usuarios = {}
ultimo_pedido = {}

# 🍽️ MENÚ
menu = {
    "1": {"nombre": "Docena de almejas", "precio": 120},
    "2": {"nombre": "Docena de ostiones", "precio": 150},
    "3": {"nombre": "Litro de ceviche de camarón", "precio": 130},
    "4": {"nombre": "Litro de ceviche de pescado", "precio": 110},
    "5": {"nombre": "Litro de aguachile de camarón", "precio": 140}
}

# 📩 MENSAJE
def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=payload)

# 📍 PEDIR UBICACIÓN
def pedir_ubicacion(numero):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "location_request_message",
            "body": {"text": "📍 Envíanos tu ubicación"},
            "action": {"name": "send_location"}
        }
    }
    requests.post(url, headers=headers, json=payload)

# 📍 ENVIAR UBICACIÓN AL ADMIN
def enviar_ubicacion_admin(lat, lon):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": ADMIN_NUMBER,
        "type": "location",
        "location": {
            "latitude": lat,
            "longitude": lon,
            "name": "Ubicación cliente"
        }
    }
    requests.post(url, headers=headers, json=payload)

# 📄 PDF
def crear_pdf(datos):
    archivo = "pedido.pdf"
    doc = SimpleDocTemplate(archivo)
    styles = getSampleStyleSheet()

    contenido = []
    contenido.append(Paragraph("Pedido Mariscos", styles["Title"]))
    contenido.append(Spacer(1, 10))

    contenido.append(Paragraph(f"Cliente: {datos['nombre']}", styles["Normal"]))
    contenido.append(Paragraph(f"Tel: {datos['telefono']}", styles["Normal"]))
    contenido.append(Spacer(1, 10))

    for item in datos["pedido"]:
        contenido.append(Paragraph(item, styles["Normal"]))

    contenido.append(Spacer(1, 10))
    contenido.append(Paragraph(f"Total: ${datos['total']}", styles["Normal"]))

    doc.build(contenido)
    return archivo

# 📤 PDF CORRECTO
def enviar_pdf(path):
    url_upload = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/media"

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    files = {
        "file": ("pedido.pdf", open(path, "rb"), "application/pdf")
    }

    data = {
        "messaging_product": "whatsapp",
        "type": "document"
    }

    res = requests.post(url_upload, headers=headers, files=files, data=data)
    media_id = res.json().get("id")

    if not media_id:
        print("❌ Error subiendo PDF:", res.text)
        return

    url_send = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

    headers2 = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": ADMIN_NUMBER,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": "pedido.pdf"
        }
    }

    requests.post(url_send, headers=headers2, json=payload)

# 🔘 BOTÓN
def enviar_boton_admin():
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": ADMIN_NUMBER,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "📦 Pedido listo"},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": "enviado",
                            "title": "🚚 Enviar pedido"
                        }
                    }
                ]
            }
        }
    }

    requests.post(url, headers=headers, json=payload)

# 🌐 WEBHOOK
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
            return "OK", 200

        msg = value["messages"][0]
        sender = msg["from"]
        tipo = msg["type"]

        # ADMIN BOTÓN
        if sender == ADMIN_NUMBER and tipo == "interactive":
            if "button_reply" in msg["interactive"]:
                if msg["interactive"]["button_reply"]["id"] == "enviado":
                    cliente = ultimo_pedido.get("cliente")
                    if cliente:
                        enviar_mensaje(cliente, "🚚 Tu pedido va en camino 😎")
            return "OK", 200

        # CLIENTE
        if sender not in usuarios:
            usuarios[sender] = {"estado": "inicio"}

        estado = usuarios[sender]["estado"]

        if tipo == "location":
            lat = msg["location"]["latitude"]
            lon = msg["location"]["longitude"]

            usuarios[sender]["ubicacion"] = {"lat": lat, "lon": lon}
            usuarios[sender]["estado"] = "confirmar"

            enviar_mensaje(sender, "Escribe SI para confirmar")
            return "OK", 200

        if tipo == "text":
            message = msg["text"]["body"].lower()

            if "gracias" in message:
                enviar_mensaje(sender, "🙏 Gracias por su preferencia")
                return "OK", 200

            if "tiempo" in message:
                enviar_mensaje(sender, "⏱️ 20 a 40 minutos")
                return "OK", 200

            if "hola" in message or estado == "inicio":
                usuarios[sender]["estado"] = "nombre"
                enviar_mensaje(sender, "¿Nombre del pedido?")
                return "OK", 200

            elif estado == "nombre":
                usuarios[sender]["nombre"] = message
                usuarios[sender]["telefono"] = sender
                usuarios[sender]["estado"] = "menu"

                enviar_mensaje(sender, "Menú:\n1 2 3 4 5\nEjemplo: 135")
                return "OK", 200

            elif estado == "menu":
                opciones = message.replace(" ", "").split(",")

                usuarios[sender]["seleccion"] = opciones
                usuarios[sender]["indice"] = 0
                usuarios[sender]["pedido"] = []
                usuarios[sender]["total"] = 0
                usuarios[sender]["estado"] = "cantidad"

                actual = opciones[0]
                enviar_mensaje(sender, f"¿Cuántas de {menu[actual]['nombre']}?")
                return "OK", 200

            elif estado == "cantidad" and message.isdigit():
                cantidad = int(message)

                opciones = usuarios[sender]["seleccion"]
                idx = usuarios[sender]["indice"]
                op = opciones[idx]

                nombre = menu[op]["nombre"]
                precio = menu[op]["precio"]

                subtotal = cantidad * precio

                usuarios[sender]["pedido"].append(f"{nombre} x{cantidad} = ${subtotal}")
                usuarios[sender]["total"] += subtotal

                usuarios[sender]["indice"] += 1

                if usuarios[sender]["indice"] < len(opciones):
                    siguiente = opciones[usuarios[sender]["indice"]]
                    enviar_mensaje(sender, f"¿Cuántas de {menu[siguiente]['nombre']}?")
                else:
                    usuarios[sender]["estado"] = "ubicacion"
                    pedir_ubicacion(sender)

                return "OK", 200

            elif estado == "confirmar":
                if "si" in message:
                    datos = usuarios[sender]

                    pdf = crear_pdf(datos)
                    enviar_pdf(pdf)

                    ubic = usuarios[sender]["ubicacion"]
                    enviar_ubicacion_admin(ubic["lat"], ubic["lon"])

                    enviar_boton_admin()

                    ultimo_pedido["cliente"] = sender

                    enviar_mensaje(sender, "Pedido confirmado")

                    usuarios[sender] = {"estado": "inicio"}
                else:
                    enviar_mensaje(sender, "Pedido cancelado")

                return "OK", 200

    except Exception as e:
        print("Error:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(port=5000)
