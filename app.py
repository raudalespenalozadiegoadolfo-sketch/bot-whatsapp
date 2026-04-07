from flask import Flask, request, jsonify
import requests
import os
import json
import re
from openai import OpenAI

app = Flask(__name__)

# =========================
# 🔑 CONFIG
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

# =========================
# 📋 MENU TEXTO
# =========================

def mostrar_menu():
    texto = "📋 MENÚ:\n\n"
    for item, precio in menu.items():
        texto += f"• {item} - ${precio}\n"
    texto += "\nEjemplo: 2 almejas y 1 cerveza"
    return texto

# =========================
# 📤 ENVIAR
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
# 🤖 IA (solo intención)
# =========================

def interpretar(texto):
    prompt = f"""
Clasifica la intención del usuario.

Responde SOLO JSON:

{{"accion":"saludo"}}
{{"accion":"ver_menu"}}
{{"accion":"orden"}}
{{"accion":"cancelar"}}
{{"accion":"finalizar"}}
{{"accion":"otro"}}

Texto: "{texto}"
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        contenido = res.choices[0].message.content.strip()
        contenido = contenido.replace("json", "").replace("", "").strip()

        return json.loads(contenido)

    except:
        return {"accion": "otro"}

# =========================
# ⚙️ PARSEAR PEDIDO (SIN IA)
# =========================

def extraer_items(texto):
    items = []
    for producto in menu.keys():
        pattern = rf"(\\d+)\\s*{producto}"
        match = re.findall(pattern, texto)
        for m in match:
            items.append({
                "producto": producto,
                "cantidad": int(m)
            })
    return items

# =========================
# 🧾 PEDIDO
# =========================

def procesar_pedido(numero, items):
    if numero not in usuarios:
        usuarios[numero] = {"pedido": {}}

    for item in items:
        p = item["producto"]
        c = item["cantidad"]

        usuarios[numero]["pedido"][p] = \
            usuarios[numero]["pedido"].get(p, 0) + c

def cancelar_item(numero, texto):
    for producto in menu.keys():
        if producto in texto:
            usuarios[numero]["pedido"].pop(producto, None)

def resumen(numero):
    pedido = usuarios[numero]["pedido"]
    if not pedido:
        return "🧾 No tienes pedido aún."

    texto = "🧾 Tu pedido:\n\n"
    total = 0

    for p, c in pedido.items():
        sub = menu[p] * c
        total += sub
        texto += f"{c} x {p} = ${sub}\n"

    texto += f"\n💰 Total: ${total}"
    return texto

# =========================
# 🌐 WEBHOOK
# =========================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.json

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        numero = msg["from"]
        texto = msg["text"]["body"].lower()

        print("MSG:", texto)

        # =========================
        # FLUJOS ESTADO
        # =========================

        if texto in ["si", "sí"] and estado_usuario.get(numero) == "menu":
            enviar(numero, mostrar_menu())
            estado_usuario[numero] = "ordenando"
            return jsonify({"ok": True})

        if texto in ["no", "ya"] and estado_usuario.get(numero) == "ordenando":
            estado_usuario[numero] = "nombre"
            enviar(numero, "🧾 ¿Nombre?")
            return jsonify({"ok": True})

        if estado_usuario.get(numero) == "nombre":
            usuarios[numero]["nombre"] = texto
            estado_usuario[numero] = "direccion"
            enviar(numero, "📍 Dirección?")
            return jsonify({"ok": True})

        if estado_usuario.get(numero) == "direccion":
            usuarios[numero]["direccion"] = texto
            estado_usuario[numero] = "telefono"
            enviar(numero, "📞 Teléfono?")
            return jsonify({"ok": True})

        if estado_usuario.get(numero) == "telefono":
            usuarios[numero]["telefono"] = texto
            estado_usuario[numero] = "final"

            enviar(numero, "✅ Pedido confirmado\n\n" + resumen(numero))
            return jsonify({"ok": True})

        # =========================
        # IA + LOGICA
        # =========================

        accion = interpretar(texto)["accion"]

        # SALUDO
        if accion == "saludo":
            estado_usuario[numero] = "menu"
            enviar(numero, "👋 Bienvenido a Marisco Alegre 🦐\n¿Quieres ver el menú?")

        # VER MENU
        elif accion == "ver_menu":
            enviar(numero, mostrar_menu())
            estado_usuario[numero] = "ordenando"

        # ORDEN
        elif accion == "orden":
            items = extraer_items(texto)

            if items:
                procesar_pedido(numero, items)
                enviar(numero, resumen(numero))
                enviar(numero, "🤖 ¿Agregar algo más o finalizar?")
                estado_usuario[numero] = "ordenando"
            else:
                enviar(numero, "🤖 No entendí el pedido, intenta como:\n2 almejas y 1 cerveza")

        # CANCELAR
        elif accion == "cancelar":
            cancelar_item(numero, texto)
            enviar(numero, "❌ Producto eliminado")
            enviar(numero, resumen(numero))

        # FINALIZAR
        elif accion == "finalizar":
            estado_usuario[numero] = "nombre"
            enviar(numero, "🧾 ¿Nombre para el pedido?")

        else:
            enviar(numero, "🤖 Puedes pedirme el menú o hacer un pedido")

    except Exception as e:
        print("ERROR:", e)

    return jsonify({"ok": True})


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)
