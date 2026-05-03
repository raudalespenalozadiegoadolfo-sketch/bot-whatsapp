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
    "camarones_empanizados": {"nombre": "Camarones Empanizados", "precio": 190, "categoria": "camarones"},
    "camarones_ajo": {"nombre": "Camarones al Ajo", "precio": 180, "categoria": "camarones"},
    "pulpo_zarandeado": {"nombre": "Pulpo Zarandeado", "precio": 220, "categoria": "pulpo"},
    "coca": {"nombre": "Coca Cola", "precio": 30, "categoria": "bebidas"},
    "pepsi": {"nombre": "Pepsi", "precio": 25, "categoria": "bebidas"}
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
    FROM pedidos ORDER BY id DESC
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
# WHATSAPP SEND
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
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "👋 Bienvenido a Marisco Alegre 🦐\n\n¿Qué deseas pedir?"},
            "action": {
                "button": "Seleccionar",
                "sections": [
                    {
                        "title": "Opciones",
                        "rows": [
                            {"id": "comida", "title": "🍽 Comida"},
                            {"id": "bebidas", "title": "🥤 Bebidas"},
                            {"id": "pedido", "title": "🧾 Ver pedido"}
                        ]
                    }
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
                            {"id": "camarones", "title": "Camarones"},
                            {"id": "pulpo", "title": "Pulpo"}
                        ]
                    }
                ]
            }
        }
    })

def menu_productos(numero, categoria):
    rows = [
        {"id": k, "title": v["nombre"], "description": f"${v['precio']}"}
        for k, v in MENU.items() if v["categoria"] == categoria
    ]

    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": categoria.upper()},
            "action": {
                "button": "Ver opciones",
                "sections": [{"title": "Productos", "rows": rows}]
            }
        }
    })

def menu_acciones(numero):
    enviar({
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "¿Qué deseas hacer?"},
            "action": {
                "button": "Opciones",
                "sections": [
                    {
                        "title": "Acciones",
                        "rows": [
                            {"id": "seguir", "title": "➕ Seguir"},
                            {"id": "finalizar", "title": "✅ Finalizar"},
                            {"id": "vaciar", "title": "🗑 Vaciar"}
                        ]
                    }
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
        numero = msg["from"]

        if numero not in usuarios:
            usuarios[numero] = {"paso": "inicio", "items": []}

        u = usuarios[numero]

        # =========================
        # INTERACTIVE
        # =========================
        if "interactive" in msg:

            seleccion = msg["interactive"]["list_reply"]["id"]

            if seleccion == "comida":
                u["paso"] = "categoria"
                menu_categorias(numero)

            elif seleccion == "bebidas":
                menu_productos(numero, "bebidas")

            elif seleccion in ["camarones", "pulpo"]:
                u["categoria"] = seleccion
                menu_productos(numero, seleccion)

            elif seleccion in MENU:
                u["producto"] = seleccion
                enviar_texto(numero, f"¿Cuántos {MENU[seleccion]['nombre']} necesitas?")
                u["paso"] = "cantidad"

            elif seleccion == "seguir":
                u["paso"] = "categoria"
                menu_categorias(numero)

            elif seleccion == "vaciar":
                u["items"] = []
                enviar_texto(numero, "🗑 Pedido vaciado")

            elif seleccion == "finalizar":
                if len(u["items"]) == 0:
                    enviar_texto(numero, "⚠️ Tu pedido está vacío")
                else:
                    u["paso"] = "nombre"
                    enviar_texto(numero, "👤 Ingresa tu nombre:")

        # =========================
        # TEXTO
        # =========================
        if "text" in msg:
            texto = msg["text"]["body"]

            if texto.lower() in ["hola","menu"]:
                menu_inicio(numero)

            elif u["paso"] == "cantidad":
                cantidad = int(texto)

                producto = MENU[u["producto"]]

                u["items"].append({
                    "nombre": producto["nombre"],
                    "precio": producto["precio"],
                    "cantidad": cantidad
                })

                enviar_texto(numero, f"✅ {cantidad} {producto['nombre']} agregado")

                total = sum(i["precio"] * i["cantidad"] for i in u["items"])

                detalle = "\n".join([f"{i['cantidad']} {i['nombre']}" for i in u["items"]])

                enviar_texto(numero, f"🧾 Tu pedido:\n{detalle}\n\n💰 Total: ${total}")

                menu_acciones(numero)

            elif u["paso"] == "nombre":
                u["cliente"] = texto
                u["paso"] = "direccion"
                enviar_texto(numero, "📍 Ingresa tu dirección:")

            elif u["paso"] == "direccion":
                u["direccion"] = texto
                u["paso"] = "telefono"
                enviar_texto(numero, "📞 Ingresa tu teléfono:")

            elif u["paso"] == "telefono":

                u["telefono"] = texto

                total = sum(i["precio"] * i["cantidad"] for i in u["items"])

                folio = guardar_pedido({
                    "cliente": u["cliente"],
                    "telefono": u["telefono"],
                    "direccion": u["direccion"],
                    "total": total,
                    "estado": "nuevo",
                    "repartidor": "sin asignar",
                    "items": u["items"]
                })

                enviar_texto(numero, f"""🧾 Pedido #{folio}

💰 Total: ${total}
📍 {u['direccion']}
📞 {u['telefono']}

✅ Pedido confirmado ¡Gracias!""")

                usuarios[numero] = {"paso":"inicio","items":[]}

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
