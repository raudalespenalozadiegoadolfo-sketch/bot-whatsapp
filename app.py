from flask import Flask, request, jsonify, render_template
import requests, os, psycopg2, json

app = Flask(__name__)

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("MY_VERIFY_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

usuarios = {}

# =========================
# MENU
# =========================
MENU = {
    "cam_diabla": {"nombre": "Camarones a la Diabla", "precio": 180, "cat": "camarones"},
    "cam_emp": {"nombre": "Camarones Empanizados", "precio": 190, "cat": "camarones"},
    "pulpo": {"nombre": "Pulpo Zarandeado", "precio": 220, "cat": "pulpo"},
    "filete": {"nombre": "Filete Empanizado", "precio": 170, "cat": "filete"},
    "coctel": {"nombre": "Coctel Mixto", "precio": 220, "cat": "coctel"},
    "ceviche": {"nombre": "Ceviche", "precio": 180, "cat": "ceviche"},
    "aguachile": {"nombre": "Aguachile", "precio": 190, "cat": "aguachile"},
    "corte": {"nombre": "Corte Fino", "precio": 300, "cat": "cortes"},

    "coca": {"nombre": "Coca Cola", "precio": 30, "cat": "refrescos"},
    "agua1": {"nombre": "Agua 1L", "precio": 25, "cat": "agua1"},
    "agua500": {"nombre": "Agua 500ml", "precio": 15, "cat": "agua500"},
    "michelada": {"nombre": "Michelada 1L", "precio": 100, "cat": "micheladas"},
    "cerveza": {"nombre": "Cerveza 355ml", "precio": 40, "cat": "cervezas"}
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

def guardar_pedido(p):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO pedidos (cliente, telefono, direccion, total, estado, repartidor, detalle)
    VALUES (%s,%s,%s,%s,'nuevo','sin asignar',%s)
    RETURNING id
    """, (
        p["cliente"],
        p["telefono"],
        p["direccion"],
        p["total"],
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
# WHATSAPP
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
        "type": "button",
        "text": {"body": "👋 Bienvenido\n¿Qué deseas pedir?"},
        "interactive": {
            "type": "button",
            "body": {"text": "Selecciona"},
            "action": {
                "buttons": [
                    {"type": "reply","reply":{"id":"comida","title":"🍽 Comida"}},
                    {"type": "reply","reply":{"id":"bebidas","title":"🥤 Bebidas"}}
                ]
            }
        }
    })

def menu_agregar(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "¿Qué deseas agregar?"},
            "action": {
                "buttons": [
                    {"type": "reply","reply":{"id":"comida","title":"🍽 Comida"}},
                    {"type": "reply","reply":{"id":"bebidas","title":"🥤 Bebidas"}}
                ]
            }
        }
    })

def menu_comida(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona categoría"},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Comida",
                    "rows": [
                        {"id":"camarones","title":"Camarones"},
                        {"id":"pulpo","title":"Pulpo"},
                        {"id":"filete","title":"Filete"},
                        {"id":"coctel","title":"Coctel"},
                        {"id":"ceviche","title":"Ceviche"},
                        {"id":"aguachile","title":"Aguachile"},
                        {"id":"cortes","title":"Cortes Finos"}
                    ]
                }]
            }
        }
    })

def menu_bebidas(num):
    enviar({
        "messaging_product": "whatsapp",
        "to": num,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": "Selecciona bebida"},
            "action": {
                "button": "Ver",
                "sections": [{
                    "title": "Bebidas",
                    "rows": [
                        {"id":"refrescos","title":"Refrescos 600ml"},
                        {"id":"agua1","title":"Agua 1L"},
                        {"id":"agua500","title":"Agua 500ml"},
                        {"id":"micheladas","title":"Micheladas 1L"},
                        {"id":"cervezas","title":"Cerveza 355ml"}
                    ]
                }]
            }
        }
    })

def menu_productos(num, cat):
    rows = [{"id":k,"title":v["nombre"],"description":f"${v['precio']}"} for k,v in MENU.items() if v["cat"]==cat]

    enviar({
        "messaging_product":"whatsapp",
        "to":num,
        "type":"interactive",
        "interactive":{
            "type":"list",
            "body":{"text":cat.upper()},
            "action":{
                "button":"Ver",
                "sections":[{"title":"Menú","rows":rows}]
            }
        }
    })

def menu_acciones(num):
    enviar({
        "messaging_product":"whatsapp",
        "to":num,
        "type":"interactive",
        "interactive":{
            "type":"button",
            "body":{"text":"¿Qué deseas hacer?"},
            "action":{
                "buttons":[
                    {"type":"reply","reply":{"id":"seguir","title":"➕ Seguir"}},
                    {"type":"reply","reply":{"id":"finalizar","title":"✅ Finalizar"}},
                    {"type":"reply","reply":{"id":"vaciar","title":"🗑 Vaciar"}}
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
        msg = data["entry"][0]["changes"][0]["value"]

        if "messages" not in msg:
            return "ok", 200

        msg = msg["messages"][0]
        num = msg["from"]

        if num not in usuarios:
            usuarios[num] = {"paso":"inicio","items":[],"activo":True}

        u = usuarios[num]

        if not u["activo"]:
            return "ok", 200

        # INTERACTIVE
        if "interactive" in msg:

            if "list_reply" in msg["interactive"]:
                sel = msg["interactive"]["list_reply"]["id"]
            else:
                sel = msg["interactive"]["button_reply"]["id"]

            if sel == "comida":
                menu_comida(num)

            elif sel == "bebidas":
                menu_bebidas(num)

            elif sel in ["camarones","pulpo","filete","coctel","ceviche","aguachile","cortes"]:
                menu_productos(num, sel)

            elif sel in ["refrescos","agua1","agua500","micheladas","cervezas"]:
                menu_productos(num, sel)

            elif sel in MENU:
                u["temp"] = MENU[sel]
                u["paso"] = "cantidad"
                texto(num,f"¿Cuántos {MENU[sel]['nombre']}?")

            elif sel == "seguir":
                menu_agregar(num)

            elif sel == "vaciar":
                u["items"] = []
                texto(num,"Pedido vaciado")
                menu_agregar(num)

            elif sel == "finalizar":
                u["paso"] = "nombre"
                texto(num,"Nombre:")

        # TEXTO
        if "text" in msg:
            t = msg["text"]["body"].lower()

            if "gracias" in t:
                texto(num,"De nada 😊 que tengas un excelente día")
                u["activo"] = False
                return "ok",200

            if u["paso"] == "cantidad":
                cant = int(t)
                p = u["temp"]

                u["items"].append({"nombre":p["nombre"],"precio":p["precio"],"cantidad":cant})

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                texto(num,f"Agregado\nTotal: ${total}")
                menu_acciones(num)

            elif u["paso"] == "nombre":
                u["nombre"] = t
                u["paso"] = "direccion"
                texto(num,"Dirección:")

            elif u["paso"] == "direccion":
                u["direccion"] = t
                u["paso"] = "telefono"
                texto(num,"Teléfono:")

            elif u["paso"] == "telefono":

                total = sum(i["precio"]*i["cantidad"] for i in u["items"])

                folio = guardar_pedido({
                    "cliente": u["nombre"],
                    "telefono": t,
                    "direccion": u["direccion"],
                    "total": total,
                    "items": u["items"]
                })

                texto(num,f"Pedido #{folio} confirmado")

                usuarios[num] = {"paso":"inicio","items":[],"activo":True}

            else:
                menu_inicio(num)

    except Exception as e:
        print("ERROR:",e)

    return "ok",200

# =========================
# RUN
# =========================
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
