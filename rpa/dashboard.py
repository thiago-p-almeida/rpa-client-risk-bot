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

# --- CONEXÃO SEGURA COM SUPABASE ---
# No ambiente local, você pode substituir pela sua string temporariamente.
# Na nuvem (Streamlit Cloud), usaremos o Secrets Manager.
try:
    # Formato esperado: postgresql://user:password@host:port/dbname
    DB_URI = st.secrets["connections"]["postgresql"]["url"]
    engine = create_engine(DB_URI)
except Exception:
    st.error("⚠️ Configuração de banco de dados não encontrada. Verifique os Secrets.")
    st.stop()

# --- FUNÇÕES DE DADOS ---
@st.cache_data(ttl=60) # Atualiza o cache a cada 60 segundos
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
