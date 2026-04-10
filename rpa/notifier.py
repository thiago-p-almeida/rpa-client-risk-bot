import smtplib
import os
import sys
import logging
import psycopg2
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE E LOGS
# ==============================================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import DB_CONFIG, SMTP_CONFIG

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'notifier.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# 2. FUNÇÕES AUXILIARES
# ==============================================================================
def get_execution_metrics():
    """Busca no banco de dados o resumo das decisões tomadas hoje (Horário de Brasília)."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Converte o UTC do banco para o fuso horário do Brasil (America/Sao_Paulo)
        # antes de comparar com a data atual.
        query = """
            WITH LatestProcessing AS (
                SELECT decision_status,
                       ROW_NUMBER() OVER(PARTITION BY cnpj ORDER BY processed_at DESC) as rn
                FROM compliance_audit_trail
                WHERE DATE(processed_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo') = 
                      DATE(CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AT TIME ZONE 'America/Sao_Paulo')
            )
            SELECT decision_status, COUNT(*) 
            FROM LatestProcessing 
            WHERE rn = 1
            GROUP BY decision_status;
        """
        cur.execute(query)
        results = cur.fetchall()
        
        metrics = {row[0]: row[1] for row in results}
        return metrics
    except Exception as e:
        logger.error(f"Erro ao buscar métricas: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def get_latest_report():
    """Encontra o arquivo Excel GovTech mais recente na pasta exports."""
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    if not os.path.exists(export_dir):
        return None
        
    # Filtra apenas os relatórios com o novo prefixo
    files =[os.path.join(export_dir, f) for f in os.listdir(export_dir) if f.startswith('govtech_audit_report') and f.endswith('.xlsx')]
    if not files:
        return None
        
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

# ==============================================================================
# 3. FUNÇÃO PRINCIPAL (CORE DO NOTIFIER)
# ==============================================================================
def send_summary_email(execution_time_seconds=0):
    """Monta o e-mail HTML institucional, anexa o relatório e envia via SMTP."""
    logger.info("📧 Iniciando módulo de notificação GovTech...")
    
    metrics = get_execution_metrics()
    latest_report = get_latest_report()
    
    if not metrics:
        logger.warning("Nenhuma métrica encontrada para hoje. O e-mail não será enviado.")
        return

    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['sender_email']
    msg['To'] = SMTP_CONFIG['recipient_email']
    msg['Subject'] = f"🏛️ Relatório Diário de Auditoria PNCP - {datetime.now().strftime('%d/%m/%Y')}"

    html_body = f"""
    <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #333;">
            <h2 style="color: #1E293B;">Resumo de Auditoria - GovTech Compliance Bot</h2>
            <p>A extração e análise de integridade dos fornecedores do PNCP foi concluída com sucesso.</p>
            
            <div style="background-color: #F8FAFC; padding: 15px; border-radius: 5px; border-left: 4px solid #3B82F6;">
                <h3 style="margin-top: 0;">Métricas do Lote de Hoje:</h3>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 5px;">✅ <b>Fornecedores Aptos:</b> {metrics.get('Approved', 0)}</li>
                    <li style="margin-bottom: 5px;">⚠️ <b>Alerta (Diligência Necessária):</b> {metrics.get('Manual Review', 0)}</li>
                    <li style="margin-bottom: 5px;">❌ <b>Inidôneos / Risco Fiscal:</b> {metrics.get('Rejected', 0)}</li>
                    <li>⏳ <b>Falhas de Sistema (Fila):</b> {metrics.get('Pending', 0)}</li>
                </ul>
            </div>
            
            <p><b>Tempo total de execução do pipeline:</b> {round(execution_time_seconds, 2)} segundos.</p>
            <p>O dossiê analítico completo com os motivos de rejeição está em anexo.</p>
            <br>
            <p style="font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 10px;">
                Este é um e-mail automático gerado pelo sistema de Compliance GovTech. Não responda a este e-mail.
            </p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    if latest_report:
        try:
            with open(latest_report, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(latest_report)}",
            )
            msg.attach(part)
            logger.info(f"📎 Arquivo anexado: {os.path.basename(latest_report)}")
        except Exception as e:
            logger.error(f"Erro ao anexar arquivo: {e}")

    try:
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls()
        server.login(SMTP_CONFIG['sender_email'], SMTP_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ E-mail institucional enviado com sucesso para {SMTP_CONFIG['recipient_email']}!")
    except Exception as e:
        logger.critical(f"🚨 Falha crítica ao enviar e-mail: {e}")

if __name__ == "__main__":
    send_summary_email()