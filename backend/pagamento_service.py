from flask import Flask, request, jsonify
import pika
import json

app = Flask(__name__)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
EXCHANGE_NAME = "app"
TOPIC_APPROVED = "Pagamentos_Aprovados"
TOPIC_DENIED = "Pagamentos_Recusados"

def connect_rabbitmq():
    """Estabelece conexão com o RabbitMQ e retorna a conexão e o canal."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
    return connection, channel

@app.route('/pagamento/webhook', methods=['POST'])
def webhook():
    """Recebe notificações de pagamento via Webhook."""
    try:
        # Recebe os dados do Webhook
        data = request.json

        transaction_id = data.get("transaction_id")
        status = data.get("status")
        quantidade = data.get("quantidade")
        cliente = data.get("cliente")

        # Valida campos obrigatórios
        if not transaction_id or not status or not quantidade or not cliente:
            return jsonify({"error": "Missing required fields"}), 400

        # Publica o evento no RabbitMQ com base no status do pagamento
        connection, channel = connect_rabbitmq()

        event = {
            "transaction_id": transaction_id,
            "status": status,
            "quantidade": quantidade,
            "cliente": cliente
        }

        if status == "autorizado":
            routing_key = TOPIC_APPROVED
        elif status == "recusado":
            routing_key = TOPIC_DENIED
        else:
            return jsonify({"error": "Invalid status"}), 400

        # Publica no RabbitMQ
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(event)
        )

        print(f"[RabbitMQ] Evento publicado: {event} -> {routing_key}")
        
        # Fecha a conexão
        connection.close()

        return jsonify({"message": "Evento processado com sucesso"}), 200
    except Exception as e:
        print(f"[Erro] {str(e)}")
        return jsonify({"error": "Erro ao processar o webhook"}), 500

if __name__ == "__main__":
    app.run(port=5002, debug=True)
