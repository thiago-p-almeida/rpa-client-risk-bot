# Automated Client Risk Bot (RPA + API + Dashboard)

![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-green?style=for-the-badge)
![Pandas](https://img.shields.io/badge/Pandas-2C2D72?style=for-the-badge&logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)

Ecossistema de análise de risco de crédito de ponta a ponta, integrando um **Robô RPA**, uma **API REST** um **Banco de Dados Relacional**. O sistema automatiza a consulta de clientes, calcula o score de cliente e gera relatórios executivos, apresentado em um Dashboard em Nuvem atualizado em tempo real para visualização executiva.

**Live Demo:** [Acessar Dashboard Cloud](https://rpa-client-risk-bot-thiago-p-almeida.streamlit.app)

## Arquitetura do Projeto
- **Cloud Database (Supabase):** Hosting do banco PostgreSQL com alta disponibilidade.
- **API (Flask):** Engine de regras de negócio que calcula scores e persiste decisões.
- **RPA (Python/Pandas):** Orquestrador de processos e ingestão de dados.
- **Frontend (Streamlit):** Dashboard de BI para análise de indicadores de risco.

## Diferenciais Técnicos
- **Observabilidade:** Sistema de logging estruturado em arquivos `.log` para auditoria.
- **Performance:** PostgreSQL com **Triggers** e **Índices** otimizados para busca.
- **Isolamento:** Gerenciamento de dependências via **ambientes virtuais (venv)**.
- **Data Ingestion:** Script de semente (seed) para população inicial do banco.

## Estrutura
- `/api`: Servidor Flask e regras de negócio.
  `/dashboard`: Código fonte da interface Streamlit.
- `/rpa`: Scripts de ingestão, processamento e geração de relatórios.
- `/database`: Schemas SQL e configurações Supabase.
- `/logs`: Histórico de execução de todos os componentes.
- `/exports`: Relatórios gerados em Excel/CSV.

## Como Executar
1. Configure as variáveis de ambiente renomeando o arquivo `api/config.py.example` para `api/config.py` com suas credenciais do Supabase.
2. Prepare o banco de dados executando o script `database/create_tables.sql` na sua instância do Supabase.
3. Inicie o servidor da API REST através do arquivo `api/app.py`.
4. Realize a ingestão inicial dos dados executando o script `rpa/ingestion.py`.
5. Execute o processamento de risco e cálculo de scores com o `rpa/processor.py`.
6. Visualize os resultados no Dashboard Interativo executando o `dashboard/app.py via Streamlit`.
7. Gere os relatórios executivos finais através do `rpa/report_generator.py`.

    OBS: Para segurança das credenciais do Supabase, utilize o sistema de **Secrets** do **Streamlit**.
    - Localmente: Crie a pasta `.streamlit/` na raiz do projeto e adicione o arquivo `secrets.toml` com suas chaves. Nunca envie este arquivo para o GitHub (adicione-o ao seu `.gitignore`).
    - No Streamlit Cloud: Vá em **Settings** > **Secrets** no painel do seu aplicativo e cole o conteúdo do seu arquivo `secrets.toml` diretamente no campo de texto para que a nuvem reconheça as variáveis de ambiente.

---
Desenvolvido por **Thiago P. Almeida**
