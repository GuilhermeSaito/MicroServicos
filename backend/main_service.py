from flask import Flask, request, jsonify
import pika
import threading

app = Flask(__name__)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPICS = {
    "pedidos_criados": "Pedidos_Criados",
    "pagamentos_aprovados": "Pagamentos_Aprovados"
}

# Conexão RabbitMQ
def publish_event(topic, message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=topic)
    channel.basic_publish(exchange="", routing_key=topic, body=message)
    connection.close()

# Endpoint para criar pedidos
@app.route("/pedidos", methods=["POST"])
def criar_pedido():
    pedido = request.json
    publish_event(TOPICS["pedidos_criados"], str(pedido))
    return jsonify({"message": "Pedido criado", "pedido": pedido}), 201

# Consumidor dos pagamentos aprovados
def consume_pagamentos_aprovados():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=TOPICS["pagamentos_aprovados"])

    def callback(ch, method, properties, body):
        print(f"[Main Service] Pagamento aprovado: {body.decode()}")

    channel.basic_consume(queue=TOPICS["pagamentos_aprovados"], on_message_callback=callback, auto_ack=True)
    print("[Main Service] Aguardando pagamentos aprovados...")
    channel.start_consuming()

# Iniciar o consumidor em uma thread separada
threading.Thread(target=consume_pagamentos_aprovados, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
