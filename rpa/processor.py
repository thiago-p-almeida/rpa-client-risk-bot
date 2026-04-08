import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import sys
import os
import logging

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E IMPORTAÇÕES
# ==============================================================================
# Adiciona a pasta raiz ao sys.path para conseguir importar o config da API.
# Isso é necessário porque o Python, por padrão, não enxerga módulos em pastas "irmãs".
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG

# ==============================================================================
# 2. CONFIGURAÇÃO DE LOGS PROFISSIONAIS (OBSERVABILIDADE)
# ==============================================================================
# Garante que a pasta 'logs' exista na raiz do projeto.
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'rpa_processor.log')

# Configura o formato do log para incluir Data, Hora, Nível (INFO/ERROR) e a Mensagem.
# O StreamHandler joga o log no terminal, o FileHandler salva no arquivo .log.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() 
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 3. VARIÁVEIS GLOBAIS
# ==============================================================================
# URL da nossa API local que atua como o "Motor de Decisão de Risco"
API_URL = "http://127.0.0.1:5050/risk-score"

# ==============================================================================
# 4. FUNÇÃO PRINCIPAL (CORE DO ROBÔ)
# ==============================================================================
def process_clients_risk():
    """
    Busca clientes pendentes no banco de dados (Fila) e solicita o score de risco via API.
    Atua como um 'Queue Consumer' (Consumidor de Fila) idempotente.
    """
    logger.info(f"🚀 Iniciando ciclo de automação. Alvo: {API_URL}")
    
    # Contadores para métricas de performance da execução atual
    success_count = 0
    error_count = 0
    conn = None
    
    try:
        # Abre a conexão com o banco de dados Supabase/PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        # RealDictCursor faz com que os resultados do banco venham como Dicionários Python
        # Ex: row['client_id'] em vez de row[0], facilitando a leitura do código.
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # --- LÓGICA DE FILA (QUEUE PATTERN) ---
        # Busca apenas clientes que NUNCA foram processados (não existem na tabela de risco)
        # OU que falharam na última tentativa (processing_status = 'Failed').
        queue_query = """
            SELECT c.client_id, c.name 
            FROM clients c
            LEFT JOIN client_risk_processing crp ON c.client_id = crp.client_id
            WHERE crp.client_id IS NULL 
               OR crp.processing_status = 'Failed';
        """
        cur.execute(queue_query)
        clients = cur.fetchall()

        # Se a fila estiver vazia, encerra o processamento graciosamente
        if not clients:
            logger.warning("Nenhum cliente pendente na fila para processar.")
            return

        # Itera sobre cada cliente retornado pela fila
        for client in clients:
            client_id = client['client_id']
            client_name = client['name']
            
            logger.info(f"🔍 Processando: {client_name} ({client_id})")

            try:
                # Faz a chamada HTTP POST para a API enviando o ID do cliente
                # O timeout=10 evita que o robô fique travado para sempre se a API cair
                response = requests.post(
                    API_URL, 
                    json={"client_id": client_id}, 
                    timeout=10
                )
                
                # Se a API retornar 200 (Sucesso), extrai os dados e contabiliza
                if response.status_code == 200:
                    res_data = response.json()
                    score = res_data.get('risk_score')
                    decision = res_data.get('decision')
                    logger.info(f"✅ Sucesso: {client_id} | Score: {score} | Decisão: {decision}")
                    success_count += 1
                else:
                    # Se a API retornar erro (ex: 400, 500), loga o erro sem parar o robô
                    logger.error(f"❌ Falha na API para {client_id}: Status {response.status_code} - {response.text}")
                    error_count += 1

            except requests.exceptions.RequestException as e:
                # Captura erros de rede (ex: API offline, Timeout)
                logger.error(f"💥 Erro de conexão ao processar {client_id}: {str(e)}")
                error_count += 1

        # Resumo final no log (Métrica de performance do lote)
        logger.info("-" * 50)
        logger.info(f"✨ Ciclo finalizado | Sucessos: {success_count} | Falhas: {error_count}")
        logger.info("-" * 50)

    except Exception as e:
        # Captura erros críticos (ex: Banco de dados offline, credencial errada)
        logger.critical(f"🚨 Erro Fatal no Banco de Dados: {str(e)}")
    finally:
        # Bloco de limpeza: Garante que a conexão com o banco será fechada
        # independentemente de ter dado sucesso ou erro, evitando vazamento de memória (Memory Leak).
        if conn:
            cur.close()
            conn.close()

# Ponto de entrada do script
if __name__ == "__main__":
    process_clients_risk()