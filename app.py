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
# MENU
# =========================
MENU = {
    "camarones_diabla": {"nombre": "Camarones Diabla", "precio": 180},
    "camarones_empanizados": {"nombre": "Camarones Empanizados", "precio": 190},
    "pulpo_diabla": {"nombre": "Pulpo Diabla", "precio": 220},
    "filete_diabla": {"nombre": "Filete Diabla", "precio": 160},
    "coctel_camaron": {"nombre": "Coctel Camarón", "precio": 190},
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
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO pedidos (cliente, telefono, direccion, total, estado, repartidor, detalle)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """, (
            p["cliente"],
            p["telefono"],
            p.get("direccion", ""),
            p["total"],
            p["estado"],
            p["repartidor"],
            json.dumps(p.get("items", []))
        ))

        folio = cur.fetchone()[0]

        conn.commit()
        cur.close()
        conn.close()

        return folio

    except Exception as e:
        print("ERROR GUARDAR:", e)
        return None

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
# TOP PRODUCTOS 🔥
# =========================
@app.route("/top")
def top_productos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT detalle FROM pedidos")
    rows = cur.fetchall()

    conteo = {}

    for r in rows:
        if r[0]:
            for item in r[0]:
                nombre = item["nombre"]
                cantidad = item["cantidad"]

                if nombre not in conteo:
                    conteo[nombre] = 0

                conteo[nombre] += cantidad

    top = sorted(conteo.items(), key=lambda x: x[1], reverse=True)

    cur.close()
    conn.close()

    return jsonify(top[:5])

# =========================
# PANEL
# =========================
@app.route("/")
def home():
    return "Servidor activo 🔥"

@app.route("/panel")
def panel():
    return render_template("panel.html")

@app.route("/pedidos")
def pedidos():
    return jsonify(obtener_pedidos())

# =========================
# PEDIDO MANUAL
# =========================
@app.route("/nuevo_manual", methods=["POST"])
def nuevo_manual():
    data = request.json

    guardar_pedido({
        "cliente": data.get("cliente"),
        "telefono": data.get("telefono"),
        "direccion": data.get("direccion"),
        "total": data.get("total"),
        "estado": "nuevo",
        "repartidor": "sin asignar",
        "items": data.get("items", [])
    })

    return jsonify({"ok": True})

# =========================
# ESTADO
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
# WHATSAPP
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
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"items": []}

        u = usuarios[numero]

        if "interactive" in msg:
            seleccion = msg["interactive"]["list_reply"]["id"]

            if seleccion in MENU:
                producto = MENU[seleccion]

                u["items"].append({
                    "nombre": producto["nombre"],
                    "precio": producto["precio"],
                    "cantidad": 1
                })

                enviar_texto(numero, "✅ Agregado\nEscribe finalizar")

        if "text" in msg:
            texto = msg["text"]["body"].lower()

            if texto == "finalizar":

                if len(u["items"]) == 0:
                    enviar_texto(numero, "⚠️ No tienes productos")
                    return "ok", 200

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

                enviar_texto(numero, f"✅ Pedido #{folio}\n💰 ${total}")

                usuarios[numero] = {"items": []}

    except Exception as e:
        print("ERROR WEBHOOK:", e)

    return "ok", 200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
