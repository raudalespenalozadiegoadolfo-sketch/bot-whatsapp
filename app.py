import os
from flask import Flask, request
import requests
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)

# =========================
# VARIABLES
# =========================
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# MENÚ
# =========================
MENU = {
    "almejas": 300,
    "ostiones": 400,
    "ceviche": 200,
    "ceviche camarón": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

# =========================
# PEDIDOS TEMPORALES
# =========================
pedidos = {}

# =========================
# HORARIO
# =========================
def negocio_abierto():
    ahora = datetime.now()
    dia = ahora.weekday()  # 0 lunes, 6 domingo
    hora = ahora.hour

    # Martes(1) a Domingo(6), 12 a 18
    return 1 <= dia <= 6 and 12 <= hora < 18


# =========================
# VERIFICACIÓN
# =========================
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Error", 403


# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"].lower()
        numero = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

        print("Mensaje:", mensaje)

        # =========================
        # VALIDAR HORARIO
        # =========================
        if not negocio_abierto():
            enviar_whatsapp(numero, "⏰ Estamos cerrados. Abrimos de martes a domingo de 12pm a 6pm 🙏")
            return "ok", 200

        # =========================
        # INICIAR PEDIDO
        # =========================
        if numero not in pedidos:
            pedidos[numero] = {
                "items": [],
                "nombre": "",
                "direccion": "",
                "tipo": ""
            }

        pedido = pedidos[numero]

        # =========================
        # DETECTAR PRODUCTOS
        # =========================
        agregado = False

        for producto, precio in MENU.items():
            if producto in mensaje:
                pedido["items"].append((producto, precio))
                agregado = True

        if agregado:
            enviar_whatsapp(numero, "😋 ¡Agregado! ¿Deseas ordenar algo más?")
            return "ok", 200

        # =========================
        # TIPO DE ENTREGA
        # =========================
        if "domicilio" in mensaje:
            pedido["tipo"] = "domicilio"
            enviar_whatsapp(numero, "📍 Envíame tu dirección por favor")
            return "ok", 200

        if "recoger" in mensaje or "tienda" in mensaje:
            pedido["tipo"] = "recoger"
            enviar_whatsapp(numero, "👌 Perfecto, ¿a nombre de quién será el pedido?")
            return "ok", 200

        # =========================
        # GUARDAR DIRECCIÓN
        # =========================
        if pedido["tipo"] == "domicilio" and pedido["direccion"] == "":
            pedido["direccion"] = mensaje
            enviar_whatsapp(numero, "🙌 Gracias, ¿a nombre de quién será el pedido?")
            return "ok", 200

        # =========================
        # GUARDAR NOMBRE Y FINALIZAR
        # =========================
        if pedido["nombre"] == "":
            pedido["nombre"] = mensaje

            total = sum(precio for _, precio in pedido["items"])

            detalle = "🧾 Tu pedido:\n"
            for item, precio in pedido["items"]:
                detalle += f"- {item} ${precio}\n"

            if pedido["tipo"] == "domicilio":
                total += 25
                detalle += "\n🚗 Envío: $25"

            detalle += f"\n\n💰 Total: ${total}"
            detalle += "\n\n🙏 Gracias por tu pedido"

            enviar_whatsapp(numero, detalle)

            # Reiniciar pedido
            pedidos[numero] = {
                "items": [],
                "nombre": "",
                "direccion": "",
                "tipo": ""
            }

            return "ok", 200

        # =========================
        # MENÚ SI NO ENTIENDE
        # =========================
        enviar_whatsapp(numero,
        """👋 Hola, te comparto nuestro menú:

🦪 Comida
- Orden de almejas $300
- Docena de ostiones $400
- Ceviche $200
- Ceviche de camarón $250
- Aguachile $260

🍺 Bebidas
- Cerveza $40
- Michelada $100
- Refresco $35

¿Quieres ordenar? 😄""")

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


# =========================
# ENVIAR MENSAJE
# =========================
def enviar_whatsapp(numero, mensaje):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

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
# START
# =========================
if __name__ == "__main__":
    app.run(port=10000)
