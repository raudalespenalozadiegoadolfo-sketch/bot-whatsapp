from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
import json

app = Flask(__name__)

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

LOGO_URL = "https://i.ibb.co/MxLwfTvY/Whats-App-Image-2026-04-09-at-6-29-58-PM.jpg"

usuarios = {}

# =========================
# 🔥 BASE DE DATOS
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

# 🔥 NUEVO (IMPORTANTE)
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
# 🔥 PANEL
# =========================
@app.route("/panel")
def panel():
    pedidos = leer_pedidos()  # 🔥 AQUÍ ESTABA EL ERROR
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

            # 🔥 MENSAJES AUTOMÁTICOS
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
# =========================
# 🔥 TU CÓDIGO ORIGINAL (NO MODIFICADO)
# =========================
# =========================

menu = {
    "camarones": {
        "Camarones a la Diabla": 180,
        "Camarones Empanizados": 190,
        "Camarones al Ajo": 180,
        "Camarones al Ajillo": 180
    },
    "pulpo": {
        "Pulpo a la Diabla": 220,
        "Pulpo Empanizado": 220,
        "Pulpo Zarandeado": 220
    },
    "filete": {
        "Filete a la Diabla": 160,
        "Filete Empanizado": 170,
        "Filete al Ajo": 170
    },
    "cortes": {
        "Arrachera": 220,
        "T-Bone": 250,
        "Rib Eye": 270
    },
    "bebidas": {
        "refrescos": {
            "Coca Cola 600ml": 30,
            "Coca Cola Light 600ml": 30,
            "Pepsi 600ml": 25,
            "Sangría 600ml": 25,
            "7UP 600ml": 25
        },
        "aguas1L": {
            "Agua Horchata 1L": 35,
            "Agua Jamaica 1L": 35,
            "Agua Piña 1L": 35,
            "Agua Limón 1L": 35
        },
        "aguas500": {
            "Agua Horchata 500ml": 20,
            "Agua Jamaica 500ml": 20,
            "Agua Piña 500ml": 20,
            "Agua Limón 500ml": 20
        },
        "micheladas": {
            "Michelada Camarón 1L": 100,
            "Michelada Clamato 1L": 80,
            "Michelada Tamarindo 1L": 90
        },
        "cervezas": {
            "Corona Extra": 40,
            "Corona Light": 40,
            "Corona Cero": 40,
            "Tecate": 35,
            "Tecate Light": 35,
            "Indio": 30,
            "Ultra": 30,
            "Heineken 0.0": 35
        }
    }
}

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

        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

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

                resumen = f"🧾 Pedido #{folio}\n\n"
                for item in u["pedido"]:
                    subtotal = item["cantidad"] * item["precio"]
                    resumen += f"• {item['cantidad']} {item['nombre']} - ${subtotal}\n"

                resumen += f"\n💰 Total: ${total}\n\n"
                resumen += f"👤 {u.get('nombre','')}\n📍 {u.get('direccion','')}\n📞 {u.get('telefono','')}"

                enviar_mensaje(numero, resumen)
                enviar_mensaje(numero, "✅ Pedido confirmado. ¡Gracias!")

                usuarios[numero] = {"pedido": [], "bienvenida": True}
                return "ok", 200

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000)
