import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import sys
import os
import logging
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E IMPORTAÇÕES
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

# ==============================================================================
# 2. CONFIGURAÇÃO DE LOGS PROFISSIONAIS
# ==============================================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'rpa_processor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_URL = "http://127.0.0.1:5050/risk-score"

# ==============================================================================
# 3. FUNÇÕES AUXILIARES (HELPERS)
# ==============================================================================
def register_failure(conn, client_id, current_attempts, error_msg):
    """
    Registra uma falha de processamento no banco de dados (Audit Trail).
    Incrementa o número de tentativas para controle da política de Retry.
    """
    try:
        cur = conn.cursor()
        new_attempts = current_attempts + 1
        # Trunca a mensagem de erro para 500 caracteres para evitar estourar o limite do banco
        safe_error_msg = str(error_msg)[:500] 
        
        insert_query = """
            INSERT INTO client_risk_processing 
            (client_id, processing_status, processing_attempts, error_message, processed_at)
            VALUES (%s, 'Failed', %s, %s, %s)
        """
        cur.execute(insert_query, (client_id, new_attempts, safe_error_msg, datetime.now()))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"🚨 Erro interno ao registrar falha para {client_id}: {e}")
        conn.rollback()

# ==============================================================================
# 4. FUNÇÃO PRINCIPAL (CORE DO ROBÔ)
# ==============================================================================
def process_clients_risk():
    logger.info(f"🚀 Iniciando ciclo de automação. Alvo: {API_URL}")
    
    success_count = 0
    error_count = 0
    conn = None
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # --- LÓGICA DE FILA AVANÇADA (CTE + RETRY POLICY) ---
        # Usa uma Common Table Expression (CTE) para pegar apenas o ÚLTIMO status de cada cliente.
        # Filtra clientes novos (IS NULL) ou que falharam, respeitando o limite de 2 tentativas.
        queue_query = """
            WITH LastProcessing AS (
                SELECT client_id, processing_status, processing_attempts,
                       ROW_NUMBER() OVER(PARTITION BY client_id ORDER BY processed_at DESC) as rn
                FROM client_risk_processing
            )
            SELECT c.client_id, c.name, COALESCE(lp.processing_attempts, 0) as current_attempts
            FROM clients c
            LEFT JOIN LastProcessing lp ON c.client_id = lp.client_id AND lp.rn = 1
            WHERE lp.client_id IS NULL 
               OR (lp.processing_status = 'Failed' AND lp.processing_attempts < 2);
        """
        cur.execute(queue_query)
        clients = cur.fetchall()

        if not clients:
            logger.warning("Nenhum cliente pendente ou elegível para retentativa na fila.")
            return

        for client in clients:
            client_id = client['client_id']
            client_name = client['name']
            current_attempts = client['current_attempts']
            
            logger.info(f"🔍 Processando: {client_name} ({client_id}) | Tentativa: {current_attempts + 1}/2")

            try:
                response = requests.post(API_URL, json={"client_id": client_id}, timeout=10)
                
                if response.status_code == 200:
                    res_data = response.json()
                    logger.info(f"✅ Sucesso: {client_id} | Score: {res_data.get('risk_score')} | Decisão: {res_data.get('decision')}")
                    success_count += 1
                else:
                    error_msg = f"Status {response.status_code} - {response.text}"
                    logger.error(f"❌ Falha na API para {client_id}: {error_msg}")
                    register_failure(conn, client_id, current_attempts, error_msg)
                    error_count += 1

            except requests.exceptions.RequestException as e:
                error_msg = f"Connection Error: {str(e)}"
                logger.error(f"💥 Erro de conexão ao processar {client_id}: {error_msg}")
                register_failure(conn, client_id, current_attempts, error_msg)
                error_count += 1

        logger.info("-" * 50)
        logger.info(f"✨ Ciclo finalizado | Sucessos: {success_count} | Falhas: {error_count}")
        logger.info("-" * 50)

    except Exception as e:
        logger.critical(f"🚨 Erro Fatal no Banco de Dados: {str(e)}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    process_clients_risk()