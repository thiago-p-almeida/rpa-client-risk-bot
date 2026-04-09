import os
import logging
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime
from config import DB_CONFIG

# ==============================================================================
# 1. CONFIGURAÇÃO DE LOGS E AMBIENTE
# ==============================================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'api.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ==============================================================================
# 2. MOTOR DE REGRAS DE COMPLIANCE (GOVTECH)
# ==============================================================================
def calculate_compliance_score(vendor_data):
    """
    Analisa os dados públicos da empresa e retorna um Score (0-1000) e uma Decisão.
    Regras baseadas em Compliance B2G (Business-to-Government).
    """
    score = 1000
    reasons =[]

    # Regra 1: Status na Receita Federal (Fator Eliminatório)
    status = str(vendor_data.get('descricao_situacao_cadastral', '')).upper()
    if status != 'ATIVA':
        return 0, 'Rejected', f"CNPJ Inativo/Baixado (Status: {status})"

    # Regra 2: Idade da Empresa (Prevenção contra Empresas de Fachada)
    data_inicio = vendor_data.get('data_inicio_atividade')
    if data_inicio:
        try:
            # Formato da Brasil API: YYYY-MM-DD
            abertura = datetime.strptime(data_inicio, '%Y-%m-%d')
            idade_anos = (datetime.now() - abertura).days / 365
            if idade_anos < 1:
                score -= 500
                reasons.append("Empresa com menos de 1 ano de abertura")
            elif idade_anos < 3:
                score -= 200
                reasons.append("Empresa jovem (menos de 3 anos)")
        except Exception:
            pass

    # Regra 3: Capital Social (Capacidade Econômico-Financeira)
    capital = vendor_data.get('capital_social', 0)
    if capital == 0:
        score -= 300
        reasons.append("Capital Social zerado ou não informado")
    elif capital < 50000:
        score -= 100
        reasons.append("Capital Social baixo (< R$ 50k)")

    # Árvore de Decisão Final
    if score >= 800:
        decision = 'Approved'
    elif score >= 500:
        decision = 'Manual Review'
    else:
        decision = 'Rejected'

    reason_str = " | ".join(reasons) if reasons else "Apto para contratação"
    return score, decision, reason_str

# ==============================================================================
# 3. ENDPOINTS DA API
# ==============================================================================
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"service": "GovTech Compliance API", "status": "online"}), 200

@app.route("/risk-score", methods=["POST"])
def risk_score():
    """Recebe o dossiê da empresa, calcula o risco e grava a trilha de auditoria."""
    data = request.get_json()

    if not data or "cnpj" not in data:
        return jsonify({"status": "error", "message": "CNPJ is required"}), 400

    cnpj = data["cnpj"]
    vendor_data = data.get("vendor_data", {}) # Dossiê vindo da Brasil API

    # Passa o dossiê pelo Motor de Regras
    score, decision, reason = calculate_compliance_score(vendor_data)

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Validar existência do fornecedor
        cur.execute("SELECT razao_social FROM vendors WHERE cnpj = %s", (cnpj,))
        vendor_record = cur.fetchone()
        
        if not vendor_record:
            return jsonify({"status": "error", "message": f"Vendor {cnpj} not found."}), 404

        razao_social = vendor_record[0]

        # 2. Registrar Trilha de Auditoria (Append-Only)
        insert_query = """
            INSERT INTO compliance_audit_trail 
            (cnpj, compliance_score, decision_status, processing_status, error_message, processed_at, processing_attempts)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (
            cnpj, score, decision, 'Completed', reason, datetime.now(), 1
        ))

        conn.commit()
        logger.info(f"✅ Compliance: {razao_social} ({cnpj}) | Score: {score} | Decisão: {decision} | Motivo: {reason}")

        return jsonify({
            "cnpj": cnpj,
            "compliance_score": score,
            "decision": decision,
            "reason": reason,
            "status": "success"
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.critical(f"🚨 Erro no banco para o CNPJ {cnpj}: {str(e)}")
        return jsonify({"status": "error", "message": "Internal database error"}), 500

    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    logger.info("Iniciando GovTech Compliance API na porta 5050...")
    app.run(debug=True, port=5050)