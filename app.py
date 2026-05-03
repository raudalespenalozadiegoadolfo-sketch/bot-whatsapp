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
# MENU COMPLETO
# =========================
MENU = {
    "camarones_diabla": {"nombre": "Camarones Diabla", "precio": 180},
    "camarones_empanizados": {"nombre": "Camarones Empanizados", "precio": 190},
    "camarones_ajo": {"nombre": "Camarones al Ajo", "precio": 180},

    "pulpo_diabla": {"nombre": "Pulpo Diabla", "precio": 220},
    "pulpo_empanizado": {"nombre": "Pulpo Empanizado", "precio": 220},

    "filete_diabla": {"nombre": "Filete Diabla", "precio": 160},
    "filete_empanizado": {"nombre": "Filete Empanizado", "precio": 170},

    "coctel_camaron": {"nombre": "Coctel Camarón", "precio": 190},
    "coctel_pulpo": {"nombre": "Coctel Pulpo", "precio": 200},

    "coca": {"nombre": "Coca Cola", "precio": 30},
    "pepsi": {"nombre": "Pepsi", "precio": 25}
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
# OBTENER PEDIDOS
# =========================
def obtener_pedidos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, cliente, telefono, direccion, total, estado, detalle
    FROM pedidos
    ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "folio": r[0],
            "cliente": r[1],
            "telefono": r[2],
            "direccion": r[3],
            "total": r[4],
            "estado": r[5],
            "detalle": r[6] or []
        }
        for r in rows
    ]

# =========================
# STATS
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
# PANEL
# =========================
@app.route("/panel")
def panel():
    return render_template("panel.html")

@app.route("/pedidos")
def pedidos():
    return jsonify(obtener_pedidos())

# =========================
# ESTADO PEDIDO
# =========================
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
# ENVIO WHATSAPP
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
# MENU WHATSAPP
# =========================
def enviar_menu(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🍽️ Menú disponible"},
            "action": {
                "button": "Ver menú",
                "sections": [
                    {
                        "title": "Comida",
                        "rows": [
                            {"id": k, "title": v["nombre"], "description": f"${v['precio']}"}
                            for k, v in MENU.items() if v["precio"] > 50
                        ]
                    },
                    {
                        "title": "Bebidas",
                        "rows": [
                            {"id": k, "title": v["nombre"], "description": f"${v['precio']}"}
                            for k, v in MENU.items() if v["precio"] <= 50
                        ]
                    }
                ]
            }
        }
    })

# =========================
# WEBHOOK PRO 🔥
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
            usuarios[numero] = {
                "paso": "inicio",
                "items": []
            }

        u = usuarios[numero]

        # =====================
        # BOTONES
        # =====================
        if "interactive" in msg:
            seleccion = msg["interactive"]["list_reply"]["id"]

            if seleccion in MENU:
                producto = MENU[seleccion]

                u["items"].append({
                    "nombre": producto["nombre"],
                    "precio": producto["precio"],
                    "cantidad": 1
                })

                enviar_texto(numero, f"✅ {producto['nombre']} agregado\nEscribe 'menu' o 'finalizar'")

        # =====================
        # TEXTO
        # =====================
        if "text" in msg:
            texto = msg["text"]["body"].lower()

            # INICIO
            if texto in ["hola", "menu"]:
                u["paso"] = "pedido"
                enviar_menu(numero)

            # FINALIZAR
            elif texto == "finalizar":

                if len(u["items"]) == 0:
                    enviar_texto(numero, "⚠️ No tienes productos")
                    return "ok", 200

                u["paso"] = "nombre"
                enviar_texto(numero, "📝 Escribe tu nombre")

            # NOMBRE
            elif u["paso"] == "nombre":
                u["cliente"] = texto
                u["paso"] = "direccion"
                enviar_texto(numero, "📍 Escribe tu dirección")

            # DIRECCION
            elif u["paso"] == "direccion":
                u["direccion"] = texto

                total = sum(i["precio"] for i in u["items"])

                resumen = "🧾 Pedido:\n"
                for i in u["items"]:
                    resumen += f"- {i['nombre']} ${i['precio']}\n"

                resumen += f"\n💰 Total: ${total}"
                resumen += "\n\nEscribe 'confirmar' o 'cancelar'"

                u["total"] = total
                u["paso"] = "confirmar"

                enviar_texto(numero, resumen)

            # CONFIRMAR
            elif texto == "confirmar" and u["paso"] == "confirmar":

                folio = guardar_pedido({
                    "cliente": u["cliente"],
                    "telefono": numero,
                    "direccion": u["direccion"],
                    "total": u["total"],
                    "estado": "nuevo",
                    "repartidor": "sin asignar",
                    "items": u["items"]
                })

                enviar_texto(numero, f"✅ Pedido #{folio} confirmado")

                usuarios[numero] = {"paso": "inicio", "items": []}

            elif texto == "cancelar":
                usuarios[numero] = {"paso": "inicio", "items": []}
                enviar_texto(numero, "❌ Pedido cancelado")

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
