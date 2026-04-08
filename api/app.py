import os
import random
import logging
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime
from config import DB_CONFIG

# --- CONFIGURAÇÃO DE LOGS PROFISSIONAIS ---
# Define o caminho da pasta de logs (sobe um nível para a raiz do projeto)
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'api.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() # Saída no terminal
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_connection():
    """Cria uma nova conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "service": "Automated Client Risk API",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/risk-score", methods=["POST"])
def risk_score():
    """Processa o score de risco e registra no banco."""
    data = request.get_json()

    if not data or "client_id" not in data:
        logger.warning("Tentativa de acesso sem client_id na requisição.")
        return jsonify({"status": "error", "message": "client_id is required"}), 400

    client_id = data["client_id"]
    score = random.randint(300, 850)
    decision = "Approved" if score > 600 else "Manual Review" if score > 400 else "Rejected"

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Validar existência do cliente
        cur.execute("SELECT name FROM clients WHERE client_id = %s", (client_id,))
        client_record = cur.fetchone()
        
        if not client_record:
            logger.error(f"Falha de processamento: Cliente {client_id} não encontrado no banco.")
            return jsonify({
                "status": "error", 
                "message": f"Client {client_id} not found."
            }), 404

        client_name = client_record[0]

        # 2. Registrar transação de risco
        insert_query = """
            INSERT INTO client_risk_processing 
            (client_id, risk_score, decision_status, processing_status, processed_at, processing_attempts)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            client_id, score, decision, 'Completed', datetime.now(), 1
        ))

        conn.commit()
        logger.info(f"Sucesso: Risco processado para {client_name} ({client_id}) | Score: {score} | Decisão: {decision}")

        return jsonify({
            "client_id": client_id,
            "risk_score": score,
            "decision": decision,
            "status": "success"
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.critical(f"Erro crítico no banco de dados para o cliente {client_id}: {str(e)}")
        return jsonify({"status": "error", "message": "Internal database error"}), 500

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Iniciando Automated Client Risk API na porta 5050...")
    app.run(debug=True, port=5050)
