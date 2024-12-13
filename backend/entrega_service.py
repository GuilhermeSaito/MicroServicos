from flask import Flask
import pika
import threading
import json

app = Flask(__name__)

RABBITMQ_HOST = "localhost"
TOPICS = {
    "pagamentos_aprovados": "Pagamentos_Aprovados",
    "pedidos_enviados": "Pedidos_Enviados"
}

def connect_rabbitmq():
    """Conecta ao RabbitMQ."""
    return pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))

def publicar_pedido_enviado(pedido):
    """Publica no tópico Pedidos_Enviados."""
    connection = connect_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=TOPICS["pedidos_enviados"])

    channel.basic_publish(
        exchange="",
        routing_key=TOPICS["pedidos_enviados"],
        body=json.dumps(pedido)
    )
    print(f"[Entrega Service] Pedido enviado publicado: {pedido}")
    connection.close()

def processar_pagamento_aprovado(evento):
    """Processa o evento de pagamento aprovado e gera uma nota fiscal."""
    data = []
    for produto in evento:
        produto_id = produto.get("id")
        nome_produto = produto.get("nome")
        quantidade = produto.get("quantidade", 0)
        cliente = produto.get("cliente")

        nota_fiscal = {
            "pedido_id": produto_id,
            "cliente": cliente,
            "produtos": nome_produto,
            "quantidade": quantidade,
            "status": "Nota Fiscal Emitida"
        }

        data.append(nota_fiscal)

        print(f"[Entrega Service] Nota Fiscal Gerada: {nota_fiscal}")

    # Publicar o evento no tópico Pedidos_Enviados
    publicar_pedido_enviado(data)

def consume_pagamentos():
    """Consome eventos do tópico Pagamentos_Aprovados."""
    connection = connect_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=TOPICS["pagamentos_aprovados"])

    def callback(ch, method, properties, body):
        evento = json.loads(body)
        print(f"[Entrega Service] Evento recebido: {evento}")
        processar_pagamento_aprovado(evento)

    channel.basic_consume(queue=TOPICS["pagamentos_aprovados"], on_message_callback=callback, auto_ack=True)
    print("[Entrega Service] Aguardando pagamentos aprovados...")
    channel.start_consuming()

# Inicia a thread para consumir eventos
threading.Thread(target=consume_pagamentos, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5003, debug=True)
