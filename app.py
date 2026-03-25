from flask import Flask, request
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(_name_)

# 🔐 CONFIG
ACCESS_TOKEN = "EAAXhxO2OiUsBRC63x4ZBzbfDQMbOniGxLTrgTcFp4xh3uS7nC5T1WD4hz0japFZA6FZCfpPRYAfcPR78VsaX2W5pYG2bPvaey9sMZAzChbqjZAZBZANKVWxUOdZCs7VmnQJc1n2yxLWltLIrhifKT3wafxrZB6AxVf3ObHqZBZCEmB8tsBrQ9Fau9jUzUOhXvKn"
PHONE_NUMBER_ID = "1059311390588707"
VERIFY_TOKEN = "my_token_secreto"
ADMIN_NUMBER = "523171234529"  # TU NÚMERO (523171234529)

# 🧠 MEMORIA
usuarios = {}
ultimo_pedido = {}

# 🍤 MENÚ
menu = {
    "1": {"nombre": "Docena de almejas", "precio": 120},
    "2": {"nombre": "Docena de ostiones", "precio": 150},
    "3": {"nombre": "Litro de ceviche de camarón", "precio": 130},
    "4": {"nombre": "Litro de ceviche de pescado", "precio": 110},
    "5": {"nombre": "Litro de aguachile de camarón", "precio": 140}
}

# 📤 ENVIAR MENSAJE
def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=data)


# 📍 ENVIAR UBICACIÓN
def enviar_ubicacion(numero):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": "📍 Envíanos tu ubicación"}
    }
    requests.post(url, headers=headers, json=data)


# 📄 GENERAR PDF
def generar_pdf(nombre, numero, producto, cantidad, total):
    archivo = "pedido.pdf"
    doc = SimpleDocTemplate(archivo)
    styles = getSampleStyleSheet()

    contenido = [
        Paragraph("Pedido Mariscos", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Cliente: {nombre}", styles["Normal"]),
        Paragraph(f"Tel: {numero}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"{producto} x{cantidad} = ${total}", styles["Normal"]),
    ]

    doc.build(contenido)
    return archivo


# 📤 ENVIAR DOCUMENTO
def enviar_documento(numero, archivo):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
    }

    files = {
        "file": (archivo, open(archivo, "rb"), "application/pdf")
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "document"
    }

    requests.post(url, headers=headers, files=files, data=data)


# 🌐 WEBHOOK (TODO EN UNO)
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():

    # 🔐 VERIFICACIÓN META
    if request.method == 'GET':
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Error", 403

    # 📩 MENSAJES
    if request.method == 'POST':
        data = request.get_json()

        try:
            mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
            numero = mensaje["from"]

            # TEXTO
            if "text" in mensaje:
                texto = mensaje["text"]["body"]

                # NUEVO USUARIO
                if numero not in usuarios:
                    usuarios[numero] = {"estado": "nombre"}
                    enviar_mensaje(numero, "👋 Hola, ¿Nombre del pedido?")
                    return "ok", 200

                estado = usuarios[numero]["estado"]

                # NOMBRE
                if estado == "nombre":
                    usuarios[numero]["nombre"] = texto
                    usuarios[numero]["estado"] = "menu"

                    menu_texto = "📋 Menú:\n"
                    for k, v in menu.items():
                        menu_texto += f"{k}. {v['nombre']} - ${v['precio']}\n"

                    enviar_mensaje(numero, menu_texto + "\nElige opción (ej: 1)")
                    return "ok", 200

                # MENÚ
                if estado == "menu":
                    if texto in menu:
                        usuarios[numero]["producto"] = texto
                        usuarios[numero]["estado"] = "cantidad"
                        enviar_mensaje(numero, "¿Cuántos?")
                    else:
                        enviar_mensaje(numero, "Opción inválida")
                    return "ok", 200

                # CANTIDAD
                if estado == "cantidad":
                    cantidad = int(texto)
                    prod = menu[usuarios[numero]["producto"]]

                    total = cantidad * prod["precio"]

                    usuarios[numero]["cantidad"] = cantidad
                    usuarios[numero]["total"] = total
                    usuarios[numero]["estado"] = "ubicacion"

                    enviar_ubicacion(numero)
                    return "ok", 200

            # UBICACIÓN
            if "location" in mensaje:
                lat = mensaje["location"]["latitude"]
                lon = mensaje["location"]["longitude"]

                usuarios[numero]["lat"] = lat
                usuarios[numero]["lon"] = lon

                nombre = usuarios[numero]["nombre"]
                prod = menu[usuarios[numero]["producto"]]
                cantidad = usuarios[numero]["cantidad"]
                total = usuarios[numero]["total"]

                archivo = generar_pdf(nombre, numero, prod["nombre"], cantidad, total)

                enviar_documento(numero, archivo)

                # 📤 ENVIAR A ADMIN
                enviar_mensaje(ADMIN_NUMBER,
                    f"📦 Nuevo pedido\n\n"
                    f"Cliente: {nombre}\n"
                    f"Producto: {prod['nombre']}\n"
                    f"Cantidad: {cantidad}\n"
                    f"Total: ${total}\n"
                    f"Ubicación: https://maps.google.com/?q={lat},{lon}"
                )

                enviar_mensaje(numero, "✅ Pedido confirmado")

                usuarios[numero]["estado"] = "final"

        except Exception as e:
            print("Error:", e)

        return "ok", 200


# 🚀 RUN
if _name_ == '_main_':
    app.run(host="0.0.0.0", port=10000)
