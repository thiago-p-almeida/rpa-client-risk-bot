import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px # Opcional: para gráficos bonitos

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Risk Bot Analytics",
    page_icon="🤖",
    layout="wide"
)

# --- CONEXÃO SEGURA COM SUPABASE (ENTERPRISE GRADE) ---
try:
    # 1. Captura a URI dos Secrets
    DB_URI = st.secrets["connections"]["postgresql"]["url"]
    
    # 2. Correção de dialeto (SQLAlchemy 1.4+ exige 'postgresql://' e não 'postgres://')
    if DB_URI.startswith("postgres://"):
        DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

    # 3. Criação do Engine com Pool de Conexões Resiliente
    engine = create_engine(
        DB_URI,
        pool_size=5,          # Mantém até 5 conexões abertas (evita sobrecarga no Supabase)
        max_overflow=10,      # Permite até 10 conexões extras em picos de acesso
        pool_pre_ping=True,   # Verifica se a conexão está viva antes de executar a query
        pool_recycle=3600     # Recicla conexões a cada 1 hora para evitar timeouts silenciosos
    )
except KeyError:
    st.error("⚠️ Configuração de banco de dados não encontrada. Verifique os Secrets do Streamlit.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Erro crítico ao inicializar o banco de dados: {str(e)}")
    st.stop()

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=60)
def load_data():
    query = """
        SELECT 
            c.name AS "Cliente",
            r.risk_score AS "Score",
            r.decision_status AS "Decisão",
            r.processed_at AS "Data"
        FROM client_risk_processing r
        JOIN clients c ON r.client_id = c.client_id
        ORDER BY r.processed_at DESC
    """
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

@st.cache_data(ttl=60)
def load_pending_count():
    """Calcula o tamanho exato da fila de processamento do Robô."""
    query = """
        SELECT COUNT(*)
        FROM clients c
        LEFT JOIN client_risk_processing crp ON c.client_id = crp.client_id
        WHERE crp.client_id IS NULL OR crp.processing_status = 'Failed'
    """
    with engine.connect() as conn:
        return conn.execute(text(query)).scalar()

# Carregamento dos dados
df = load_data()
pending_count = load_pending_count()

if not df.empty:
    # 1. Métricas de Topo (Agora com 4 colunas)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Processado", len(df))
    m2.metric("⏳ Fila Pendente", pending_count)
    m3.metric("Média de Score", round(df["Score"].mean(), 1))
    m4.metric("Última Atualização", df["Data"].iloc[0].strftime("%H:%M:%S"))

# --- INTERFACE DO DASHBOARD ---
st.title("🛡️ Risk Analysis Control Panel")
st.markdown("Visualização em tempo real do processamento de risco via RPA.")

# Sidebar para filtros ou ações
with st.sidebar:
    st.header("⚙️ Controles")
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    st.info("Este dashboard consome dados em tempo real diretamente do Supabase PostgreSQL.")

    st.divider()
    st.info("👤 **Autor**: Thiago P. Almeida (Data Analyst Specialist)")
    st.info("🔗 [LinkedIn](https://www.linkedin.com/in/thiago-p-almeida/)")
    st.info("✉️ [E-mail](mailto:thiagoalmeida.tia@gmail.com)")

# Carregamento dos dados
df = load_data()

if not df.empty:
    # 1. Métricas de Topo
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Processado", len(df))
    m2.metric("Média de Score", round(df["Score"].mean(), 1))
    m3.metric("Última Atualização", df["Data"].iloc[0].strftime("%H:%M:%S"))

    st.divider()

    # 2. Visualização de Dados e Gráfico
    col_table, col_chart = st.columns([2, 1])

    with col_table:
        st.subheader("📋 Histórico de Processamento")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with col_chart:
        st.subheader("📊 Distribuição de Decisões")
        fig = px.pie(df, names="Decisão", color="Decisão", 
                     color_discrete_map={'Approved':'green', 'Rejected':'red', 'Manual Review':'orange'})
        st.plotly_chart(fig, use_container_width=True)

    # 3. Exportação (O valor do RPA)
    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Relatório Consolidado (CSV)",
        data=csv,
        file_name=f"risk_report_{df['Data'].iloc[0].strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.warning("Nenhum dado encontrado no banco de dados.")
