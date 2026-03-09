import pandas as pd
import psycopg2
import sys
import os
import logging
import warnings
from datetime import datetime

# 1. Ajuste de Path para importar o config da API
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

# Silencia o aviso do SQLAlchemy para manter o log limpo (Senior choice)
warnings.filterwarnings("ignore", category=UserWarning, module='pandas')

# --- CONFIGURAÇÃO DE LOGS ---
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'report_generator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_risk_report():
    """Lê dados de risco do banco e gera um Excel formatado."""
    
    # Define o caminho de saída
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"risk_report_{timestamp}.xlsx"
    file_path = os.path.join(export_dir, file_name)

    logger.info("📊 Iniciando geração do relatório de risco...")

    conn = None
    try:
        # Conexão com o banco usando psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        
        query = """
            SELECT 
                c.name AS "Cliente",
                r.client_id AS "ID",
                r.risk_score AS "Score",
                r.decision_status AS "Decisão",
                r.processed_at AS "Data Processamento"
            FROM client_risk_processing r
            JOIN clients c ON r.client_id = c.client_id
            ORDER BY r.processed_at DESC;
        """

        # O Pandas lê o SQL
        df = pd.read_sql(query, conn)

        if df.empty:
            logger.warning("⚠️ Nenhum dado encontrado no banco para exportar.")
            return

        # --- CORREÇÃO DE TIMEZONE PARA EXCEL ---
        # Converte a coluna de data para 'timezone unaware' removendo o offset (+00:00)
        if "Data Processamento" in df.columns:
            df["Data Processamento"] = pd.to_datetime(df["Data Processamento"]).dt.tz_localize(None)

        # Exportação para Excel
        df.to_excel(file_path, index=False, engine='openpyxl')

        logger.info(f"✅ Relatório gerado com sucesso: {file_path}")
        logger.info(f"📈 Total de registros exportados: {len(df)}")

    except Exception as e:
        logger.error(f"🚨 Erro ao gerar relatório: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    generate_risk_report()
