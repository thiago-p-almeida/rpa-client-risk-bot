import time
import logging
import sys
import os

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
# Adiciona a pasta atual (rpa) ao path para podermos importar os outros scripts
sys.path.append(os.path.dirname(__file__))

import ingestion
import processor
import report_generator
import notifier

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'orchestrator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. FUNÇÃO PRINCIPAL (PIPELINE DE EXECUÇÃO)
# ==============================================================================
def run_pipeline():
    """
    Orquestra a execução sequencial de todos os módulos do RPA.
    Atua como o 'Maestro' do processo (Controller Pattern).
    """
    logger.info("🤖 Iniciando Pipeline do Risk Bot RPA...")
    start_time = time.time()

    try:
        # Passo 1: Ingestão de Dados (Lê Excel e joga no Banco)
        logger.info(">>> FASE 1: Ingestão de Dados")
        ingestion.process_excel_ingestion()

        # Passo 2: Processamento (Consome a fila e chama a API)
        logger.info(">>> FASE 2: Processamento de Risco")
        processor.process_clients_risk()

        # Passo 3: Geração de Relatório (Exporta o Excel)
        logger.info(">>> FASE 3: Geração de Relatório")
        report_generator.generate_risk_report()

        # Calcula o tempo total antes de enviar o e-mail
        end_time = time.time()
        execution_time = end_time - start_time

        # Passo 4: Notificação (Envia o e-mail com o anexo e o tempo)
        logger.info(">>> FASE 4: Notificação Executiva")
        notifier.send_summary_email(execution_time_seconds=execution_time)

        logger.info(f"🎉 Pipeline concluído com sucesso em {round(execution_time, 2)} segundos!")

    except Exception as e:
        # Se qualquer módulo der um erro fatal não tratado, o orquestrador captura aqui
        logger.critical(f"🚨 FALHA CATASTRÓFICA NO PIPELINE: {str(e)}")
        # Em um cenário real, aqui poderíamos chamar o notifier para enviar um e-mail de "Pipeline Quebrado"

if __name__ == "__main__":
    run_pipeline()