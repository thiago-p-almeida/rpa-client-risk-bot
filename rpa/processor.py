import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import sys
import os
import logging
import time
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'rpa_processor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Endpoints
INTERNAL_API_URL = "http://127.0.0.1:5050/risk-score"
BRASIL_API_BASE_URL = "https://brasilapi.com.br/api/cnpj/v1/"

# ==============================================================================
# 2. FUNÇÕES AUXILIARES (HELPERS)
# ==============================================================================
def register_failure(conn, cnpj, current_attempts, error_msg):
    """Registra uma falha na trilha de auditoria e incrementa a tentativa."""
    try:
        cur = conn.cursor()
        new_attempts = current_attempts + 1
        safe_error_msg = str(error_msg)[:500] 
        
        insert_query = """
            INSERT INTO compliance_audit_trail 
            (cnpj, processing_status, processing_attempts, error_message, processed_at)
            VALUES (%s, 'Failed', %s, %s, %s)
        """
        cur.execute(insert_query, (cnpj, new_attempts, safe_error_msg, datetime.now()))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"🚨 Erro interno ao registrar falha para {cnpj}: {e}")
        conn.rollback()

def fetch_vendor_dossier(cnpj):
    """
    Consulta a Brasil API para extrair os dados públicos da empresa.
    Implementa Rate Limiting implícito (espera de rede).
    """
    url = f"{BRASIL_API_BASE_URL}{cnpj}"
    try:
        # Timeout de 10s. APIs públicas podem sofrer gargalos.
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            # CNPJ não existe na base da Receita Federal
            return {"error": "CNPJ não encontrado na Receita Federal"}
        elif response.status_code == 429:
            # Too Many Requests (Fomos bloqueados temporariamente)
            raise requests.exceptions.RequestException("Rate Limit Excedido (HTTP 429)")
        else:
            response.raise_for_status()
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ Falha ao consultar Brasil API para {cnpj}: {e}")
        return None # Retorna None para acionar a política de Retry do robô

# ==============================================================================
# 3. FUNÇÃO PRINCIPAL (CORE DO ROBÔ)
# ==============================================================================
def process_compliance_queue():
    """Consome a fila de fornecedores, enriquece os dados e envia para o Motor de Regras."""
    logger.info(f"🚀 Iniciando Agente Investigador GovTech...")
    
    success_count = 0
    error_count = 0
    conn = None
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # --- LÓGICA DE FILA AVANÇADA (CTE + RETRY POLICY) ---
        queue_query = """
            WITH LastProcessing AS (
                SELECT cnpj, processing_status, processing_attempts,
                       ROW_NUMBER() OVER(PARTITION BY cnpj ORDER BY processed_at DESC) as rn
                FROM compliance_audit_trail
            )
            SELECT v.cnpj, v.razao_social, COALESCE(lp.processing_attempts, 0) as current_attempts
            FROM vendors v
            LEFT JOIN LastProcessing lp ON v.cnpj = lp.cnpj AND lp.rn = 1
            WHERE lp.cnpj IS NULL 
               OR (lp.processing_status = 'Failed' AND lp.processing_attempts < 2)
            LIMIT 50; -- Processa em lotes de 50 para evitar banimento de IP
        """
        cur.execute(queue_query)
        vendors = cur.fetchall()

        if not vendors:
            logger.warning("Nenhum fornecedor pendente na fila.")
            return

        logger.info(f"📦 Lote de {len(vendors)} fornecedores capturado. Iniciando enriquecimento...")

        for vendor in vendors:
            cnpj = vendor['cnpj']
            razao_social = vendor['razao_social']
            current_attempts = vendor['current_attempts']
            
            logger.info(f"🔍 Investigando: {razao_social[:30]}... ({cnpj}) | Tentativa: {current_attempts + 1}/2")

            # 1. Enriquecimento de Dados (Data Enrichment)
            vendor_dossier = fetch_vendor_dossier(cnpj)
            
            if vendor_dossier is None:
                # Falha de rede na Brasil API. Registra falha para tentar de novo depois.
                register_failure(conn, cnpj, current_attempts, "Falha de conexão com Brasil API")
                error_count += 1
                time.sleep(2) # Pausa tática antes de tentar o próximo
                continue

            # 2. Envio para o Motor de Decisão (Nossa API Flask)
            payload = {
                "cnpj": cnpj,
                "vendor_data": vendor_dossier
            }

            try:
                response = requests.post(INTERNAL_API_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    res_data = response.json()
                    logger.info(f"✅ Auditado: {cnpj} | Score: {res_data.get('compliance_score')} | Decisão: {res_data.get('decision')}")
                    success_count += 1
                else:
                    error_msg = f"Motor de Regras retornou Status {response.status_code} - {response.text}"
                    logger.error(f"❌ Falha na API Interna para {cnpj}: {error_msg}")
                    register_failure(conn, cnpj, current_attempts, error_msg)
                    error_count += 1

            except requests.exceptions.RequestException as e:
                error_msg = f"Connection Error com API Interna: {str(e)}"
                logger.error(f"💥 Erro de conexão ao processar {cnpj}: {error_msg}")
                register_failure(conn, cnpj, current_attempts, error_msg)
                error_count += 1
            
            # Throttling: Pausa de 1.5 segundos entre cada empresa para respeitar a Brasil API
            time.sleep(1.5)

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
    process_compliance_queue()