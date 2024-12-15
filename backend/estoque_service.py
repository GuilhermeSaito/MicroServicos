from flask import Flask, jsonify, request
from flask_cors import CORS
import pika
import threading
import json
import sqlite3

app = Flask(__name__)
CORS(app)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPICS = {
    "pedidos_criados": "Pedidos_Criados",
    "pedidos_excluidos": "Pedidos_Excluídos"
}

# Configurações do Banco de Dados SQLite
DATABASE = "produtos.db"

# --------------------------------- Banco de Dados SQLite ---------------------------------

def init_db():
    """Inicializa o banco de dados e cria a tabela estoque."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                quantidade INTEGER NOT NULL
            )
        ''')
        conn.commit()

# Função para executar consultas no banco de dados
def query_db(query, args=(), one=False):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        if query.strip().lower().startswith("select"):
            rv = cursor.fetchall()
            return (rv[0] if rv else None) if one else rv
        conn.commit()

# Função para conectar ao RabbitMQ
def connect_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.exchange_declare(exchange="app", exchange_type='direct')
    return connection, channel

# --------------------------------- Consumir Eventos no RabbitMQ ---------------------------------

# Atualiza o estoque ao consumir eventos
def atualizar_estoque(evento, tipo_evento):
    pode_atualizar = 1
    cliente = ""

    if tipo_evento == "Pedidos_Criados":
        # Reduz quantidade do estoque
        for produto in evento:
            nome_produto = produto.get("nome")
            quantidade = produto.get("quantidade", 0)

            registro = query_db("SELECT quantidade, id FROM estoque WHERE nome = ?", (nome_produto,), one=True)
            if registro:
                if registro[0] - quantidade < 0:
                    print(f"[Estoque] Produto {nome_produto} Não foi possível atualizar por conta da quantidade")
                    pode_atualizar = 0
                    break
                print(f"[Estoque] Produto {registro[1]} - Pode ser reduzido)")
            else:
                print(f"[Estoque] Produto {nome_produto} não encontrado no estoque.")
        if pode_atualizar:
            print(f"[Estoque] Produto irá atualizar o estoque.")
            for produto in evento:
                nome_produto = produto.get("nome")
                quantidade = produto.get("quantidade", 0)
                cliente = produto.get("cliente")

                registro = query_db("SELECT quantidade, id FROM estoque WHERE nome = ?", (nome_produto,), one=True)

                nova_quantidade = registro[0] - quantidade
                query_db("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_quantidade, registro[1]))
            # print("----------------- DEVERIA ATUALIZAR SOMENTE 1 VEZ -----------------")
            # print(cliente)
            produto_existente = query_db("SELECT id FROM pedidos WHERE cliente = ?", (cliente,), one=True)

            if not produto_existente:
                query_db("INSERT INTO pedidos (cliente, status) VALUES (?, ?)", (cliente, "criado"))
            else:
                print(f"[Estoque] Pedido já existe, não precisa criar um novo.")
            
            
        else:
            print(f"[Estoque] Produto NÃO irá atualizar o estoque.")

    elif tipo_evento == "Pedidos_Excluídos":
        # Reverte quantidade no estoque
        for produto in evento:
            nome_produto = produto.get("nome")
            quantidade = produto.get("quantidade", 0)
            cliente = produto.get("cliente")

            registro = query_db("SELECT quantidade, id FROM estoque WHERE nome = ?", (nome_produto,), one=True)
            if registro:
                nova_quantidade = registro[0] + quantidade
                query_db("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_quantidade, registro[1]))
                print(f"[Estoque] Produto {nome_produto} - Revertido (Nova quantidade: {nova_quantidade})")

                produto_id = get_id_produto(nome_produto, cliente)
                print(f"------------------- ID do PRODUTO: {produto_id} -------------------")

                query_db("DELETE FROM produtos WHERE id = ?", (produto_id[0],))
                query_db("DELETE FROM pedidos WHERE cliente = ?", (cliente,))
            else:
                print(f"[Estoque] Produto {nome_produto} não encontrado no estoque.")
        query_db("DELETE FROM produtos WHERE cliente = ?", (cliente,))

    print(f"[Estoque] Evento '{tipo_evento}' processado. Pedido ID: {evento}")

# Consumidor RabbitMQ
def consume_events():
    connection, channel = connect_rabbitmq()

    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Declara as filas que serão consumidas
    for topic in [TOPICS["pedidos_criados"], TOPICS["pedidos_excluidos"]]:
        channel.queue_bind(exchange = "app", queue = queue_name, routing_key = topic)

    def callback(ch, method, properties, body):
        evento = json.loads(body)
        topic = method.routing_key
        print(f"[Estoque] Evento recebido: {evento} - Tópico: {topic}")

        if topic == TOPICS["pedidos_criados"]:
            atualizar_estoque(evento, "Pedidos_Criados")
        elif topic == TOPICS["pedidos_excluidos"]:
            atualizar_estoque(evento, "Pedidos_Excluídos")

    # Configura consumo para as filas
    for topic in [TOPICS["pedidos_criados"], TOPICS["pedidos_excluidos"]]:
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

    channel.start_consuming()

# --------------------------------- Funcoes auxiliares ---------------------------------
    
def get_id_produto(nome_produto, cliente):
    id = query_db("SELECT id FROM produtos WHERE nome = ? AND cliente = ?", (nome_produto, cliente), one=True)
    if id == None:
        return -1
    return id

def get_id_estoque(nome_produto):
    id = query_db("SELECT id FROM estoque WHERE nome = ?", (nome_produto,), one=True)
    if id == None:
        return -1
    return id

def achou_valor(val):
    if val == -1:
        return 0
    return 1
    

# --------------------------------- Endpoints REST ---------------------------------

# 1. Consultar Estoque
@app.route("/estoque/getall", methods=["GET"])
def consultar_estoque():
    registros = query_db("SELECT id, nome, quantidade FROM estoque")
    estoque = [
        {
            "id": reg[0],
            "nome": reg[1],
            "quantidade": reg[2],
            "status": "em estoque" if reg[2] > 0 else "sem estoque"
        }
        for reg in registros
    ]
    return jsonify(estoque), 200

# 2. Consultar Produto Específico
@app.route("/estoque/get", methods=["GET"])
def consultar_produto():
    data = request.json
    nome = data.get("nome")
    produto_id = get_id_estoque(nome)

    if not achou_valor(produto_id):
        return jsonify({"error": "Produto não encontrado"}), 404
    
    produto_id = produto_id[0]

    registro = query_db("SELECT DISTINCT id, nome, quantidade FROM estoque WHERE id = ?", (produto_id,), one=True)
    if not registro:
        return jsonify({"error": "Produto não encontrado"}), 404

    produto = {
        "id": registro[0],
        "nome": registro[1],
        "quantidade": registro[2],
        "status": "em estoque" if registro[2] > 0 else "sem estoque"
    }
    return jsonify(produto), 200

# 3. Atualizar Estoque Manualmente
@app.route("/estoque/update", methods=["POST"])
def atualizar_estoque_manual():
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")
    produto_id = get_id_estoque(nome)

    if not achou_valor(produto_id):
        return jsonify({"error": "Produto não encontrado"}), 404
    
    produto_id = produto_id[0]

    query_db("UPDATE estoque SET quantidade = ? WHERE id = ?", (quantidade, produto_id))
    return jsonify({"message": "Estoque atualizado com sucesso", "id": produto_id, "quantidade": quantidade}), 200

@app.route("/estoque/create", methods=["POST"])
def criar_estoque_produto():
    data = request.json
    nome = data.get("nome")
    quantidade = data.get("quantidade")

    if not nome or quantidade is None:
        return jsonify({"error": "Nome, quantidade são obrigatórios"}), 400

    # Verificar se já existe um produto com o mesmo nome e cliente
    produto_existente = query_db("SELECT id, quantidade FROM estoque WHERE nome = ?", (nome,), one=True)

    if produto_existente:
        # Atualizar a quantidade do produto existente
        produto_id, quantidade_atual = produto_existente
        nova_quantidade = quantidade_atual + quantidade
        query_db("UPDATE estoque SET quantidade = ? WHERE id = ?", (nova_quantidade, produto_id))
        return jsonify({"message": f"Quantidade do produto '{nome}' para a quantidade '{nova_quantidade}' atualizada com sucesso"}), 200
    else:
        # Criar um novo produto
        query_db("INSERT INTO estoque (nome, quantidade) VALUES (?, ?)", (nome, quantidade))
        return jsonify({"message": "Produto no estoque criado com sucesso"}), 201

# --------------------------------- Inicialização ---------------------------------

# Inicializa o banco de dados
init_db()

# Thread para consumir eventos
threading.Thread(target=consume_events, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5001, debug=True)
