from flask import Flask, Response
from flask_cors import CORS
import pika
import threading
import json
import time

app = Flask(__name__)
CORS(app)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPICS = [
    "Pedidos_Criados",
    "Pedidos_Excluídos",
    "Pagamentos_Aprovados",
    "Pagamentos_Recusados",
    "Pedidos_Enviados"
]

# Lista de notificações para enviar via SSE
notifications = []

# --------------------------------- Consumidor RabbitMQ ---------------------------------
def connect_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange="app", exchange_type='direct')
    return connection, channel

def consume_events():
    """Função para consumir eventos dos tópicos do RabbitMQ."""
    global notifications

    connection, channel = connect_rabbitmq()

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Declaração das filas
    for topic in TOPICS:
        channel.queue_bind(exchange="app", queue=queue_name, routing_key=topic)

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
        notifications.append(event)
        print(f"[Notificação] Nova notificação: {event}")

    # Registra o callback
    for topic in TOPICS:
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    # Loop manual para consumir mensagens
    print("[Notificação] Aguardando eventos...")
    while True:
        connection.process_data_events(time_limit=1)  # Processa eventos com timeout
        time.sleep(0.1)  # Evita sobrecarga no loop


# --------------------------------- SSE Endpoint ---------------------------------

@app.route('/stream', methods=['GET'])
def stream_notifications():
    """Endpoint SSE para enviar notificações ao frontend."""
    print("--------------- Entro na funcao stream notification ------------------")
    def event_stream():
        print("--------------- Entro na funcao event stream ------------------")
        last_sent = 0
        while True:
            # print(f"Len notifications: {len(notification)}; len last_sent: {last_sent}")
            # Verifica se há notificações novas
            if len(notifications) > last_sent:
                print(f"------------- Entro no if -------------------- Len notifications: {len(notifications)}; len last_sent: {last_sent}")
                # Envia as notificações que ainda não foram enviadas
                for i in range(last_sent, len(notifications)):
                    print(f"------------- Ta no for -------------------- {i}")
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
    app.run(port=5004, debug=True, threaded=True)
