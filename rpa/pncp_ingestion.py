import requests
import psycopg2
from psycopg2.extras import execute_values
import sys
import os
import logging
import time
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'pncp_ingestion.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. INTEGRAÇÃO COM A API DO GOVERNO (PNCP) - COM RESILIÊNCIA
# ==============================================================================
def fetch_pncp_contracts():
    """Busca contratos recentes na API pública do PNCP com política de Retry."""
    # Reduzido para 1 dia para evitar sobrecarga no servidor do governo
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    data_inicial = start_date.strftime('%Y%m%d')
    data_final = end_date.strftime('%Y%m%d')
    
    url = f"https://pncp.gov.br/api/consulta/v1/contratos?dataInicial={data_inicial}&dataFinal={data_final}&pagina=1"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(f"🌐 Consultando PNCP (Tentativa {attempt}/{max_retries}): {url}")
        try:
            # Aumentado para 45s (APIs públicas são lentas)
            response = requests.get(url, timeout=45)
            response.raise_for_status()
            data = response.json()
            
            contratos = data.get('data',[])
            logger.info(f"📥 {len(contratos)} contratos encontrados.")
            return contratos
            
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout na tentativa {attempt}. O servidor do governo está lento.")
            if attempt < max_retries:
                time.sleep(5) # Espera 5 segundos antes de tentar novamente (Backoff)
        except Exception as e:
            logger.error(f"❌ Erro ao consultar PNCP: {e}")
            break # Se for erro 500 ou 404, sai do loop e desiste
            
    return[]

# ==============================================================================
# 3. FUNÇÃO CORE: EXTRAÇÃO E BULK INSERT (RESILIENT PARSING)
# ==============================================================================
def process_pncp_ingestion():
    """Extrai fornecedores dos contratos e insere no banco de dados."""
    logger.info("🚀 Iniciando Ingestão de Dados do PNCP...")
    
    contratos = fetch_pncp_contracts()
    if not contratos:
        logger.warning("Nenhum dado retornado do PNCP. Encerrando ingestão.")
        return

    unique_vendors = {}
    
    for contrato in contratos:
        # Busca o CNPJ em múltiplas chaves possíveis do Governo
        cnpj = (contrato.get('niFornecedor') or 
                contrato.get('fornecedorCnpjCpfIdGenerico') or 
                contrato.get('cnpj'))
                
        # Busca a Razão Social na chave oficial do manual do PNCP
        nome = (contrato.get('nomeRazaoSocialFornecedor') or 
                contrato.get('nomeFornecedor') or 
                contrato.get('razaoSocial'))
        
        if cnpj and nome:
            # Data Cleansing: Remove pontos, barras e traços
            cnpj_clean = ''.join(filter(str.isdigit, str(cnpj)))
            
            # Filtra apenas CNPJs (14 dígitos)
            if len(cnpj_clean) == 14:
                unique_vendors[cnpj_clean] = nome

    if not unique_vendors:
        # Log de Debug Sênior: Imprime a estrutura do primeiro contrato para investigarmos
        logger.warning("⚠️ Nenhum CNPJ válido extraído. Estrutura do JSON recebido:")
        if contratos:
            logger.warning(list(contratos[0].keys()))
        return

    records_to_insert = [(cnpj, nome[:255]) for cnpj, nome in unique_vendors.items()]
    logger.info(f"⚙️ Preparando para inserir {len(records_to_insert)} fornecedores únicos no banco...")

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        insert_query = """
            INSERT INTO vendors (cnpj, razao_social)
            VALUES %s
            ON CONFLICT (cnpj) DO NOTHING;
        """
        
        execute_values(cur, insert_query, records_to_insert)
        conn.commit()
        logger.info(f"✅ Lote de {len(records_to_insert)} fornecedores processado com sucesso.")

    except Exception as e:
        logger.critical(f"💥 Erro fatal de conexão com o banco: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    process_pncp_ingestion()