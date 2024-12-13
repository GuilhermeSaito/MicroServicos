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
                quantidade INTEGER NOT NULL,
                cliente TEXT NOT NULL
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

def get_id_produto(nome_produto, cliente):
    id = query_db("SELECT id FROM produtos WHERE nome = ? AND cliente = ?", (nome_produto, cliente), one=True)
    if id == None:
        return -1
    return id

def achou_valor(val):
    if val == -1:
        return 0
    return 1

# --------------------------------- Endpoints REST ---------------------------------

@app.route("/produtos/create", methods=["POST"])
def criar_produto():
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")
    cliente = data.get("cliente")

    if not nome or quantidade is None or not cliente:
        return jsonify({"error": "Nome, quantidade e cliente são obrigatórios"}), 400

    # Verificar se já existe um produto com o mesmo nome e cliente
    produto_existente = query_db("SELECT id, quantidade FROM produtos WHERE nome = ? AND cliente = ?", (nome, cliente), one=True)

    if produto_existente:
        # Atualizar a quantidade do produto existente
        produto_id, quantidade_atual = produto_existente
        nova_quantidade = quantidade_atual + quantidade
        query_db("UPDATE produtos SET quantidade = ? WHERE id = ?", (nova_quantidade, produto_id))
        return jsonify({"message": f"Quantidade do produto '{nome}' para o cliente '{cliente}' atualizada com sucesso"}), 200
    else:
        # Criar um novo produto
        query_db("INSERT INTO produtos (nome, quantidade, cliente) VALUES (?, ?, ?)", (nome, quantidade, cliente))
        return jsonify({"message": "Produto criado com sucesso"}), 201

# Ler todos os produtos
@app.route("/produtos/getall", methods=["GET"])
def ler_produtos():
    produtos = query_db("SELECT id, nome, quantidade, cliente FROM produtos")
    produtos_list = [{"id": p[0], "nome": p[1], "quantidade": p[2], "cliente": p[3]} for p in produtos]
    return jsonify(produtos_list), 200

# Atualizar um produto
@app.route("/produtos/update", methods=["GET"])
def atualizar_produto():
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")
    cliente = data.get("cliente")
    produto_id = get_id_produto(nome, cliente)

    if not achou_valor(produto_id):
        return jsonify({"error": "Produto não encontrado"}), 404

    if not nome or quantidade is None or produto_id is None:
        return jsonify({"error": "Nome e quantidade e client são obrigatórios"}), 400

    query_db("UPDATE produtos SET nome = ?, quantidade = ? WHERE id = ?", (nome, quantidade, produto_id))
    return jsonify({"message": f"Produto {produto_id} atualizado com sucesso"}), 200

# Remover um produto
@app.route("/produtos/remove", methods=["GET"])
def remover_produto():
    data = request.json
    nome = data.get("nome")
    cliente = data.get("cliente")
    produto_id = get_id_produto(nome, cliente)

    if not achou_valor(produto_id):
        return jsonify({"error": "Produto não encontrado"}), 404

    query_db("DELETE FROM produtos WHERE id = ?", (produto_id,))
    return jsonify({"message": f"Produto {produto_id} removido com sucesso"}), 200

# Criar um pedido (publica evento)
@app.route("/produtos/pedidos/create", methods=["POST"])
def criar_pedido():
    data = request.json
    cliente = data.get("cliente")

    if not cliente:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    produto_existente = query_db("SELECT id, nome, quantidade, cliente FROM produtos WHERE cliente = ?", (cliente,))
    pedidos_cliente = [
        {
            "id": reg[0],
            "nome": reg[1],
            "quantidade": reg[2],
            "cliente": reg[3]
        }
        for reg in produto_existente
    ]
    evento = pedidos_cliente

    # Publicar evento no RabbitMQ
    publish_event(TOPIC_PEDIDOS_CRIADOS, evento)
    return jsonify({"message": f"Pedido {evento} criado e evento publicado"}), 201

# Excluir um pedido (publica evento)
@app.route("/produtos/pedidos/delete", methods=["POST"])
def excluir_pedido(pedido_id):
    data = request.json
    cliente = data.get("cliente")

    if not cliente:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    produto_existente = query_db("SELECT id, nome, quantidade, cliente FROM produtos WHERE cliente = ?", (cliente,))
    pedidos_cliente = [
        {
            "id": reg[0],
            "nome": reg[1],
            "quantidade": reg[2],
            "cliente": reg[3]
        }
        for reg in produto_existente
    ]
    evento = pedidos_cliente
    
    publish_event(TOPIC_PEDIDOS_EXCLUIDOS, evento)
    return jsonify({"message": f"Pedido {pedido_id} excluído e evento publicado"}), 200

# --------------------------------- Inicialização ---------------------------------

if __name__ == "__main__":
    init_db()
    print("[Microsserviço Principal] Banco de dados inicializado.")
    app.run(port=5000, debug=True)
