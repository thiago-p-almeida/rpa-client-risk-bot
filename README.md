# Automated Client Risk Bot (RPA + API)

![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-green?style=for-the-badge)
![Pandas](https://img.shields.io/badge/Pandas-2C2D72?style=for-the-badge&logo=pandas&logoColor=white)

Ecossistema completo de análise de risco de crédito, integrando um **Robô RPA**, uma **API REST** e um **Banco de Dados Relacional**. O sistema automatiza a consulta de clientes, cálculo de score e geração de relatórios executivos.

## Arquitetura do Projeto
- **Database (Postgres):** Armazena dados mestres e histórico de processamento.
- **API (Flask):** Engine de regras de negócio que calcula scores e persiste decisões.
- **RPA (Python):** Orquestrador de consumo da API e geração de relatórios (Pandas).

## Diferenciais Técnicos
- **Observabilidade:** Sistema de logging estruturado em arquivos `.log` para auditoria.
- **Performance:** PostgreSQL com **Triggers** e **Índices** otimizados para busca.
- **Isolamento:** Gerenciamento de dependências via **ambientes virtuais (venv)**.
- **Data Ingestion:** Script de semente (seed) para população inicial do banco.

## Estrutura
- `/api`: Servidor Flask e configurações de banco.
- `/rpa`: Scripts de ingestão, processamento e geração de relatórios.
- `/database`: Scripts SQL para criação do schema.
- `/logs`: Histórico de execução de todos os componentes.
- `/exports`: Relatórios gerados em Excel.

## Como Executar
1. Execute o script `database/create_tables.sql` no seu banco de dados.
2. Inicie a API: `cd api && python3 app.py`
3. Realize a ingestão inicial: `cd rpa && python3 ingestion.py`
4. Execute o processamento: `python3 processor.py`
5. Gere o relatório final: `python3 report_generator.py`

OBS: Renomeie o arquivo api/config.py.example para api/config.py e insira suas credenciais locais.

---
Desenvolvido por **Thiago Almeida**
