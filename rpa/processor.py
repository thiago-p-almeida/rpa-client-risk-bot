import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import sys
import os
import logging

# 1. Ajuste de Path para importar o config da API
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

# --- CONFIGURAÇÃO DE LOGS PROFISSIONAIS PARA RPA ---
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'rpa_processor.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() # Exibe no terminal e grava no arquivo
    ]
)
logger = logging.getLogger(__name__)

# 2. CONFIGURAÇÃO DA API
API_URL = "http://127.0.0.1:5000/risk-score"

def process_clients_risk():
    """Busca clientes no banco e solicita o score de risco via API."""
    logger.info(f"🚀 Iniciando ciclo de automação. Alvo: {API_URL}")
    
    success_count = 0
    error_count = 0
    conn = None
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT client_id, name FROM clients;")
        clients = cur.fetchall()

        if not clients:
            logger.warning("Nenhum cliente encontrado na tabela 'clients' para processar.")
            return

        for client in clients:
            client_id = client['client_id']
            client_name = client['name']
            
            logger.info(f"🔍 Processando: {client_name} ({client_id})")

            try:
                response = requests.post(
                    API_URL, 
                    json={"client_id": client_id}, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    res_data = response.json()
                    score = res_data.get('risk_score')
                    decision = res_data.get('decision')
                    logger.info(f"✅ Sucesso: {client_id} | Score: {score} | Decisão: {decision}")
                    success_count += 1
                else:
                    logger.error(f"❌ Falha na API para {client_id}: Status {response.status_code} - {response.text}")
                    error_count += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"💥 Erro de conexão ao processar {client_id}: {str(e)}")
                error_count += 1

        # Resumo final no log (Métrica de performance)
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
