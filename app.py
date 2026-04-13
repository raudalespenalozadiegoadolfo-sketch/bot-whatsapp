from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
import json

app = Flask(__name__)

print("🔥 APP INICIANDO...")

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

DB_FILE = "pedidos.json"
usuarios = {}

# =========================
# BASE DE DATOS
# =========================
def asegurar_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)

def guardar_pedido(pedido):
    asegurar_db()
    with open(DB_FILE, "r") as f:
        data = json.load(f)

    data.append(pedido)

    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def leer_pedidos():
    asegurar_db()
    with open(DB_FILE, "r") as f:
        return json.load(f)

# =========================
# ENVIAR WHATSAPP
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print("❌ ERROR enviando:", e)

def enviar_mensaje(numero, texto):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# RUTAS WEB
# =========================
@app.route("/")
def home():
    return "🔥 Servidor activo"

@app.route("/test")
def test():
    return "OK"

# =========================
# PANEL
# =========================
@app.route("/panel")
def panel():
    try:
        pedidos = leer_pedidos()
        return render_template("panel.html", pedidos=pedidos)
    except Exception as e:
        return f"❌ Error panel: {e}"

@app.route("/pedidos")
def obtener_pedidos():
    return jsonify(leer_pedidos())

# 🔥 CREAR PEDIDO DE PRUEBA
@app.route("/crear_test")
def crear_test():
    pedido = {
        "folio": str(uuid.uuid4())[:8].upper(),
        "cliente": "Cliente prueba",
        "direccion": "Dirección demo",
        "telefono": "0000000000",
        "items": [{"nombre": "Camarones", "cantidad": 2, "precio": 150}],
        "total": 300,
        "estado": "nuevo",
        "repartidor": "Sin asignar"
    }
    guardar_pedido(pedido)
    return "✅ Pedido de prueba creado"

@app.route("/estado/<folio>/<nuevo_estado>")
def cambiar_estado(folio, nuevo_estado):
    data = leer_pedidos()

    for p in data:
        if p["folio"] == folio:
            p["estado"] = nuevo_estado

            if nuevo_estado == "preparando":
                enviar_mensaje(p["telefono"], f"👨‍🍳 Pedido #{folio} en preparación")

            elif nuevo_estado == "enviado":
                enviar_mensaje(p["telefono"], f"🚚 Pedido #{folio} en camino")

            elif nuevo_estado == "entregado":
                enviar_mensaje(p["telefono"], f"✅ Pedido #{folio} entregado")

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
            usuarios[numero] = {"pedido": []}

        u = usuarios[numero]

        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

            # MENÚ
            if texto in ["hola", "menu", "inicio"]:
                enviar_mensaje(numero,
                    "👋 Bienvenido a Marisco Alegre 🦐\n\n"
                    "1️⃣ Comida\n2️⃣ Bebidas\n3️⃣ Ver pedido\n4️⃣ Confirmar"
                )
                return "ok", 200

            # AGREGAR PRODUCTOS (DEMO)
            if texto == "1":
                item = {"nombre": "Camarones", "cantidad": 1, "precio": 150}
                u["pedido"].append(item)
                enviar_mensaje(numero, "🦐 Camarones agregados al pedido")
                return "ok", 200

            if texto == "2":
                item = {"nombre": "Refresco", "cantidad": 1, "precio": 30}
                u["pedido"].append(item)
                enviar_mensaje(numero, "🥤 Refresco agregado al pedido")
                return "ok", 200

            # VER PEDIDO
            if texto == "3":
                if not u["pedido"]:
                    enviar_mensaje(numero, "🧾 Pedido vacío")
                else:
                    total = sum(i["cantidad"] * i["precio"] for i in u["pedido"])
                    enviar_mensaje(numero, f"🧾 Total: ${total}")
                return "ok", 200

            # CONFIRMAR
            if texto == "4":
                if not u["pedido"]:
                    enviar_mensaje(numero, "❌ No hay productos")
                    return "ok", 200

                folio = str(uuid.uuid4())[:8].upper()
                total = sum(i["cantidad"] * i["precio"] for i in u["pedido"])

                pedido = {
                    "folio": folio,
                    "cliente": "WhatsApp",
                    "direccion": "Pendiente",
                    "telefono": numero,
                    "items": u["pedido"],
                    "total": total,
                    "estado": "nuevo",
                    "repartidor": "Sin asignar"
                }

                guardar_pedido(pedido)

                enviar_mensaje(numero, f"✅ Pedido #{folio} confirmado\n💰 ${total}")

                usuarios[numero] = {"pedido": []}
                return "ok", 200

    except Exception as e:
        print("❌ ERROR:", e)

    return "ok", 200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
