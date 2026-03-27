@app.route('/webhook', methods=['GET'])
def verificar_webhook():
    try:
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if token == TOKEN_VERIFICACION:
            return challenge, 200
        else:
            return "Token de verificación incorrecto", 403
    except Exception as e:
        return str(e), 500

@app.route('/webhook', methods=['POST'])
def recibir_mensaje():
    data = request.get_json()
    # Agregamos un print para ver en los logs qué nos envía Meta exactamente
    print(f"Evento recibido: {data}")
    
    try:
        # Verificamos la estructura completa del JSON de WhatsApp
        if 'entry' in data and data['entry'][0]['changes'][0]['value'].get('messages'):
            mensaje = data['entry'][0]['changes'][0]['value']['messages'][0]
            numero = mensaje['from']
            texto_usuario = mensaje['body']
            
            enviar_mensaje(numero, f"¡Hola! Recibí tu mensaje: {texto_usuario}")
            
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        
    return jsonify({"status": "recibido"}), 200
