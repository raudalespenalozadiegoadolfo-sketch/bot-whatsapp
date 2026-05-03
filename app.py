from flask import Flask, request, jsonify, render_template
import requests
import os
import psycopg2
import json
import traceback

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
# MENÚ COMPLETO
# =========================
MENU = {
    "camarones": {
        "diabla": ("Camarones a la Diabla", 180),
        "empanizados": ("Camarones Empanizados", 190),
        "ajo": ("Camarones al Ajo", 180)
    },
    "pulpo": {
        "diabla": ("Pulpo a la Diabla", 220),
        "empanizado": ("Pulpo Empanizado", 220),
        "zarandeado": ("Pulpo Zarandeado", 220)
    },
    "filete": {
        "diabla": ("Filete a la Diabla", 160),
        "empanizado": ("Filete Empanizado", 170),
        "ajo": ("Filete al Ajo", 170)
    },
    "coctel": {
        "camaron": ("Coctel Camarón", 190),
        "pulpo": ("Coctel Pulpo", 200),
        "callo": ("Coctel Callo", 250),
        "mixto": ("Coctel Mixto", 220)
    },
    "bebidas": {
        "coca": ("Coca Cola", 30),
        "pepsi": ("Pepsi", 25)
    }
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
    INSERT INTO pedidos (cliente, telefono, direccion, total, estado, detalle)
    VALUES (%s,%s,%s,%s,%s,%s)
    RETURNING id
    """, (
        p["cliente"],
        p["telefono"],
        p["direccion"],
        p["total"],
        p["estado"],
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

    cur.execute("SELECT * FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "folio": r[0],
            "cliente": r[1],
            "telefono": r[2],
            "direccion": r[3],
            "total": r[4],
            "estado": r[5],
            "detalle": r[6]
        })

    return jsonify(data)

# =========================
# STATS (FIX)
# =========================
@app.route("/stats")
def stats():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(total),0) FROM pedidos")
    pedidos, ventas = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE estado='preparando'")
    preparando = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM pedidos WHERE estado='enviado'")
    enviados = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({
        "pedidos": pedidos,
        "ventas": ventas,
        "preparando": preparando,
        "enviados": enviados
    })

# =========================
# WHATSAPP HELPERS
# =========================
def enviar(data):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json=data)

def texto(num, msg):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "text": {"body": msg}
    })

def botones(num, texto_msg, botones_list):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": texto_msg},
            "action": {"buttons": botones_list}
        }
    })

def lista(num, titulo, secciones):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": titulo},
            "action": {
                "button": "Ver opciones",
                "sections": secciones
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

    try:
        data = request.json
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {
                "estado": "inicio",
                "items": [],
                "cerrado": False
            }

        u = usuarios[numero]

        # 🚫 SI YA DIJO GRACIAS
        if u.get("cerrado"):
            return "ok", 200

        # =========================
        # TEXTO
        # =========================
        if "text" in msg:
            texto_usuario = msg["text"]["body"].lower()

            if "gracias" in texto_usuario:
                texto(numero, "🙏 De nada, que tengas un excelente día")
                u["cerrado"] = True
                return "ok", 200

            if texto_usuario in ["hola", "menu"]:
                botones(numero, "👋 Bienvenido a Marisco Alegre 🦐\n¿Qué deseas pedir?", [
                    {"type":"reply","reply":{"id":"comida","title":"🍽 Comida"}},
                    {"type":"reply","reply":{"id":"bebidas","title":"🥤 Bebidas"}},
                    {"type":"reply","reply":{"id":"pedido","title":"🧾 Pedido"}}
                ])
                return "ok", 200

            if u["estado"] == "cantidad":
                cantidad = int(texto_usuario)
                prod = u["producto"]

                u["items"].append({
                    "nombre": prod[0],
                    "precio": prod[1],
                    "cantidad": cantidad
                })

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                resumen = "\n".join([f"• {i['nombre']} x{i['cantidad']}" for i in u["items"]])

                texto(numero, f"🧾 Tu pedido:\n{resumen}\n\n💰 Total: ${total}")

                botones(numero, "¿Qué deseas hacer?", [
                    {"type":"reply","reply":{"id":"seguir","title":"➕ Seguir"}},
                    {"type":"reply","reply":{"id":"finalizar","title":"✅ Finalizar"}},
                    {"type":"reply","reply":{"id":"vaciar","title":"🗑 Vaciar"}}
                ])

                u["estado"] = "menu"

        # =========================
        # BOTONES
        # =========================
        if "interactive" in msg:
            data = msg["interactive"]

            if data["type"] == "button_reply":
                opcion = data["button_reply"]["id"]

                if opcion == "seguir":
                    botones(numero, "¿Qué deseas agregar?", [
                        {"type":"reply","reply":{"id":"comida","title":"🍽 Comida"}},
                        {"type":"reply","reply":{"id":"bebidas","title":"🥤 Bebidas"}}
                    ])

                elif opcion == "vaciar":
                    u["items"] = []
                    texto(numero, "🗑 Pedido vaciado")

                elif opcion == "finalizar":
                    texto(numero, "👤 Ingresa tu nombre:")
                    u["estado"] = "nombre"

                elif opcion in ["comida","bebidas"]:
                    secciones = []

                    for cat in MENU:
                        if opcion == "comida" and cat == "bebidas":
                            continue
                        if opcion == "bebidas" and cat != "bebidas":
                            continue

                        secciones.append({
                            "title": cat.upper(),
                            "rows": [
                                {"id": f"{cat}|{k}", "title": v[0], "description": f"${v[1]}"}
                                for k,v in MENU[cat].items()
                            ]
                        })

                    lista(numero, "Selecciona opción", secciones)

            elif data["type"] == "list_reply":
                seleccion = data["list_reply"]["id"]

                cat, prod = seleccion.split("|")
                producto = MENU[cat][prod]

                u["producto"] = producto
                u["estado"] = "cantidad"

                texto(numero, f"¿Cuántos {producto[0]} necesitas?")

        # =========================
        # DATOS CLIENTE
        # =========================
        if "text" in msg:

            if u["estado"] == "nombre":
                u["cliente"] = msg["text"]["body"]
                texto(numero, "📍 Dirección:")
                u["estado"] = "direccion"

            elif u["estado"] == "direccion":
                u["direccion"] = msg["text"]["body"]
                texto(numero, "📞 Teléfono:")
                u["estado"] = "telefono"

            elif u["estado"] == "telefono":
                u["telefono"] = msg["text"]["body"]

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                folio = guardar_pedido({
                    "cliente": u["cliente"],
                    "telefono": u["telefono"],
                    "direccion": u["direccion"],
                    "total": total,
                    "estado": "nuevo",
                    "items": u["items"]
                })

                texto(numero, f"✅ Pedido #{folio} confirmado\n¡Gracias!")

                usuarios[numero] = {"estado":"inicio","items":[]}

    except Exception:
        print("🔥 ERROR WEBHOOK:")
        traceback.print_exc()

    return "ok", 200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
