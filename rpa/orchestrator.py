import time
import logging
import sys
import os

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
sys.path.append(os.path.dirname(__file__))

# Imports atualizados para o domínio GovTech
import pncp_ingestion
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
    """Orquestra a execução sequencial de todos os módulos do RPA GovTech."""
    logger.info("🤖 Iniciando Pipeline do GovTech Compliance Bot...")
    start_time = time.time()

    try:
        # Passo 1: Ingestão de Dados (Lê API do PNCP e joga no Banco)
        logger.info(">>> FASE 1: Ingestão de Contratos (PNCP)")
        pncp_ingestion.process_pncp_ingestion()

        # Passo 2: Processamento (Enriquece com Brasil API e chama Motor de Regras)
        logger.info(">>> FASE 2: Auditoria de Compliance (Brasil API)")
        processor.process_compliance_queue()

        # Passo 3: Geração de Relatório (Exporta o Excel GovTech)
        logger.info(">>> FASE 3: Geração de Dossiê (Excel)")
        report_generator.generate_compliance_report()

        end_time = time.time()
        execution_time = end_time - start_time

        # Passo 4: Notificação (Envia o e-mail institucional)
        logger.info(">>> FASE 4: Notificação Executiva")
        notifier.send_summary_email(execution_time_seconds=execution_time)

        logger.info(f"🎉 Pipeline concluído com sucesso em {round(execution_time, 2)} segundos!")

    except Exception as e:
        logger.critical(f"🚨 FALHA CATASTRÓFICA NO PIPELINE: {str(e)}")

if __name__ == "__main__":
    run_pipeline()