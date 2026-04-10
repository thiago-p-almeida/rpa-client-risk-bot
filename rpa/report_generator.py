import pandas as pd
import psycopg2
import sys
import os
import logging
import warnings
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

warnings.filterwarnings("ignore", category=UserWarning, module='pandas')

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'report_generator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. FUNÇÃO PRINCIPAL (GERAÇÃO DO EXCEL)
# ==============================================================================
def generate_compliance_report():
    """Lê dados de auditoria do banco e gera um Excel formatado para o Backoffice."""
    
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    os.makedirs(export_dir, exist_ok=True)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # Novo nome de arquivo refletindo o domínio GovTech
    file_name = f"govtech_audit_report_{timestamp}.xlsx"
    file_path = os.path.join(export_dir, file_name)

    logger.info("📊 Iniciando geração do relatório de auditoria de fornecedores...")

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Query atualizada para ler as novas tabelas e usar a CTE (evitando duplicatas)
        query = """
            WITH LatestProcessing AS (
                SELECT cnpj, compliance_score, decision_status, processed_at, error_message,
                       ROW_NUMBER() OVER(PARTITION BY cnpj ORDER BY processed_at DESC) as rn
                FROM compliance_audit_trail
            )
            SELECT 
                v.cnpj AS "CNPJ",
                v.razao_social AS "Razão Social",
                lp.compliance_score AS "Score Fiscal",
                COALESCE(lp.decision_status, 'Pending') AS "Status de Auditoria",
                lp.error_message AS "Motivo / Alerta",
                lp.processed_at AS "Data Processamento"
            FROM vendors v
            LEFT JOIN LatestProcessing lp ON v.cnpj = lp.cnpj AND lp.rn = 1
            ORDER BY lp.processed_at DESC NULLS LAST;
        """

        df = pd.read_sql(query, conn)

        if df.empty:
            logger.warning("⚠️ Nenhum dado encontrado no banco para exportar.")
            return

        # Correção de timezone para o Excel não quebrar
        if "Data Processamento" in df.columns:
            df["Data Processamento"] = pd.to_datetime(df["Data Processamento"]).dt.tz_localize(None)

        df.to_excel(file_path, index=False, engine='openpyxl')

        logger.info(f"✅ Relatório GovTech gerado com sucesso: {file_path}")
        logger.info(f"📈 Total de fornecedores exportados: {len(df)}")

    except Exception as e:
        logger.error(f"🚨 Erro ao gerar relatório: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    generate_compliance_report()