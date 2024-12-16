from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import threading
import time
import json

app = Flask(__name__)
CORS(app)

# Configuração do Webhook (backend do e-commerce)
ECOMMERCE_WEBHOOK_URL = "http://localhost:5002/pagamento/webhook"

# Simulação de Banco de Dados de Transações
transactions = {}

# Simulação de Processamento de Pagamentos
def process_payment(transaction_id, payment_data):
    """Simula o processamento do pagamento e envia uma notificação via Webhook."""
    time.sleep(2)  # Simula o tempo de processamento

    # Determina o status do pagamento aleatoriamente
    # status = random.choice(["autorizado", "recusado"])
    status = "autorizado"
    payment_data["status"] = status

    # Atualiza o banco de dados simulado
    transactions[transaction_id] = payment_data

    # Envia notificação via Webhook
    try:
        print(payment_data)
        print(type(payment_data))
        print("ENTRO NO TRY!!")
        response = requests.post(ECOMMERCE_WEBHOOK_URL, json=payment_data)
        print(f"[Webhook] Notificação enviada. Status HTTP: {response.status_code}")
    except Exception as e:
        print(f"[Webhook] Falha ao enviar notificação: {e}")

@app.route('/transacoes/pay', methods=['POST'])
def pay():
    """Endpoint para processar pagamentos."""
    data = request.json

    # Validação básica
    if not data or not all(key in data for key in ("transaction_id", "quantidade", "cliente")):
        return jsonify({"error": "Dados inválidos."}), 400

    transaction_id = data["transaction_id"]

    if transaction_id in transactions:
        return jsonify({"error": "Transação já processada."}), 400

    # Adiciona a transação no banco de dados simulado
    transactions[transaction_id] = {
        "transaction_id": transaction_id,
        "quantidade": data["quantidade"],
        "cliente": data["cliente"],
        "status": "em processamento"
    }

    # Processa o pagamento em uma thread separada
    threading.Thread(target=process_payment, args=(transaction_id, transactions[transaction_id])).start()

    return jsonify({"message": "Pagamento em processamento.", "transaction_id": transaction_id}), 202

@app.route('/transacoes/getIndividual', methods=['GET'])
def get_transaction(transaction_id):
    """Endpoint para consultar uma transação específica."""
    transaction = transactions.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Transação não encontrada."}), 404

    return jsonify(transaction)

if __name__ == "__main__":
    app.run(port=5005, debug=True)
