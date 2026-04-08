import os
import sys
import logging
import shutil
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E IMPORTAÇÕES
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

# ==============================================================================
# 2. CONFIGURAÇÃO DE LOGS E DIRETÓRIOS
# ==============================================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'data', 'archive')

# Garante que a estrutura de pastas exista
for directory in [LOG_DIR, INPUT_DIR, ARCHIVE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'ingestion.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 3. FUNÇÃO CORE: INGESTÃO EM LOTE (BULK INSERT)
# ==============================================================================
def process_excel_ingestion():
    """
    Varre a pasta de input, lê arquivos Excel, valida os dados e insere no banco em lote.
    Move os arquivos para a pasta 'archive' após o processamento.
    """
    logger.info("📥 Iniciando rotina de ingestão de dados via Excel...")

    # Lista todos os arquivos .xlsx na pasta de input
    files_to_process =[f for f in os.listdir(INPUT_DIR) if f.endswith('.xlsx') and not f.startswith('~')]

    if not files_to_process:
        logger.warning(f"Nenhum arquivo Excel encontrado na pasta: {INPUT_DIR}")
        return

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        for filename in files_to_process:
            file_path = os.path.join(INPUT_DIR, filename)
            logger.info(f"📄 Lendo arquivo: {filename}")

            try:
                # 1. Leitura e Validação (Pandas)
                df = pd.read_excel(file_path, engine='openpyxl')
                
                # Verifica se as colunas obrigatórias existem
                required_columns = {'client_id', 'name', 'email'}
                if not required_columns.issubset(df.columns):
                    logger.error(f"❌ Arquivo {filename} ignorado: Faltam colunas obrigatórias {required_columns}")
                    continue

                # Remove linhas onde client_id, name ou email estejam vazios (Data Cleansing)
                df = df.dropna(subset=['client_id', 'name', 'email'])
                
                # Converte os dados do DataFrame para uma lista de tuplas (formato exigido pelo psycopg2)
                records_to_insert = list(df[['client_id', 'name', 'email']].itertuples(index=False, name=None))

                if not records_to_insert:
                    logger.warning(f"⚠️ Arquivo {filename} não contém dados válidos após a limpeza.")
                    continue

                # 2. Inserção em Lote (Bulk Insert) com Idempotência
                insert_query = """
                    INSERT INTO clients (client_id, name, email)
                    VALUES %s
                    ON CONFLICT (client_id) DO NOTHING;
                """
                
                # execute_values é altamente otimizado para inserir milhares de linhas de uma vez
                execute_values(cur, insert_query, records_to_insert)
                conn.commit()

                logger.info(f"✅ Sucesso: {len(records_to_insert)} registros processados do arquivo {filename}.")

                # 3. Ciclo de Vida do Arquivo (Arquivamento)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_filename = f"processed_{timestamp}_{filename}"
                shutil.move(file_path, os.path.join(ARCHIVE_DIR, archive_filename))
                logger.info(f"📁 Arquivo movido para: {ARCHIVE_DIR}/{archive_filename}")

            except Exception as e:
                logger.error(f"🚨 Erro ao processar o arquivo {filename}: {str(e)}")
                conn.rollback() # Desfaz a transação deste arquivo em caso de erro

    except Exception as e:
        logger.critical(f"💥 Erro fatal de conexão com o banco: {str(e)}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    process_excel_ingestion()