from flask import Flask, request, jsonify, render_template
import requests
import os
import psycopg2
import json

app = Flask(__name__)

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

usuarios = {}

# =========================
# MENU + CATEGORIAS
# =========================
MENU = {
    "camarones_diabla": {"nombre": "Camarones Diabla", "precio": 180, "cat": "camarones"},
    "camarones_empanizados": {"nombre": "Camarones Empanizados", "precio": 190, "cat": "camarones"},
    "camarones_ajo": {"nombre": "Camarones al Ajo", "precio": 180, "cat": "camarones"},

    "pulpo_diabla": {"nombre": "Pulpo Diabla", "precio": 220, "cat": "pulpo"},

    "filete_diabla": {"nombre": "Filete Diabla", "precio": 160, "cat": "filete"},

    "coctel_camaron": {"nombre": "Coctel Camarón", "precio": 190, "cat": "coctel"},

    "coca": {"nombre": "Coca Cola", "precio": 30, "cat": "bebidas"},
    "pepsi": {"nombre": "Pepsi", "precio": 25, "cat": "bebidas"}
}

# =========================
# DB
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id SERIAL PRIMARY KEY,
        cliente TEXT,
        telefono TEXT,
        direccion TEXT,
        total INT,
        estado TEXT DEFAULT 'nuevo',
        repartidor TEXT DEFAULT 'sin asignar',
        detalle JSON
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

# =========================
# GUARDAR PEDIDO
# =========================
def guardar_pedido(p):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO pedidos (cliente, telefono, direccion, total, estado, repartidor, detalle)
    VALUES (%s,%s,%s,%s,%s,%s,%s)
    RETURNING id
    """, (
        p["cliente"],
        p["telefono"],
        p["direccion"],
        p["total"],
        p["estado"],
        p["repartidor"],
        json.dumps(p["items"])
    ))

    folio = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return folio

# =========================
# UTILIDADES
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def enviar_texto(numero, texto):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# MENUS
# =========================
def menu_inicio(numero):
    enviar_texto(numero, "👋 Bienvenido a *Marisco Alegre* 🦐\n\n¿Qué deseas pedir?")

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona una opción"},
            "action": {
                "buttons": [
                    {"type":"reply","reply":{"id":"comida","title":"🍽 Comida"}},
                    {"type":"reply","reply":{"id":"bebidas","title":"🥤 Bebidas"}},
                    {"type":"reply","reply":{"id":"pedido","title":"🧾 Pedido"}}
                ]
            }
        }
    })

def menu_categorias(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona categoría"},
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Categorías",
                        "rows": [
                            {"id":"camarones","title":"Camarones"},
                            {"id":"pulpo","title":"Pulpo"},
                            {"id":"filete","title":"Filete"},
                            {"id":"coctel","title":"Cocteles"}
                        ]
                    }
                ]
            }
        }
    })

def menu_productos(numero, categoria):
    rows = []
    for k,v in MENU.items():
        if v["cat"] == categoria:
            rows.append({
                "id": k,
                "title": v["nombre"],
                "description": f"${v['precio']}"
            })

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": categoria.upper()},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title":"Productos","rows":rows}]
            }
        }
    })

def resumen(numero, u):
    total = sum(i["precio"] * i["cantidad"] for i in u["items"])

    texto = "🧾 Tu pedido:\n\n"
    for i in u["items"]:
        texto += f"• {i['cantidad']} {i['nombre']} - ${i['precio']*i['cantidad']}\n"

    texto += f"\n💰 Total: ${total}"

    enviar_texto(numero, texto)

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas hacer?"},
            "action": {
                "buttons": [
                    {"type":"reply","reply":{"id":"seguir","title":"➕ Seguir"}},
                    {"type":"reply","reply":{"id":"finalizar","title":"✅ Finalizar"}},
                    {"type":"reply","reply":{"id":"vaciar","title":"🗑 Vaciar"}}
                ]
            }
        }
    })

# =========================
# WEBHOOK PRO
# =========================
@app.route("/webhook", methods=["GET","POST"])
def webhook():

    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "error", 403

    data = request.json

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"paso":"inicio","items":[]}

        u = usuarios[numero]

        # =========================
        # BOTONES
        # =========================
        if "interactive" in msg:

            if "button_reply" in msg["interactive"]:
                accion = msg["interactive"]["button_reply"]["id"]

                if accion == "comida":
                    u["paso"] = "categoria"
                    menu_categorias(numero)

                elif accion == "bebidas":
                    u["paso"] = "producto"
                    menu_productos(numero, "bebidas")

                elif accion == "pedido":
                    resumen(numero, u)

                elif accion == "seguir":
                    u["paso"] = "inicio"
                    menu_inicio(numero)

                elif accion == "vaciar":
                    u["items"] = []
                    enviar_texto(numero, "🗑 Pedido vaciado")
                    menu_inicio(numero)

                elif accion == "finalizar":

                    total = sum(i["precio"] * i["cantidad"] for i in u["items"])

                    folio = guardar_pedido({
                        "cliente": "Cliente",
                        "telefono": numero,
                        "direccion": "",
                        "total": total,
                        "estado": "nuevo",
                        "repartidor": "sin asignar",
                        "items": u["items"]
                    })

                    enviar_texto(numero, f"✅ Pedido #{folio} confirmado\n¡Gracias!")

                    usuarios[numero] = {"paso":"inicio","items":[]}

            elif "list_reply" in msg["interactive"]:
                seleccion = msg["interactive"]["list_reply"]["id"]

                if u["paso"] == "categoria":
                    u["categoria"] = seleccion
                    u["paso"] = "producto"
                    menu_productos(numero, seleccion)

                elif u["paso"] == "producto":
                    u["producto_temp"] = MENU[seleccion]
                    u["paso"] = "cantidad"
                    enviar_texto(numero, f"¿Cuántos {MENU[seleccion]['nombre']} necesitas?")

        # =========================
        # TEXTO
        # =========================
        if "text" in msg:
            texto = msg["text"]["body"].lower()

            if texto in ["hola","menu"]:
                menu_inicio(numero)

            elif u["paso"] == "cantidad":

                cantidad = int(texto)
                p = u["producto_temp"]

                u["items"].append({
                    "nombre": p["nombre"],
                    "precio": p["precio"],
                    "cantidad": cantidad
                })

                enviar_texto(numero, f"✅ {cantidad} {p['nombre']} agregado")

                u["paso"] = "resumen"
                resumen(numero, u)

    except Exception as e:
        print("ERROR:", e)

    return "ok", 200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
