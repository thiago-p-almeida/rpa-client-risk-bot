import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS CUSTOMIZADO (GOVTECH UI)
# ==============================================================================
st.set_page_config(page_title="GovTech Compliance Radar", page_icon="🏛️", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
        .metric-card {
            background-color: #262730;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .metric-title {
            color: #A0AEC0;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            color: #F8FAFC;
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }
        .border-blue   { border-left: 6px solid #3B82F6; } /* Pending */
        .border-green  { border-left: 6px solid #10B981; } /* Approved */
        .border-yellow { border-left: 6px solid #F59E0B; } /* Manual Review */
        .border-red    { border-left: 6px solid #EF4444; } /* Rejected */
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==============================================================================
# 2. CONEXÃO SEGURA COM SUPABASE
# ==============================================================================
try:
    DB_URI = st.secrets["connections"]["postgresql"]["url"]
    if DB_URI.startswith("postgres://"):
        DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

    engine = create_engine(
        DB_URI,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600
    )
except Exception as e:
    st.error(f"🚨 Erro crítico ao inicializar o banco de dados: {str(e)}")
    st.stop()

# ==============================================================================
# 3. EXTRAÇÃO DE DADOS (COMPLIANCE AUDIT TRAIL)
# ==============================================================================
@st.cache_data(ttl=30)
def load_data():
    """Busca o último status de compliance de cada fornecedor."""
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
            COALESCE(lp.decision_status, 'Pending') AS "Status",
            lp.error_message AS "Motivo / Alerta",
            lp.processed_at AS "Data Auditoria"
        FROM vendors v
        LEFT JOIN LatestProcessing lp ON v.cnpj = lp.cnpj AND lp.rn = 1
        ORDER BY lp.processed_at DESC NULLS LAST;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ==============================================================================
# 4. INTERFACE DO OBSERVATÓRIO (VIEW)
# ==============================================================================
st.title("🏛️ GovTech Compliance Radar")
st.markdown("Observatório em tempo real de integridade de fornecedores de licitações públicas (PNCP).")

with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Atualizar Radar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("👤 **Autor**: Thiago P. Almeida\n\n🔗 [LinkedIn](https://www.linkedin.com/in/thiago-p-almeida/)")

df = load_data()

if not df.empty:
    # --- CÁLCULO DOS KPIS ---
    count_pending = len(df[df["Status"] == "Pending"])
    count_approved = len(df[df["Status"] == "Approved"])
    count_manual = len(df[df["Status"] == "Manual Review"])
    count_rejected = len(df[df["Status"] == "Rejected"])

    # --- RENDERIZAÇÃO DOS CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
            <div class="metric-card border-blue">
                <div class="metric-title">⏳ Fila de Auditoria</div>
                <div class="metric-value">{count_pending}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
            <div class="metric-card border-green">
                <div class="metric-title">✅ Fornecedores Aptos</div>
                <div class="metric-value">{count_approved}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
            <div class="metric-card border-yellow">
                <div class="metric-title">⚠️ Alerta (Diligência)</div>
                <div class="metric-value">{count_manual}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
            <div class="metric-card border-red">
                <div class="metric-title">❌ Inidôneos / Risco</div>
                <div class="metric-value">{count_rejected}</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- TABELA E GRÁFICO ---
    col_table, col_chart = st.columns([2, 1])

    with col_table:
        st.subheader("📋 Dossiê de Fornecedores (PNCP)")
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    with col_chart:
        st.subheader("📊 Matriz de Risco")
        color_map = {
            'Pending': '#3B82F6', 
            'Approved': '#10B981', 
            'Manual Review': '#F59E0B', 
            'Rejected': '#EF4444'
        }
        fig = px.pie(df, names="Status", color="Status", color_discrete_map=color_map, hole=0.4)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Nenhum fornecedor encontrado no banco de dados.")