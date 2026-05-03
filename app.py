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
# MENU REAL
# =========================
MENU = {
    # CAMARONES
    "cam_diabla": {"nombre": "Camarones a la Diabla", "precio": 180, "cat": "camarones"},
    "cam_emp": {"nombre": "Camarones Empanizados", "precio": 190, "cat": "camarones"},
    "cam_ajo": {"nombre": "Camarones al Ajo", "precio": 180, "cat": "camarones"},

    # PULPO
    "pulpo_diabla": {"nombre": "Pulpo a la Diabla", "precio": 220, "cat": "pulpo"},
    "pulpo_emp": {"nombre": "Pulpo Empanizado", "precio": 220, "cat": "pulpo"},
    "pulpo_zar": {"nombre": "Pulpo Zarandeado", "precio": 220, "cat": "pulpo"},

    # FILETE
    "filete_diabla": {"nombre": "Filete a la Diabla", "precio": 160, "cat": "filete"},
    "filete_emp": {"nombre": "Filete Empanizado", "precio": 170, "cat": "filete"},
    "filete_ajo": {"nombre": "Filete al Ajo", "precio": 170, "cat": "filete"},

    # COCTEL
    "coctel_cam": {"nombre": "Coctel Camarón", "precio": 190, "cat": "coctel"},
    "coctel_pulpo": {"nombre": "Coctel Pulpo", "precio": 200, "cat": "coctel"},
    "coctel_callo": {"nombre": "Coctel Callo", "precio": 250, "cat": "coctel"},
    "coctel_mixto": {"nombre": "Coctel Mixto", "precio": 220, "cat": "coctel"},

    # BEBIDAS
    "coca": {"nombre": "Coca Cola", "precio": 30, "cat": "bebidas"},
    "pepsi": {"nombre": "Pepsi", "precio": 25, "cat": "bebidas"},
    "sangria": {"nombre": "Sangría", "precio": 25, "cat": "bebidas"},
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
# GUARDAR
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
        "nuevo",
        "sin asignar",
        json.dumps(p["items"])
    ))

    folio = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return folio

# =========================
# PANEL
# =========================
@app.route("/panel")
def panel():
    return render_template("panel.html")

@app.route("/pedidos")
def pedidos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, cliente, telefono, direccion, total, estado, detalle FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            "folio": r[0],
            "cliente": r[1],
            "telefono": r[2],
            "direccion": r[3],
            "total": r[4],
            "estado": r[5],
            "detalle": r[6]
        } for r in rows
    ])

@app.route("/estado/<folio>/<estado>")
def estado(folio, estado):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (estado, folio))

    conn.commit()
    cur.close()
    conn.close()

    return "ok"

# =========================
# WHATSAPP ENVIO
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def texto(num, t):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "text": {"body": t}
    })

# =========================
# MENUS
# =========================
def menu_inicio(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐\n\n¿Qué deseas pedir?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "comida", "title": "🍽 Comida"}},
                    {"type": "reply", "reply": {"id": "bebidas", "title": "🥤 Bebidas"}},
                    {"type": "reply", "reply": {"id": "pedido", "title": "🧾 Pedido"}}
                ]
            }
        }
    })

def menu_categorias(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona categoría"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "camarones", "title": "Camarones"}},
                    {"type": "reply", "reply": {"id": "pulpo", "title": "Pulpo"}},
                    {"type": "reply", "reply": {"id": "filete", "title": "Filete"}}
                ]
            }
        }
    })

def menu_productos(num, cat):
    rows = [
        {"id": k, "title": v["nombre"], "description": f"${v['precio']}"}
        for k, v in MENU.items() if v["cat"] == cat
    ]

    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": cat.upper()},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Menú", "rows": rows}]
            }
        }
    })

def menu_acciones(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas hacer?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "seguir", "title": "➕ Seguir"}},
                    {"type": "reply", "reply": {"id": "finalizar", "title": "✅ Finalizar"}},
                    {"type": "reply", "reply": {"id": "vaciar", "title": "🗑 Vaciar"}}
                ]
            }
        }
    })

# =========================
# WEBHOOK
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
        num = msg["from"]

        if num not in usuarios:
            usuarios[num] = {"paso": "inicio", "items": []}

        u = usuarios[num]

        # ========= INTERACTIVE =========
        if "interactive" in msg:

            if "list_reply" in msg["interactive"]:
                seleccion = msg["interactive"]["list_reply"]["id"]
            else:
                seleccion = msg["interactive"]["button_reply"]["id"]

            # PRODUCTO
            if seleccion in MENU:
                p = MENU[seleccion]

                u["temp"] = p
                u["paso"] = "cantidad"

                texto(num, f"¿Cuántos {p['nombre']} necesitas?")

            # FLUJO
            elif seleccion == "comida":
                menu_categorias(num)

            elif seleccion in ["camarones","pulpo","filete"]:
                menu_productos(num, seleccion)

            elif seleccion == "bebidas":
                menu_productos(num, "bebidas")

            elif seleccion == "seguir":
                menu_inicio(num)

            elif seleccion == "vaciar":
                u["items"] = []
                texto(num, "🗑 Pedido vaciado")
                menu_inicio(num)

            elif seleccion == "finalizar":
                u["paso"] = "nombre"
                texto(num, "👤 Ingresa tu nombre:")

        # ========= TEXTO =========
        if "text" in msg:

            t = msg["text"]["body"]

            if u["paso"] == "cantidad":
                cant = int(t)

                p = u["temp"]

                u["items"].append({
                    "nombre": p["nombre"],
                    "precio": p["precio"],
                    "cantidad": cant
                })

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                resumen = "\n".join([f"{i['cantidad']} {i['nombre']}" for i in u["items"]])

                texto(num, f"✅ Agregado\n\n{resumen}\n\n💰 Total: ${total}")

                u["paso"] = "inicio"
                menu_acciones(num)

            elif u["paso"] == "nombre":
                u["nombre"] = t
                u["paso"] = "direccion"
                texto(num, "📍 Dirección:")

            elif u["paso"] == "direccion":
                u["direccion"] = t
                u["paso"] = "telefono"
                texto(num, "📞 Teléfono:")

            elif u["paso"] == "telefono":

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                folio = guardar_pedido({
                    "cliente": u["nombre"],
                    "telefono": t,
                    "direccion": u["direccion"],
                    "total": total,
                    "items": u["items"]
                })

                texto(num, f"✅ Pedido #{folio} confirmado\n\nGracias por tu compra 🙌")

                usuarios[num] = {"paso": "inicio", "items": []}

            else:
                menu_inicio(num)

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
