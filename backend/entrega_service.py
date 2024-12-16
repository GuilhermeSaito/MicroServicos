from flask import Flask
from flask_cors import CORS
import pika
import threading
import json

app = Flask(__name__)
CORS(app)

RABBITMQ_HOST = "localhost"
TOPICS = {
    "pagamentos_aprovados": "Pagamentos_Aprovados",
    "pedidos_enviados": "Pedidos_Enviados"
}

def connect_rabbitmq():
    """Conecta ao RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange="app", exchange_type='direct')
    return connection, channel

def publicar_pedido_enviado(pedido):
    """Publica no tópico Pedidos_Enviados."""
    connection, channel = connect_rabbitmq()

    channel.basic_publish(
        exchange="app",
        routing_key=TOPICS["pedidos_enviados"],
        body=json.dumps(pedido)
    )
    print(f"[Entrega Service] Pedido enviado publicado: {pedido}")
    connection.close()

def processar_pagamento_aprovado(evento):
    """Processa o evento de pagamento aprovado e gera uma nota fiscal."""
    print(f"--------------------- {evento} -----------------")
    print(type(evento))
    data = {
        "id": evento[0],
        "status": "Nota Fiscal Emitida"
    }
    
    print(f"[Entrega Service] Nota Fiscal Gerada: {data}")

    # Publicar o evento no tópico Pedidos_Enviados
    publicar_pedido_enviado(data)

def consume_pagamentos():
    """Consome eventos do tópico Pagamentos_Aprovados."""
    def callback(ch, method, properties, body):
        evento = json.loads(body)
        print(f"[Entrega Service] Evento recebido: {evento}")
        processar_pagamento_aprovado(evento)

    connection, channel = connect_rabbitmq()

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue
    
    channel.queue_bind(exchange = "app", queue = queue_name, routing_key = TOPICS["pagamentos_aprovados"])
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    print("[Entrega Service] Aguardando pagamentos aprovados...")
    channel.start_consuming()

# Inicia a thread para consumir eventos
threading.Thread(target=consume_pagamentos, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5003, debug=True)
