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
    """Busca no banco de dados o resumo das decisões tomadas hoje."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        query = """
            SELECT decision_status, COUNT(*) 
            FROM client_risk_processing 
            WHERE DATE(processed_at) = CURRENT_DATE
            GROUP BY decision_status;
        """
        cur.execute(query)
        results = cur.fetchall()
        
        # Converte a lista de tuplas em um dicionário
        metrics = {row[0]: row[1] for row in results}
        return metrics
    except Exception as e:
        logger.error(f"Erro ao buscar métricas: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def get_latest_report():
    """Encontra o arquivo Excel mais recente na pasta exports."""
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'exports')
    if not os.path.exists(export_dir):
        return None
        
    files =[os.path.join(export_dir, f) for f in os.listdir(export_dir) if f.endswith('.xlsx')]
    if not files:
        return None
        
    # Retorna o arquivo modificado mais recentemente
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

# ==============================================================================
# 3. FUNÇÃO PRINCIPAL (CORE DO NOTIFIER)
# ==============================================================================
def send_summary_email(execution_time_seconds=0):
    """Monta o e-mail HTML, anexa o relatório e envia via SMTP."""
    logger.info("📧 Iniciando módulo de notificação...")
    
    metrics = get_execution_metrics()
    latest_report = get_latest_report()
    
    if not metrics:
        logger.warning("Nenhuma métrica encontrada para hoje. O e-mail não será enviado.")
        return

    # Construção do E-mail HTML (Design Executivo)
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['sender_email']
    msg['To'] = SMTP_CONFIG['recipient_email']
    msg['Subject'] = f"📊 Relatório Diário de Risco RPA - {datetime.now().strftime('%d/%m/%Y')}"

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2>Resumo de Execução - Risk Bot RPA</h2>
            <p>O processamento diário de risco de clientes foi concluído com sucesso.</p>
            
            <h3>Métricas de Hoje:</h3>
            <ul>
                <li><b>Aprovados:</b> {metrics.get('Approved', 0)}</li>
                <li><b>Revisão Manual:</b> {metrics.get('Manual Review', 0)}</li>
                <li><b>Rejeitados:</b> {metrics.get('Rejected', 0)}</li>
                <li><b>Falhas de Sistema:</b> {metrics.get('Pending', 0)}</li>
            </ul>
            
            <p><b>Tempo total de execução:</b> {round(execution_time_seconds, 2)} segundos.</p>
            <p>O relatório analítico completo está em anexo.</p>
            <br>
            <p style="font-size: 12px; color: #888;">Este é um e-mail automático gerado pelo RPA Client Risk Bot.</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html'))

    # Anexando o arquivo Excel
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

    # Envio via SMTP
    try:
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls() # Criptografa a conexão
        server.login(SMTP_CONFIG['sender_email'], SMTP_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ E-mail enviado com sucesso para {SMTP_CONFIG['recipient_email']}!")
    except Exception as e:
        logger.critical(f"🚨 Falha crítica ao enviar e-mail: {e}")

if __name__ == "__main__":
    send_summary_email()