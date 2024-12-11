from flask import Flask
import pika
import threading

app = Flask(__name__)

RABBITMQ_HOST = "localhost"
TOPIC_PEDIDOS_CRIADOS = "Pedidos_Criados"

def consume_pedidos():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=TOPIC_PEDIDOS_CRIADOS)

    def callback(ch, method, properties, body):
        print(f"[Estoque Service] Atualizando estoque para: {body.decode()}")

    channel.basic_consume(queue=TOPIC_PEDIDOS_CRIADOS, on_message_callback=callback, auto_ack=True)
    print("[Estoque Service] Aguardando pedidos criados...")
    channel.start_consuming()

threading.Thread(target=consume_pedidos, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5001, debug=True)
