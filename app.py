from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI

app = Flask(__name__)

# =========================
# 🔑 CONFIGURACIÓN
# =========================

VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# 🧠 MEMORIA
# =========================

usuarios = {}
estado_usuario = {}

# =========================
# 🍽️ MENÚ
# =========================

menu = {
    "almeja": 300,
    "ostion": 400,
    "ceviche": 200,
    "ceviche camaron": 250,
    "aguachile": 260,
    "cerveza": 40,
    "michelada": 100,
    "refresco": 35
}

def mostrar_menu():
    texto = "📋 MENÚ:\n\n"
    for item, precio in menu.items():
        texto += f"• {item} - ${precio}\n"
    texto += "\nEjemplo: 2 almejas y 1 cerveza"
    return texto

# =========================
# 📤 ENVIAR MENSAJE
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
# 🤖 IA INTERPRETACIÓN
# =========================

def interpretar(texto):
    prompt = f"""
Eres un asistente de pedidos.

MENÚ:
almeja 300
ostion 400
ceviche 200
ceviche camaron 250
aguachile 260
cerveza 40
michelada 100
refresco 35

Responde SOLO en JSON:

1. Ver menú:
{{"accion":"ver"}}

2. Pedido:
{{"accion":"ordenar","items":[{{"producto":"almeja","cantidad":2}}]}}

3. Saludo:
{{"accion":"saludo"}}

4. Cancelar producto:
{{"accion":"cancelar","items":[{{"producto":"michelada"}}]}}

5. Otro:
{{"accion":"otro"}}

Texto: "{texto}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        contenido = response.choices[0].message.content.strip()
        return eval(contenido)

    except Exception as e:
        print("ERROR IA:", e)
        return {"accion": "otro"}

# =========================
# 🧾 PEDIDO
# =========================

def procesar_pedido(numero, items):
    if numero not in usuarios:
        usuarios[numero] = {"pedido": {}}

    for item in items:
        producto = item["producto"]
        cantidad = item["cantidad"]

        if producto in menu:
            usuarios[numero]["pedido"][producto] = \
                usuarios[numero]["pedido"].get(producto, 0) + cantidad

def cancelar_items(numero, items):
    if numero not in usuarios:
        return

    for item in items:
        producto = item["producto"]
        if producto in usuarios[numero]["pedido"]:
            del usuarios[numero]["pedido"][producto]

def generar_resumen(numero):
    pedido = usuarios[numero]["pedido"]
    texto = "🧾 Tu pedido:\n\n"
    total = 0

    for producto, cantidad in pedido.items():
        subtotal = menu[producto] * cantidad
        total += subtotal
        texto += f"{cantidad} x {producto} = ${subtotal}\n"

    texto += f"\n💰 Total: ${total}"
    return texto

# =========================
# 🌐 WEBHOOK
# =========================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if token == VERIFY_TOKEN:
            return challenge
        return "Error", 403

    data = request.json

    try:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = mensaje["from"]
        texto = mensaje["text"]["body"].lower()

        print("MENSAJE:", texto)

        # =========================
        # 🧠 FLUJOS POR ESTADO
        # =========================

        if texto in ["si", "sí"]:
            if estado_usuario.get(numero) == "esperando_menu":
                enviar(numero, mostrar_menu())
                estado_usuario[numero] = "ordenando"
                return jsonify({"status": "ok"})

        if texto in ["no", "ya", "nada"]:
            if estado_usuario.get(numero) == "ordenando":
                estado_usuario[numero] = "pidiendo_nombre"
                enviar(numero, "🧾 ¿Cuál es tu nombre?")
                return jsonify({"status": "ok"})

        if estado_usuario.get(numero) == "pidiendo_nombre":
            usuarios[numero]["nombre"] = texto
            estado_usuario[numero] = "pidiendo_direccion"
            enviar(numero, "📍 ¿Cuál es tu dirección?")
            return jsonify({"status": "ok"})

        if estado_usuario.get(numero) == "pidiendo_direccion":
            usuarios[numero]["direccion"] = texto
            estado_usuario[numero] = "pidiendo_telefono"
            enviar(numero, "📞 ¿Tu número de teléfono?")
            return jsonify({"status": "ok"})

        if estado_usuario.get(numero) == "pidiendo_telefono":
            usuarios[numero]["telefono"] = texto
            estado_usuario[numero] = "finalizado"

            resumen = generar_resumen(numero)

            enviar(numero, f"✅ Pedido confirmado\n\n{resumen}\n\n🚚 En camino")
            return jsonify({"status": "ok"})

        # =========================
        # 🤖 IA
        # =========================

        respuesta = interpretar(texto)
        accion = respuesta.get("accion")

        if accion == "saludo":
            estado_usuario[numero] = "esperando_menu"
            enviar(numero, "👋 ¡Hola! Bienvenido a Marisco Alegre 🦐\n¿Quieres ver el menú?")

        elif accion == "ver":
            enviar(numero, mostrar_menu())
            estado_usuario[numero] = "ordenando"

        elif accion == "ordenar":
            items = respuesta.get("items", [])
            procesar_pedido(numero, items)

            enviar(numero, generar_resumen(numero))
            enviar(numero, "🤖 ¿Quieres agregar algo más o modificar tu pedido?")

            estado_usuario[numero] = "ordenando"

        elif accion == "cancelar":
            items = respuesta.get("items", [])
            cancelar_items(numero, items)

            enviar(numero, "❌ Producto eliminado")
            enviar(numero, generar_resumen(numero))

        else:
            enviar(numero, "🤖 Puedes pedirme el menú o hacer un pedido.")

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"status": "ok"})


# =========================
# 🚀 INICIAR
# =========================

if __name__ == "__main__":
    app.run(debug=True)
