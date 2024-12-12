from flask import Flask, Response
import pika
import threading
import json
import time

app = Flask(__name__)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPICS = [
    "Pedidos_Criados",
    "Pagamentos_Aprovados",
    "Pagamentos_Recusados",
    "Pedidos_Enviados"
]

# Lista de notificações para enviar via SSE
notifications = []

# --------------------------------- Consumidor RabbitMQ ---------------------------------

def consume_events():
    """Função para consumir eventos dos tópicos do RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()

    # Declaração das filas
    for topic in TOPICS:
        channel.queue_declare(queue=topic)

    # Callback para processar mensagens recebidas
    def callback(ch, method, properties, body):
        event = json.loads(body)
        topic = method.routing_key

        # Determina o status do pedido baseado no tópico
        status_mapping = {
            "Pedidos_Criados": "Pedido Criado",
            "Pagamentos_Aprovados": "Pagamento Aprovado",
            "Pagamentos_Recusados": "Pagamento Recusado",
            "Pedidos_Enviados": "Pedido Enviado"
        }
        status = status_mapping.get(topic, "Desconhecido")

        # Cria uma notificação com o ID e status do pedido
        notification = {"id": event["id"], "status": status}
        notifications.append(notification)
        print(f"[Notificação] Nova notificação: {notification}")

    # Configura consumo de mensagens
    for topic in TOPICS:
        channel.basic_consume(queue=topic, on_message_callback=callback, auto_ack=True)

    print("[Notificação] Aguardando eventos...")
    channel.start_consuming()

# --------------------------------- SSE Endpoint ---------------------------------

@app.route('/stream', methods=['GET'])
def stream_notifications():
    """Endpoint SSE para enviar notificações ao frontend."""
    def event_stream():
        last_sent = 0
        while True:
            # Verifica se há notificações novas
            if len(notifications) > last_sent:
                # Envia as notificações que ainda não foram enviadas
                for i in range(last_sent, len(notifications)):
                    notification = notifications[i]
                    data = json.dumps(notification)
                    yield f"data: {data}\n\n"
                    print(f"[SSE] Notificação enviada: {notification}")
                last_sent = len(notifications)
            time.sleep(1)  # Aguarda um segundo antes de checar novamente

    return Response(event_stream(), mimetype="text/event-stream")

# --------------------------------- Inicialização ---------------------------------

# Thread para consumir eventos do RabbitMQ
threading.Thread(target=consume_events, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5004, debug=True)
