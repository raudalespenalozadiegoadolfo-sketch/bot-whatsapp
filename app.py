from flask import Flask, request, jsonify
import requests
import os
import uuid

app = Flask(__name__)

# =========================
# VARIABLES (CORREGIDO)
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")

usuarios = {}

# =========================
# MENÚ COMPLETO
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
    "ceviches": {
        "Ceviche de Pescado": 180,
        "Ceviche de Camarón": 200
    },
    "aguachiles": {
        "Aguachile Verde": 190,
        "Aguachile Negro": 190,
        "Aguachile Rojo": 190
    },
    "bebidas": {
        "Coca Cola 600ml": 30,
        "Pepsi 600ml": 25,
        "7UP 600ml": 25,
        "Manzana 600ml": 25,
        "Sprite 600ml": 30
    }
}

# =========================
# ENVIAR MENSAJE
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

# =========================
# MENÚ PRINCIPAL
# =========================
def menu_principal(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐\n\n¿Qué deseas pedir?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽️ Comida"}},
                    {"type": "reply", "reply": {"id": "bebidas", "title": "🍹 Bebidas"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    })

# =========================
# MOSTRAR CATEGORÍAS
# =========================
def mostrar_categorias(numero):
    rows = []
    for cat in menu:
        if cat != "bebidas":
            rows.append({"id": cat, "title": cat.capitalize()})

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona categoría"},
            "action": {"button": "Ver opciones", "sections": [{"title": "Menú", "rows": rows}]}
        }
    })

# =========================
# MOSTRAR PRODUCTOS
# =========================
def mostrar_productos(numero, categoria):
    items = menu[categoria]
    rows = []

    for nombre, precio in items.items():
        rows.append({
            "id": f"prod_{nombre}",
            "title": nombre,
            "description": f"${precio}"
        })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": categoria.upper()},
            "action": {"button": "Ver opciones", "sections": [{"title": "Productos", "rows": rows}]}
        }
    })

# =========================
# MOSTRAR PEDIDO
# =========================
def mostrar_pedido(numero, u):
    if not u["pedido"]:
        texto = "🧾 Tu pedido está vacío"
    else:
        texto = "🧾 Tu pedido:\n\n"
        total = 0
        for item in u["pedido"]:
            subtotal = item["cantidad"] * item["precio"]
            texto += f"• {item['cantidad']} {item['nombre']} - ${subtotal}\n"
            total += subtotal
        texto += f"\n💰 Total: ${total}"

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# BOTONES CARRITO
# =========================
def acciones(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas hacer?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Seguir"}},
                    {"type": "reply", "reply": {"id": "finalizar", "title": "✅ Finalizar"}},
                    {"type": "reply", "reply": {"id": "vaciar", "title": "🗑️ Vaciar"}}
                ]
            }
        }
    })

# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # VERIFICACIÓN
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # 🔥 CORRECCIÓN CLAVE
        if "messages" not in value:
            return "ok", 200

        mensaje = value["messages"][0]
        numero = mensaje["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": []}

        u = usuarios[numero]

        # =========================
        # TEXTO
        # =========================
        if "text" in mensaje:
            texto = mensaje["text"]["body"].lower()

            # MENÚ AUTOMÁTICO
            if texto in ["hola", "menu", "inicio"]:
                menu_principal(numero)
                return "ok", 200

            # CANTIDAD
            if u.get("esperando_cantidad"):
                cantidad = int(texto)

                nombre = u["producto"]["nombre"]
                precio = u["producto"]["precio"]

                u["pedido"].append({
                    "nombre": nombre,
                    "precio": precio,
                    "cantidad": cantidad
                })

                u["esperando_cantidad"] = False

                enviar({
                    "messaging_product": "whatsapp",
                    "to": numero,
                    "text": {"body": f"✅ {cantidad} {nombre} agregado"}
                })

                mostrar_pedido(numero, u)
                acciones(numero)
                return "ok", 200

            # DATOS CLIENTE
            if u.get("estado") == "nombre":
                u["nombre"] = texto
                u["estado"] = "direccion"
                enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "📍 Dirección:"}})
                return "ok", 200

            if u.get("estado") == "direccion":
                u["direccion"] = texto
                u["estado"] = "telefono"
                enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "📞 Teléfono:"}})
                return "ok", 200

            if u.get("estado") == "telefono":
                u["telefono"] = texto

                orden = str(uuid.uuid4())[:8]

                resumen = f"🧾 Orden #{orden}\n\n"
                total = 0

                for item in u["pedido"]:
                    subtotal = item["cantidad"] * item["precio"]
                    resumen += f"{item['cantidad']} {item['nombre']} - ${subtotal}\n"
                    total += subtotal

                resumen += f"\nTotal: ${total}\n\n"
                resumen += f"👤 {u['nombre']}\n📍 {u['direccion']}\n📞 {u['telefono']}"

                enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": resumen}})
                enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "🙏 Gracias por su preferencia"}})

                usuarios[numero] = {"pedido": []}
                return "ok", 200

        # =========================
        # INTERACTIVOS
        # =========================
        if "interactive" in mensaje:
            inter = mensaje["interactive"]

            if inter["type"] == "button_reply":
                id = inter["button_reply"]["id"]

                if id == "comida":
                    mostrar_categorias(numero)

                elif id == "bebidas":
                    mostrar_productos(numero, "bebidas")

                elif id == "pedido":
                    mostrar_pedido(numero, u)

                elif id == "seguir":
                    menu_principal(numero)

                elif id == "vaciar":
                    u["pedido"] = []
                    enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "🗑️ Carrito vacío"}})
                    menu_principal(numero)

                elif id == "finalizar":
                    u["estado"] = "nombre"
                    enviar({"messaging_product": "whatsapp","to": numero,"text": {"body": "👤 Nombre del cliente:"}})

            elif inter["type"] == "list_reply":
                id = inter["list_reply"]["id"]

                if id in menu:
                    mostrar_productos(numero, id)

                elif id.startswith("prod_"):
                    nombre = id.replace("prod_", "")

                    for cat in menu:
                        if nombre in menu[cat]:
                            precio = menu[cat][nombre]

                    u["producto"] = {"nombre": nombre, "precio": precio}
                    u["esperando_cantidad"] = True

                    enviar({
                        "messaging_product": "whatsapp",
                        "to": numero,
                        "text": {"body": f"¿Cuántos {nombre} necesitas?"}
                    })

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200


if __name__ == "__main__":
    app.run(port=5000)
