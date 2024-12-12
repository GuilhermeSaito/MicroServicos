from flask import Flask, jsonify
import pika
import threading
import json

app = Flask(__name__)

# Configurações do RabbitMQ
RABBITMQ_HOST = "localhost"
TOPICS = {
    "pedidos_criados": "Pedidos_Criados",
    "pedidos_excluidos": "Pedidos_Excluídos"
}

# Simulação de banco de dados: estoque em memória
estoque = {
    1: {"nome": "Produto A", "quantidade": 100},
    2: {"nome": "Produto B", "quantidade": 200},
}

# Função para conectar ao RabbitMQ
def connect_rabbitmq():
    return pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))

# Atualiza o estoque ao consumir eventos
def atualizar_estoque(evento, tipo_evento):
    global estoque
    pedido_id = evento.get("id")
    produtos = evento.get("produtos", [])

    if tipo_evento == "Pedidos_Criados":
        # Reduz quantidade do estoque
        for produto_id in produtos:
            if produto_id in estoque:
                estoque[produto_id]["quantidade"] -= 1
                print(f"[Estoque] Produto {produto_id} - Reduzido (Nova quantidade: {estoque[produto_id]['quantidade']})")
            else:
                print(f"[Estoque] Produto {produto_id} não encontrado no estoque.")

    elif tipo_evento == "Pedidos_Excluídos":
        # Reverte quantidade no estoque
        for produto_id in produtos:
            if produto_id in estoque:
                estoque[produto_id]["quantidade"] += 1
                print(f"[Estoque] Produto {produto_id} - Revertido (Nova quantidade: {estoque[produto_id]['quantidade']})")
            else:
                print(f"[Estoque] Produto {produto_id} não encontrado no estoque.")

    print(f"[Estoque] Evento '{tipo_evento}' processado. Pedido ID: {pedido_id}")

# Consumidor RabbitMQ
def consume_events():
    connection = connect_rabbitmq()
    channel = connection.channel()

    # Declara as filas que serão consumidas
    for topic in [TOPICS["pedidos_criados"], TOPICS["pedidos_excluidos"]]:
        channel.queue_declare(queue=topic)

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
        channel.basic_consume(queue=topic, on_message_callback=callback, auto_ack=True)

    print("[Estoque] Aguardando eventos...")
    channel.start_consuming()

# --------------------------------- Endpoints REST ---------------------------------

# 1. Consultar Estoque
@app.route("/estoque", methods=["GET"])
def consultar_estoque():
    return jsonify(estoque), 200

# --------------------------------- Inicialização ---------------------------------

# Thread para consumir eventos
threading.Thread(target=consume_events, daemon=True).start()

if __name__ == "__main__":
    app.run(port=5001, debug=True)
