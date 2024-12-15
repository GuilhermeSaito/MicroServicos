from flask import Flask, request, jsonify
import sqlite3
import pika
import json
import threading

app = Flask(__name__)

# Configurações do Banco de Dados SQLite
DATABASE = "produtos.db"

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPIC_PEDIDOS_CRIADOS = "Pedidos_Criados"
TOPIC_PEDIDOS_EXCLUIDOS = "Pedidos_Excluídos"
TOPIC_PAGAMENTOS_APROVADOS = "Pagamentos_Aprovados"
TOPIC_PAGAMENTOS_RECUSADOS = "Pagamentos_Recusados"
TOPIC_PEDIDOS_ENVIADOS = "Pedidos_Enviados"

# --------------------------------- Banco de Dados SQLite ---------------------------------

def init_db():
    """Inicializa o banco de dados e cria a tabela produtos/pedidos."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                cliente TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        conn.commit()

def query_db(query, args=(), one=False):
    """Executa consultas SQL no banco de dados SQLite."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        if query.strip().lower().startswith("select"):
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
        conn.commit()

# --------------------------------- Publicar Eventos no RabbitMQ ---------------------------------

def publish_event(topic, event_data):
    """Publica um evento no RabbitMQ."""
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange="app", exchange_type='direct')
    channel.basic_publish(
        exchange="app",
        routing_key=topic,
        body=json.dumps(event_data)
    )
    print(f"[RabbitMQ] Evento publicado no tópico '{topic}': {event_data}")
    connection.close()

# --------------------------------- Consumidores do RabbitMQ ---------------------------------

def consume_event(topic):
    """Consome mensagens de um tópico RabbitMQ."""
    def callback(ch, method, properties, body):
        print(f"[RabbitMQ] Evento recebido no tópico '{topic}': {body}")
        event_data = json.loads(body)
        handle_event(topic, event_data)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange="app", exchange_type='direct')
    channel.queue_declare(queue=topic)
    channel.queue_bind(exchange="app", queue=topic, routing_key=topic)
    channel.basic_consume(queue=topic, on_message_callback=callback, auto_ack=True)

    print(f"[RabbitMQ] Consumindo tópico: {topic}")
    channel.start_consuming()

def handle_event(topic, event_data):
    """Lógica para tratar eventos recebidos."""
    if topic == TOPIC_PAGAMENTOS_APROVADOS:
        atualizar_status_pedido(event_data['id'], "Aprovado")
    elif topic == TOPIC_PAGAMENTOS_RECUSADOS:
        atualizar_status_pedido(event_data['id'], "Recusado")
        publish_event(TOPIC_PEDIDOS_EXCLUIDOS, event_data)
    elif topic == TOPIC_PEDIDOS_ENVIADOS:
        atualizar_status_pedido(event_data['id'], "Enviado")

def atualizar_status_pedido(pedido_id, status):
    query_db("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
    print(f"[Banco de Dados] Pedido {pedido_id} atualizado para status: {status}")

# --------------------------------- Endpoints REST ---------------------------------

@app.route("/produtos/pedidos/create", methods=["POST"])
def criar_pedido():
    data = request.json
    cliente = data.get("cliente")

    if not cliente:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    # Criar pedido com status inicial "Criado"
    query_db("INSERT INTO pedidos (cliente, status) VALUES (?, ?)", (cliente, "Criado"))
    pedido_id = query_db("SELECT last_insert_rowid()", one=True)[0]

    evento = {"id": pedido_id, "cliente": cliente, "status": "Criado"}
    publish_event(TOPIC_PEDIDOS_CRIADOS, evento)

    return jsonify({"message": f"Pedido {pedido_id} criado e evento publicado"}), 201

@app.route("/produtos/pedidos/status/<int:pedido_id>", methods=["GET"])
def consultar_pedido(pedido_id):
    pedido = query_db("SELECT id, cliente, status FROM pedidos WHERE id = ?", (pedido_id,), one=True)
    if pedido:
        return jsonify({"id": pedido[0], "cliente": pedido[1], "status": pedido[2]}), 200
    return jsonify({"error": "Pedido não encontrado"}), 404

# --------------------------------- Inicialização ---------------------------------

if __name__ == "__main__":
    init_db()
    print("[Microsserviço Principal] Banco de dados inicializado.")

    # Iniciar consumidores em threads
    threading.Thread(target=consume_event, args=(TOPIC_PAGAMENTOS_APROVADOS,), daemon=True).start()
    threading.Thread(target=consume_event, args=(TOPIC_PAGAMENTOS_RECUSADOS,), daemon=True).start()
    threading.Thread(target=consume_event, args=(TOPIC_PEDIDOS_ENVIADOS,), daemon=True).start()

    app.run(port=5000, debug=True)
