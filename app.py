from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "mi_token_secreto"

@app.route("/")
def home():
    return "Bot activo"

@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if token == VERIFY_TOKEN:
        return challenge or "ok"
    return "Token incorrecto", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(data)
    return "ok", 200

