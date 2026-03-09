-- Habilita extensão para UUID caso decida usar IDs mais seguros no futuro
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tabela Mestra (Cadastro de Clientes)
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL, 
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Processamento de Risco (Transacional)
CREATE TABLE IF NOT EXISTS client_risk_processing (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 1000),
    
    -- Status da Decisão de Negócio
    decision_status VARCHAR(50) DEFAULT 'Pending' 
        CHECK (decision_status IN ('Approved', 'Rejected', 'Manual Review', 'Pending')),
    
    -- Status do Fluxo de Automação
    processing_status VARCHAR(50) DEFAULT 'Pending' 
        CHECK (processing_status IN ('Pending', 'Processing', 'Completed', 'Failed')),
    
    processing_attempts INTEGER DEFAULT 0,
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_client
        FOREIGN KEY (client_id)
        REFERENCES clients (client_id)
        ON DELETE CASCADE
);

-- 3. Índices Estratégicos
-- Acelera a busca de dados do cliente
CREATE INDEX IF NOT EXISTS idx_clients_client_id ON clients(client_id);

-- Acelera a fila do Robô (Busca registros que precisam de processamento)
CREATE INDEX IF NOT EXISTS idx_processing_queue 
ON client_risk_processing(processing_status, created_at) 
WHERE processing_status = 'Pending';

-- 4. Automação de Timestamps (Trigger)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
