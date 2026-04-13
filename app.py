from flask import Flask, request, jsonify, render_template
import requests, os, psycopg2

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
    "camarones_diabla": 180,
    "camarones_empanizados": 190,
    "camarones_ajo": 180,
    "pulpo_diabla": 220,
    "pulpo_empanizado": 220,
    "filete_diabla": 160,
    "filete_empanizado": 170,
    "coctel_camaron": 190,
    "coctel_pulpo": 200,
    "coca": 30,
    "pepsi": 25
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
        folio SERIAL,
        cliente TEXT,
        telefono TEXT,
        total INT,
        estado TEXT,
        repartidor TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

def guardar_pedido(p):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO pedidos (cliente, telefono, total, estado, repartidor)
    VALUES (%s,%s,%s,%s,%s)
    RETURNING folio
    """, (p["cliente"], p["telefono"], p["total"], p["estado"], p["repartidor"]))

    folio = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return folio

def obtener_pedidos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT folio, cliente, total, estado FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [{"folio": r[0], "cliente": r[1], "total": r[2], "estado": r[3]} for r in rows]

# =========================
# STATS 🔥
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

    return {
        "pedidos": pedidos,
        "ventas": ventas,
        "preparando": preparando,
        "enviados": enviados
    }

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

def enviar_menu(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "🍽️ Selecciona tu pedido"},
            "action": {
                "button": "Ver menú",
                "sections": [
                    {
                        "title": "Comida",
                        "rows": [
                            {"id": "camarones_diabla", "title": "Camarones", "description": "$180"},
                            {"id": "pulpo_diabla", "title": "Pulpo", "description": "$220"},
                            {"id": "filete_diabla", "title": "Filete", "description": "$160"},
                            {"id": "coctel_camaron", "title": "Coctel", "description": "$190"}
                        ]
                    },
                    {
                        "title": "Bebidas",
                        "rows": [
                            {"id": "coca", "title": "Coca Cola", "description": "$30"},
                            {"id": "pepsi", "title": "Pepsi", "description": "$25"}
                        ]
                    }
                ]
            }
        }
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

@app.route("/estado/<folio>/<estado>")
def estado(folio, estado):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET estado=%s WHERE folio=%s", (estado, folio))
    conn.commit()
    cur.close()
    conn.close()
    return "ok"

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

        # 🔴 SOLUCIÓN ERROR 'messages'
        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": []}

        u = usuarios[numero]

        # BOTONES
        if "interactive" in msg:
            seleccion = msg["interactive"]["list_reply"]["id"]

            if seleccion in MENU:
                u["pedido"].append(MENU[seleccion])
                enviar_texto(numero, "✅ Agregado\nEscribe ver o finalizar")

        # TEXTO
        if "text" in msg:
            texto = msg["text"]["body"].lower()

            if texto in ["hola","menu"]:
                enviar_menu(numero)

            elif texto == "ver":
                total = sum(u["pedido"])
                enviar_texto(numero, f"🧾 Total: ${total}")

            elif texto == "finalizar":

                if len(u["pedido"]) == 0:
                    enviar_texto(numero, "⚠️ No tienes productos")
                    return "ok", 200

                total = sum(u["pedido"])

                folio = guardar_pedido({
                    "cliente": "Cliente",
                    "telefono": numero,
                    "total": total,
                    "estado": "nuevo",
                    "repartidor": "sin asignar"
                })

                # 🔥 FIX folio None
                if folio is None:
                    enviar_texto(numero, "❌ Error al guardar pedido")
                else:
                    enviar_texto(numero, f"✅ Pedido #{folio} confirmado\n💰 ${total}")

                usuarios[numero] = {"pedido": []}

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
