from flask import Flask, Response
import pika
import threading
import queue

app = Flask(__name__)
notifications = queue.Queue()

RABBITMQ_HOST = "localhost"
TOPIC_PAGAMENTOS_APROVADOS = "Pagamentos_Aprovados"

def consume_events():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=TOPIC_PAGAMENTOS_APROVADOS)

    def callback(ch, method, properties, body):
        notifications.put(body.decode())

    channel.basic_consume(queue=TOPIC_PAGAMENTOS_APROVADOS, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            data = notifications.get()
            yield f"data: {data}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

threading.Thread(target=consume_events, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5004, debug=True)
