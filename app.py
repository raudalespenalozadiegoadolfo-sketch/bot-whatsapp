from flask import Flask, request
import requests

app = Flask(_name_)

# 🔑 CONFIG
ACCESS_TOKEN = "EAAXhxO2OiUsBRC63x4ZBzbfDQMbOniGxLTrgTcFp4xh3uS7nC5T1WD4hz0japFZA6FZCfpPRYAfcPR78VsaX2W5pYG2bPvaey9sMZAzChbqjZAZBZANKVWxUOdZCs7VmnQJc1n2yxLWltLIrhifKT3wafxrZB6AxVf3ObHqZBZCEmB8tsBrQ9Fau9jUzUOhXvKn"
PHONE_NUMBER_ID = "1059311390588707"
VERIFY_TOKEN = "my_token_secreto"
ADMIN_NUMBER = "523171234529"


# 🧠 ESTADO
usuarios = {}

# 📋 MENÚ
menu = {
    "1": {"nombre": "Docena de almejas", "precio": 120},
    "2": {"nombre": "Docena de ostiones", "precio": 150},
    "3": {"nombre": "Litro ceviche camarón", "precio": 130},
    "4": {"nombre": "Litro ceviche pescado", "precio": 110},
    "5": {"nombre": "Litro aguachile", "precio": 140}
}

# 📩 ENVIAR MENSAJE
def enviar_mensaje(numero, mensaje):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=data)


# 🔍 VERIFICACIÓN WEBHOOK
@app.route('/webhook', methods=['GET'])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge
    else:
        return "Error", 403


# 🤖 LÓGICA PRINCIPAL
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]

        # TEXTO
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()
        else:
            texto = ""

        # CREAR USUARIO
        if numero not in usuarios:
            usuarios[numero] = {
                "paso": "inicio",
                "nombre": "",
                "pedido": [],
                "ubicacion": None
            }

        estado = usuarios[numero]["paso"]

        # 👋 INICIO
        if texto in ["hola", "menu", "inicio"] or estado == "inicio":
            enviar_mensaje(numero, "👋 ¡Bienvenido!\n\n¿Nombre del pedido?")
            usuarios[numero]["paso"] = "nombre"

        # 🧾 NOMBRE
        elif estado == "nombre":
            usuarios[numero]["nombre"] = texto

            enviar_mensaje(numero,
                "📋 Menú:\n\n"
                "1️⃣ Docena de almejas - $120\n"
                "2️⃣ Docena de ostiones - $150\n"
                "3️⃣ Litro ceviche camarón - $130\n"
                "4️⃣ Litro ceviche pescado - $110\n"
                "5️⃣ Litro aguachile - $140\n\n"
                "👉 Escribe los números (ej: 135)"
            )

            usuarios[numero]["paso"] = "menu"

        # 🔢 MENÚ
        elif estado == "menu":
            seleccion = list(texto)
            usuarios[numero]["pedido"] = []

            for item in seleccion:
                if item in menu:
                    usuarios[numero]["pedido"].append({
                        "id": item,
                        "cantidad": 0
                    })

            usuarios[numero]["indice"] = 0
            usuarios[numero]["paso"] = "cantidad"

            producto = menu[usuarios[numero]["pedido"][0]["id"]]["nombre"]
            enviar_mensaje(numero, f"¿Cuántas de {producto}?")

        # 📦 CANTIDADES
        elif estado == "cantidad":
            i = usuarios[numero]["indice"]
            usuarios[numero]["pedido"][i]["cantidad"] = int(texto)

            usuarios[numero]["indice"] += 1

            if usuarios[numero]["indice"] < len(usuarios[numero]["pedido"]):
                siguiente = usuarios[numero]["pedido"][usuarios[numero]["indice"]]["id"]
                producto = menu[siguiente]["nombre"]
                enviar_mensaje(numero, f"¿Cuántas de {producto}?")
            else:
                enviar_mensaje(numero, "📍 Envíanos tu ubicación")
                usuarios[numero]["paso"] = "ubicacion"

        # 📍 UBICACIÓN
        elif "location" in mensaje:
            usuarios[numero]["ubicacion"] = mensaje["location"]

            total = 0
            resumen = f"🧾 Pedido de {usuarios[numero]['nombre']}\n\n"

            for item in usuarios[numero]["pedido"]:
                prod = menu[item["id"]]
                subtotal = prod["precio"] * item["cantidad"]
                total += subtotal
                resumen += f"{prod['nombre']} x{item['cantidad']} = ${subtotal}\n"

            resumen += f"\n💰 TOTAL: ${total}"

            # 📲 CLIENTE
            enviar_mensaje(numero, "📦 Pedido listo\n\n" + resumen)
            enviar_mensaje(numero, "✅ Pedido confirmado")

            # 🔥 ADMIN (TÚ)
            enviar_mensaje(ADMIN_NUMBER,
                f"🚨 NUEVO PEDIDO 🚨\n\n"
                f"Cliente: {usuarios[numero]['nombre']}\n"
                f"Número: {numero}\n\n"
                f"{resumen}"
            )

            usuarios[numero]["paso"] = "inicio"

    except Exception as e:
        print("Error:", e)

    return "ok", 200


@app.route('/')
def home():
    return "Bot activo"
