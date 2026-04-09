import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS CUSTOMIZADO (ENTERPRISE UI)
# ==============================================================================
st.set_page_config(page_title="Risk Bot Analytics", page_icon="🤖", layout="wide")

# Injeção de CSS para criar os Cards Sóbrios e Responsivos
def inject_custom_css():
    st.markdown("""
        <style>
        /* Estilo base do Card */
        .metric-card {
            background-color: #262730;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Título do Card */
        .metric-title {
            color: #A0AEC0;
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        /* Valor do Card */
        .metric-value {
            color: #F8FAFC;
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }
        /* Cores das Bordas (Paleta Slate & Signal) */
        .border-blue   { border-left: 6px solid #3B82F6; } /* Pending */
        .border-green  { border-left: 6px solid #10B981; } /* Approved */
        .border-yellow { border-left: 6px solid #F59E0B; } /* Manual Review */
        .border-red    { border-left: 6px solid #EF4444; } /* Rejected */
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ==============================================================================
# 2. CONEXÃO SEGURA COM SUPABASE (RESILIENTE)
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
# 3. EXTRAÇÃO DE DADOS (DATA INTEGRITY & CTE)
# ==============================================================================
@st.cache_data(ttl=30) # Cache reduzido para 30s para maior tempo real
def load_data():
    """
    Usa uma CTE para buscar apenas o ÚLTIMO status de cada cliente,
    eliminando duplicidades geradas pela trilha de auditoria (retries).
    """
    query = """
        WITH LatestProcessing AS (
            SELECT client_id, risk_score, decision_status, processed_at,
                   ROW_NUMBER() OVER(PARTITION BY client_id ORDER BY processed_at DESC) as rn
            FROM client_risk_processing
        )
        SELECT 
            c.client_id AS "ID",
            c.name AS "Cliente",
            lp.risk_score AS "Score",
            COALESCE(lp.decision_status, 'Pending') AS "Decisão",
            lp.processed_at AS "Data"
        FROM clients c
        LEFT JOIN LatestProcessing lp ON c.client_id = lp.client_id AND lp.rn = 1
        ORDER BY lp.processed_at DESC NULLS LAST;
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# ==============================================================================
# 4. INTERFACE DO DASHBOARD (VIEW)
# ==============================================================================
st.title("🛡️ Risk Analysis Control Panel")
st.markdown("Visualização executiva em tempo real do ecossistema de risco.")

with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("👤 **Autor**: Thiago P. Almeida\n\n🔗 [LinkedIn](https://www.linkedin.com/in/thiago-p-almeida/)")

df = load_data()

if not df.empty:
    # --- CÁLCULO DOS KPIS ---
    count_pending = len(df[df["Decisão"] == "Pending"])
    count_approved = len(df[df["Decisão"] == "Approved"])
    count_manual = len(df[df["Decisão"] == "Manual Review"])
    count_rejected = len(df[df["Decisão"] == "Rejected"])

    # --- RENDERIZAÇÃO DOS CARDS CUSTOMIZADOS ---
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.markdown(f"""
            <div class="metric-card border-blue">
                <div class="metric-title">⏳ Fila Pendente</div>
                <div class="metric-value">{count_pending}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
            <div class="metric-card border-green">
                <div class="metric-title">✅ Aprovados</div>
                <div class="metric-value">{count_approved}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
            <div class="metric-card border-yellow">
                <div class="metric-title">⚠️ Revisão Manual</div>
                <div class="metric-value">{count_manual}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
            <div class="metric-card border-red">
                <div class="metric-title">❌ Rejeitados</div>
                <div class="metric-value">{count_rejected}</div>
            </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- TABELA E GRÁFICO ---
    col_table, col_chart = st.columns([2, 1])

    with col_table:
        st.subheader("📋 Posição Atual dos Clientes")
        # Mostra a tabela limpa (sem duplicatas)
        st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    with col_chart:
        st.subheader("📊 Distribuição Global")
        # Paleta de cores sincronizada com os cards
        color_map = {
            'Pending': '#3B82F6', 
            'Approved': '#10B981', 
            'Manual Review': '#F59E0B', 
            'Rejected': '#EF4444'
        }
        fig = px.pie(df, names="Decisão", color="Decisão", color_discrete_map=color_map, hole=0.4)
        fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Nenhum dado encontrado no banco de dados.")