from flask import Flask, request, jsonify, render_template
import requests
import os
import uuid
import psycopg2

app = Flask(__name__)

print("🔥 APP INICIANDO...")

# =========================
# VARIABLES
# =========================
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

usuarios = {}

# =========================
# DB CONNECTION
# =========================
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id SERIAL PRIMARY KEY,
        folio TEXT,
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

init_db()

# =========================
# DB FUNCTIONS
# =========================
def guardar_pedido(p):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO pedidos (folio, cliente, telefono, total, estado, repartidor)
    VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        p["folio"],
        p["cliente"],
        p["telefono"],
        p["total"],
        p["estado"],
        p["repartidor"]
    ))

    conn.commit()
    cur.close()
    conn.close()

def obtener_pedidos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT folio, cliente, telefono, total, estado, repartidor FROM pedidos ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    pedidos = []
    for r in rows:
        pedidos.append({
            "folio": r[0],
            "cliente": r[1],
            "telefono": r[2],
            "total": r[3],
            "estado": r[4],
            "repartidor": r[5]
        })

    return pedidos

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

def enviar_mensaje(numero, texto):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "text": {"body": texto}
    })

# =========================
# MENU
# =========================
MENU = {
    "camarones": 180,
    "pulpo": 220,
    "filete": 160,
    "coctel": 190,
    "coca": 30,
    "pepsi": 25
}

def enviar_menu(numero):
    texto = "🍽️ MENÚ\n\n"
    for k, v in MENU.items():
        texto += f"• {k} - ${v}\n"

    texto += "\nEscribe el nombre para agregar"
    enviar_mensaje(numero, texto)

# =========================
# RUTAS
# =========================
@app.route("/")
def home():
    return "🔥 Bot activo"

@app.route("/panel")
def panel():
    pedidos = obtener_pedidos()
    return render_template("panel.html", pedidos=pedidos)

@app.route("/pedidos")
def pedidos():
    return jsonify(obtener_pedidos())

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
    print("📩", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "ok", 200

        msg = value["messages"][0]
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"pedido": []}

        u = usuarios[numero]

        if "text" in msg:
            texto = msg["text"]["body"].lower()

            # INICIO
            if texto in ["hola", "menu"]:
                enviar_menu(numero)
                return "ok", 200

            # AGREGAR PRODUCTO
            if texto in MENU:
                u["pedido"].append({
                    "nombre": texto,
                    "precio": MENU[texto]
                })
                enviar_mensaje(numero, f"✅ {texto} agregado")
                return "ok", 200

            # VER PEDIDO
            if texto == "ver":
                total = sum(i["precio"] for i in u["pedido"])
                enviar_mensaje(numero, f"🧾 Total: ${total}")
                return "ok", 200

            # FINALIZAR
            if texto == "finalizar":
                total = sum(i["precio"] for i in u["pedido"])

                folio = str(uuid.uuid4())[:8]

                pedido = {
                    "folio": folio,
                    "cliente": "Cliente",
                    "telefono": numero,
                    "total": total,
                    "estado": "nuevo",
                    "repartidor": "sin asignar"
                }

                guardar_pedido(pedido)

                enviar_mensaje(numero, f"✅ Pedido #{folio} confirmado")

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
