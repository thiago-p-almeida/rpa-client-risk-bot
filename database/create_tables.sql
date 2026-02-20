-- Tabela de Cadastro (Dados Mestres)
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL, -- Aumentado para 255 por segurança
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Transações (Histórico de Risco)
CREATE TABLE IF NOT EXISTS client_risk_processing (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    risk_score INTEGER,
    decision_status VARCHAR(50),   -- 'Approved', 'Rejected', 'Manual Review'
    processing_status VARCHAR(50), -- 'Completed', 'Failed', 'Pending'
    processing_attempts INTEGER DEFAULT 0,
    error_message TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_client
        FOREIGN KEY (client_id)
        REFERENCES clients (client_id)
        ON DELETE CASCADE
);

-- Index para performance nas buscas do Robô
CREATE INDEX IF NOT EXISTS idx_clients_search ON clients(client_id);
