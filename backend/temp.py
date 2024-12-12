from flask import Flask, request, jsonify
import sqlite3
import pika
import json

app = Flask(__name__)

# Configurações do Banco de Dados SQLite
DATABASE = "produtos.db"

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPIC_PEDIDOS_CRIADOS = "Pedidos_Criados"
TOPIC_PEDIDOS_EXCLUIDOS = "Pedidos_Excluídos"

# --------------------------------- Banco de Dados SQLite ---------------------------------

def init_db():
    """Inicializa o banco de dados e cria a tabela produtos."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL
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
    channel.queue_declare(queue=topic)

    channel.basic_publish(
        exchange="",
        routing_key=topic,
        body=json.dumps(event_data)
    )
    print(f"[RabbitMQ] Evento publicado no tópico '{topic}': {event_data}")
    connection.close()

# --------------------------------- Endpoints REST ---------------------------------

# Criar um novo produto
@app.route("/produtos", methods=["POST"])
def criar_produto():
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")

    if not nome or quantidade is None:
        return jsonify({"error": "Nome e quantidade são obrigatórios"}), 400

    query_db("INSERT INTO produtos (nome, quantidade) VALUES (?, ?)", (nome, quantidade))
    return jsonify({"message": "Produto criado com sucesso"}), 201

# Ler todos os produtos
@app.route("/produtos", methods=["GET"])
def ler_produtos():
    produtos = query_db("SELECT id, nome, quantidade FROM produtos")
    produtos_list = [{"id": p[0], "nome": p[1], "quantidade": p[2]} for p in produtos]
    return jsonify(produtos_list), 200

# Atualizar um produto
@app.route("/produtos/<int:produto_id>", methods=["PUT"])
def atualizar_produto(produto_id):
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")

    if not nome or quantidade is None:
        return jsonify({"error": "Nome e quantidade são obrigatórios"}), 400

    query_db("UPDATE produtos SET nome = ?, quantidade = ? WHERE id = ?", (nome, quantidade, produto_id))
    return jsonify({"message": f"Produto {produto_id} atualizado com sucesso"}), 200

# Remover um produto
@app.route("/produtos/<int:produto_id>", methods=["DELETE"])
def remover_produto(produto_id):
    query_db("DELETE FROM produtos WHERE id = ?", (produto_id,))
    return jsonify({"message": f"Produto {produto_id} removido com sucesso"}), 200

# Criar um pedido (publica evento)
@app.route("/pedidos", methods=["POST"])
def criar_pedido():
    data = request.json
    pedido_id = data.get("id")
    produtos = data.get("produtos")

    if not pedido_id or not produtos:
        return jsonify({"error": "ID do pedido e lista de produtos são obrigatórios"}), 400

    # Publicar evento no RabbitMQ
    evento = {"id": pedido_id, "produtos": produtos}
    publish_event(TOPIC_PEDIDOS_CRIADOS, evento)
    return jsonify({"message": f"Pedido {pedido_id} criado e evento publicado"}), 201

# Excluir um pedido (publica evento)
@app.route("/pedidos/<int:pedido_id>", methods=["DELETE"])
def excluir_pedido(pedido_id):
    # Publicar evento no RabbitMQ
    evento = {"id": pedido_id, "produtos": []}  # Supondo que a lista de produtos não é obrigatória aqui
    publish_event(TOPIC_PEDIDOS_EXCLUIDOS, evento)
    return jsonify({"message": f"Pedido {pedido_id} excluído e evento publicado"}), 200

# --------------------------------- Inicialização ---------------------------------

if __name__ == "__main__":
    init_db()
    print("[Microsserviço Principal] Banco de dados inicializado.")
    app.run(port=5000, debug=True)
