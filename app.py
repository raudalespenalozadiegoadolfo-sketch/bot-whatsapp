from flask import Flask, request
import requests
import os
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 📌 MENÚ
MENU_ITEMS = {
    "almejas": 300,
    "ostiones": 400,
    "ceviche": 200,
    "ceviche camarón": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

MENU_TEXTO = """
🍽️ MENÚ

🦪 Comida:
- Almejas $300
- Ostiones $400
- Ceviche $200
- Ceviche camarón $250
- Aguachile $260

🥤 Bebidas:
- Cerveza $40
- Michelada $100
- Refresco $35
"""

HORARIO = "🕒 Martes a Domingo de 12 PM a 6 PM"

# 📦 CARRITO EN MEMORIA
carritos = {}

# 📌 ENVIAR MENSAJE
def enviar_whatsapp(numero, mensaje):
    url = f"https://graph.facebook.com/v17.0/{os.environ.get('PHONE_NUMBER_ID')}/messages"

    headers = {
        "Authorization": f"Bearer {os.environ.get('WHATSAPP_ACCESS_TOKEN')}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }

    requests.post(url, headers=headers, json=data)

# 📌 WEBHOOK VERIFY
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == os.environ.get("MY_VERIFY_TOKEN"):
        return request.args.get("hub.challenge")
    return "Error", 403

# 📌 WEBHOOK MENSAJES
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]["text"]["body"].lower()
        numero = value["messages"][0]["from"]

        print("Mensaje:", mensaje)

        # 🧠 CREAR CARRITO SI NO EXISTE
        if numero not in carritos:
            carritos[numero] = {
                "items": [],
                "total": 0,
                "nombre": None,
                "direccion": None,
                "estado": "inicio"
            }

        carrito = carritos[numero]

        # 🔥 MOSTRAR MENÚ
        if mensaje in ["hola", "menu", "menú", "si", "sí"]:
            enviar_whatsapp(numero, f"¡Hola! 😊 Aquí tienes nuestro menú:\n{MENU_TEXTO}\n¿Qué deseas ordenar? 🍽️")
            carrito["estado"] = "ordenando"
            return "ok", 200

        # 🛒 AGREGAR PRODUCTOS
        for item, precio in MENU_ITEMS.items():
            if item in mensaje:
                carrito["items"].append((item, precio))
                carrito["total"] += precio

                enviar_whatsapp(numero, f"✅ Agregaste {item} (${precio})\n\n¿Deseas algo más? 😄")
                carrito["estado"] = "ordenando"
                return "ok", 200

        # ➕ MÁS PRODUCTOS
        if mensaje in ["si", "sí"] and carrito["estado"] == "ordenando":
            enviar_whatsapp(numero, "Perfecto 😄 ¿Qué más deseas agregar?")
            return "ok", 200

        # ❌ TERMINAR PEDIDO
        if mensaje in ["no", "nada", "ya"] and carrito["estado"] == "ordenando":
            enviar_whatsapp(numero, "👌 Perfecto. ¿Cuál es tu nombre?")
            carrito["estado"] = "nombre"
            return "ok", 200

        # 👤 GUARDAR NOMBRE
        if carrito["estado"] == "nombre":
            carrito["nombre"] = mensaje
            enviar_whatsapp(numero, "📍 Envíame tu dirección por favor")
            carrito["estado"] = "direccion"
            return "ok", 200

        # 📍 GUARDAR DIRECCIÓN
        if carrito["estado"] == "direccion":
            carrito["direccion"] = mensaje
            enviar_whatsapp(numero, "🚚 ¿Es a domicilio o recogerás en tienda?")
            carrito["estado"] = "tipo_entrega"
            return "ok", 200

        # 🚚 ENTREGA
        if carrito["estado"] == "tipo_entrega":
            envio = 0

            if "domicilio" in mensaje:
                envio = 25

            total_final = carrito["total"] + envio

            # 🧾 TICKET
            resumen = "🧾 RESUMEN DE TU PEDIDO\n\n"

            for item, precio in carrito["items"]:
                resumen += f"- {item} ${precio}\n"

            resumen += f"\nSubtotal: ${carrito['total']}"
            resumen += f"\nEnvío: ${envio}"
            resumen += f"\n💰 Total: ${total_final}\n\n"

            resumen += f"👤 Nombre: {carrito['nombre']}\n"
            resumen += f"📍 Dirección: {carrito['direccion']}\n\n"
            resumen += "🙏 ¡Gracias por tu pedido!"

            enviar_whatsapp(numero, resumen)

            # 🔄 REINICIAR
            carritos[numero] = {
                "items": [],
                "total": 0,
                "nombre": None,
                "direccion": None,
                "estado": "inicio"
            }

            return "ok", 200

        # 🤖 RESPUESTA IA (fallback)
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un bot amable de restaurante"},
                {"role": "user", "content": mensaje}
            ]
        )

        texto = respuesta.choices[0].message.content
        enviar_whatsapp(numero, texto)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run()
