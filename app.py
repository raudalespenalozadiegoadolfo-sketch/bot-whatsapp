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
# MENÚ
# =========================
MENU = {
    "camarones": [
        {"id": "cam_diabla", "nombre": "Camarones a la diabla", "precio": 180},
        {"id": "cam_emp", "nombre": "Camarones empanizados", "precio": 190},
        {"id": "cam_ajo", "nombre": "Camarones al ajo", "precio": 180},
    ],
    "pulpo": [
        {"id": "pul_diabla", "nombre": "Pulpo a la diabla", "precio": 220},
        {"id": "pul_emp", "nombre": "Pulpo empanizado", "precio": 220},
    ],
    "filete": [
        {"id": "filete_diabla", "nombre": "Filete a la diabla", "precio": 160},
        {"id": "filete_emp", "nombre": "Filete empanizado", "precio": 170},
    ],
    "bebidas": [
        {"id": "coca", "nombre": "Coca Cola", "precio": 30},
        {"id": "pepsi", "nombre": "Pepsi", "precio": 25},
        {"id": "agua", "nombre": "Agua fresca", "precio": 35},
    ]
}

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
        print("ERROR enviando:", e)

def enviar_mensaje(numero, texto):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# BOTONES
# =========================
def enviar_menu(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "🍽️ MENÚ\nSelecciona categoría"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "cat_camarones", "title": "🍤 Camarones"}},
                    {"type": "reply", "reply": {"id": "cat_pulpo", "title": "🐙 Pulpo"}},
                    {"type": "reply", "reply": {"id": "cat_filete", "title": "🐟 Filete"}},
                    {"type": "reply", "reply": {"id": "cat_bebidas", "title": "🥤 Bebidas"}}
                ]
            }
        }
    })

def enviar_productos(numero, categoria):
    productos = MENU[categoria]

    buttons = []
    for p in productos[:3]:  # WhatsApp permite 3 botones
        buttons.append({
            "type": "reply",
            "reply": {
                "id": f"prod_{p['id']}",
                "title": p["nombre"][:20]
            }
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"Selecciona de {categoria}"},
            "action": {"buttons": buttons}
        }
    })

def botones_cantidad(numero, producto_id):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Cuántos quieres?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": f"{producto_id}_1", "title": "1"}},
                    {"type": "reply", "reply": {"id": f"{producto_id}_2", "title": "2"}},
                    {"type": "reply", "reply": {"id": f"{producto_id}_3", "title": "3"}}
                ]
            }
        }
    })

# =========================
# CARRITO
# =========================
def agregar_producto(u, producto_id, cantidad):
    for categoria in MENU.values():
        for p in categoria:
            if p["id"] == producto_id:
                u["pedido"].append({
                    "nombre": p["nombre"],
                    "cantidad": cantidad,
                    "precio": p["precio"]
                })

def ver_pedido(numero, u):
    if not u["pedido"]:
        enviar_mensaje(numero, "🧾 Vacío")
        return

    total = 0
    texto = "🧾 TU PEDIDO\n\n"

    for item in u["pedido"]:
        subtotal = item["cantidad"] * item["precio"]
        texto += f"{item['cantidad']} x {item['nombre']} = ${subtotal}\n"
        total += subtotal

    texto += f"\n💰 Total: ${total}"

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Más"}},
                    {"type": "reply", "reply": {"id": "checkout", "title": "✅ Pagar"}},
                    {"type": "reply", "reply": {"id": "cancelar", "title": "❌ Cancelar"}}
                ]
            }
        }
    })

# =========================
# RUTAS
# =========================
@app.route("/")
def home():
    return "🔥 BOT ACTIVO"

@app.route("/panel")
def panel():
    pedidos = leer_pedidos()
    return render_template("panel.html", pedidos=pedidos)

@app.route("/crear_test")
def test():
    pedido = {
        "folio": "TEST123",
        "cliente": "Cliente prueba",
        "direccion": "Casa",
        "telefono": "000",
        "items": [],
        "total": 300,
        "estado": "nuevo"
    }
    guardar_pedido(pedido)
    return "Pedido creado"

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

        # BOTONES
        if "interactive" in mensaje:
            resp = mensaje["interactive"]["button_reply"]["id"]

            if resp.startswith("cat_"):
                categoria = resp.replace("cat_", "")
                enviar_productos(numero, categoria)
                return "ok", 200

            if resp.startswith("prod_"):
                producto_id = resp.replace("prod_", "")
                botones_cantidad(numero, producto_id)
                return "ok", 200

            if "_" in resp:
                producto_id, cantidad = resp.split("_")
                agregar_producto(u, producto_id, int(cantidad))
                enviar_mensaje(numero, "✅ Agregado")
                ver_pedido(numero, u)
                return "ok", 200

            if resp == "seguir":
                enviar_menu(numero)
                return "ok", 200

            if resp == "checkout":
                u["estado"] = "nombre"
                enviar_mensaje(numero, "🧑 Tu nombre:")
                return "ok", 200

            if resp == "cancelar":
                usuarios[numero] = {"pedido": []}
                enviar_mensaje(numero, "❌ Cancelado")
                return "ok", 200

        # TEXTO
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

            if texto in ["hola", "menu"]:
                enviar_menu(numero)
                return "ok", 200

            if u.get("estado") == "nombre":
                u["nombre"] = texto
                u["estado"] = "direccion"
                enviar_mensaje(numero, "📍 Dirección:")
                return "ok", 200

            if u.get("estado") == "direccion":
                u["direccion"] = texto

                folio = str(uuid.uuid4())[:8].upper()
                total = sum(i["cantidad"] * i["precio"] for i in u["pedido"])

                pedido = {
                    "folio": folio,
                    "cliente": u["nombre"],
                    "direccion": u["direccion"],
                    "telefono": numero,
                    "items": u["pedido"],
                    "total": total,
                    "estado": "nuevo"
                }

                guardar_pedido(pedido)

                enviar_mensaje(numero, f"🔥 Pedido #{folio} confirmado\nTotal: ${total}")

                usuarios[numero] = {"pedido": []}
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
