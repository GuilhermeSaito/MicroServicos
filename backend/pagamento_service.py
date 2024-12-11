from flask import Flask
import pika
import threading
import random

app = Flask(__name__)

RABBITMQ_HOST = "localhost"
TOPIC_PEDIDOS_CRIADOS = "Pedidos_Criados"
TOPIC_PAGAMENTOS_APROVADOS = "Pagamentos_Aprovados"

def publish_event(topic, message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=topic)
    channel.basic_publish(exchange="", routing_key=topic, body=message)
    connection.close()

def consume_pedidos():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=TOPIC_PEDIDOS_CRIADOS)

    def callback(ch, method, properties, body):
        pedido = body.decode()
        print(f"[Pagamento Service] Processando pagamento: {pedido}")
        aprovado = random.choice([True, False])
        if aprovado:
            publish_event(TOPIC_PAGAMENTOS_APROVADOS, pedido)
            print("[Pagamento Service] Pagamento aprovado!")
        else:
            print("[Pagamento Service] Pagamento recusado!")

    channel.basic_consume(queue=TOPIC_PEDIDOS_CRIADOS, on_message_callback=callback, auto_ack=True)
    print("[Pagamento Service] Aguardando pedidos criados...")
    channel.start_consuming()

threading.Thread(target=consume_pedidos, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5002, debug=True)
