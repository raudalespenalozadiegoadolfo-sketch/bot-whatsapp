from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
import json
print("🔥 APP INICIANDO...")

app = Flask(__name__)

@app.route("/")
def home():
    return "Servidor activo 🔥"

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

LOGO_URL = "https://i.ibb.co/MxLwfTvY/Whats-App-Image-2026-04-09-at-6-29-58-PM.jpg"

usuarios = {}

# =========================
# BASE DE DATOS
# =========================
DB_FILE = "pedidos.json"

def guardar_pedido(pedido):
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(pedido)

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def leer_pedidos():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# =========================
# ENVIAR
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def enviar_mensaje(numero, texto):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# RUTA BASE
# =========================
@app.route("/")
def home():
    return "Servidor activo 🔥"

# =========================
# PANEL
# =========================
@app.route("/panel")
def panel():
    pedidos = leer_pedidos()
    return render_template("panel.html", pedidos=pedidos)

@app.route("/pedidos")
def obtener_pedidos():
    return jsonify(leer_pedidos())

@app.route("/estado/<folio>/<nuevo_estado>")
def cambiar_estado(folio, nuevo_estado):

    data = leer_pedidos()

    for p in data:
        if p["folio"] == folio:
            p["estado"] = nuevo_estado

            if nuevo_estado == "preparando":
                enviar_mensaje(p["telefono"], f"👨‍🍳 Tu pedido #{folio} está en preparación")

            elif nuevo_estado == "enviado":
                enviar_mensaje(p["telefono"], f"🚚 Tu pedido #{folio} va en camino")

            elif nuevo_estado == "entregado":
                enviar_mensaje(p["telefono"], f"✅ Pedido #{folio} entregado. ¡Gracias!")

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return "ok"

@app.route("/repartidor/<folio>/<nombre>")
def asignar_repartidor(folio, nombre):

    data = leer_pedidos()

    for p in data:
        if p["folio"] == folio:
            p["repartidor"] = nombre

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return "ok"

@app.route("/stats")
def stats():
    data = leer_pedidos()
    total = sum(p["total"] for p in data)
    pedidos = len(data)

    return {"ventas": total, "pedidos": pedidos}

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": [], "bienvenida": False}

        u = usuarios[numero]

        # =========================
        # TEXTO
        # =========================
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

            # 🔥 MENÚ PRINCIPAL
            if texto in ["hola", "menu", "inicio"]:
                enviar_mensaje(numero,
                    "👋 Bienvenido a Marisco Alegre 🦐\n\n"
                    "Escribe:\n"
                    "1️⃣ Comida\n"
                    "2️⃣ Bebidas\n"
                    "3️⃣ Ver pedido"
                )
                return "ok", 200

            # 🔥 RESPUESTAS
            if texto == "1":
                enviar_mensaje(numero,
                    "🍽️ Menú de comida:\n"
                    "- Camarones\n- Pulpo\n- Filete\n- Cortes"
                )
                return "ok", 200

            if texto == "2":
                enviar_mensaje(numero,
                    "🍹 Menú de bebidas:\n"
                    "- Refrescos\n- Aguas\n- Micheladas\n- Cervezas"
                )
                return "ok", 200

            if texto == "3":
                if not u["pedido"]:
                    enviar_mensaje(numero, "🧾 Tu pedido está vacío")
                else:
                    texto_pedido = "🧾 Tu pedido:\n"
                    total = 0
                    for item in u["pedido"]:
                        subtotal = item["cantidad"] * item["precio"]
                        texto_pedido += f"• {item['cantidad']} {item['nombre']} - ${subtotal}\n"
                        total += subtotal
                    texto_pedido += f"\n💰 Total: ${total}"
                    enviar_mensaje(numero, texto_pedido)
                return "ok", 200

            # =========================
            # FINALIZAR PEDIDO
            # =========================
            if u.get("estado") == "telefono":
                u["telefono"] = texto

                folio = str(uuid.uuid4())[:8].upper()

                total = 0
                for item in u["pedido"]:
                    total += item["cantidad"] * item["precio"]

                pedido_data = {
                    "folio": folio,
                    "cliente": u.get("nombre",""),
                    "direccion": u.get("direccion",""),
                    "telefono": u.get("telefono",""),
                    "items": u["pedido"],
                    "total": total,
                    "estado": "nuevo",
                    "repartidor": "Sin asignar"
                }

                guardar_pedido(pedido_data)

                enviar_mensaje(numero, f"✅ Pedido #{folio} confirmado\n💰 Total: ${total}")

                usuarios[numero] = {"pedido": [], "bienvenida": True}
                return "ok", 200

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
