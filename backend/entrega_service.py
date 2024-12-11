from flask import Flask
import pika
import threading

app = Flask(__name__)

RABBITMQ_HOST = "localhost"
TOPIC_PAGAMENTOS_APROVADOS = "Pagamentos_Aprovados"

def consume_pagamentos():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=TOPIC_PAGAMENTOS_APROVADOS)

    def callback(ch, method, properties, body):
        print(f"[Entrega Service] Enviando pedido: {body.decode()}")

    channel.basic_consume(queue=TOPIC_PAGAMENTOS_APROVADOS, on_message_callback=callback, auto_ack=True)
    print("[Entrega Service] Aguardando pagamentos aprovados...")
    channel.start_consuming()

threading.Thread(target=consume_pagamentos, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5003, debug=True)
