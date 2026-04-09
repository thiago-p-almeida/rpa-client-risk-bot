-- ==============================================================================
-- FASE 1: LIMPEZA DO AMBIENTE (HARD RESET PARA PIVOTAGEM)
-- ==============================================================================
DROP TABLE IF EXISTS client_risk_processing CASCADE;
DROP TABLE IF EXISTS clients CASCADE;

-- ==============================================================================
-- FASE 2: CRIAÇÃO DO NOVO SCHEMA GOVTECH (COMPLIANCE & AUDIT)
-- ==============================================================================

-- 1. Tabela Mestra (Cadastro de Fornecedores / Vendors)
CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(14) UNIQUE NOT NULL, -- Apenas números, sem pontuação
    razao_social VARCHAR(255) NOT NULL, 
    cnae_principal VARCHAR(50), -- Código da atividade econômica da empresa
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Trilha de Auditoria (Append-Only)
CREATE TABLE IF NOT EXISTS compliance_audit_trail (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(14) NOT NULL,
    bid_id VARCHAR(100), -- ID da Licitação/Edital (Contexto da análise)
    compliance_score INTEGER CHECK (compliance_score >= 0 AND compliance_score <= 1000),
    
    -- Status da Decisão do Agente Público / Motor de Regras
    decision_status VARCHAR(50) DEFAULT 'Pending' 
        CHECK (decision_status IN ('Approved', 'Rejected', 'Manual Review', 'Pending')),
    
    -- Status do Fluxo do Robô RPA
    processing_status VARCHAR(50) DEFAULT 'Pending' 
        CHECK (processing_status IN ('Pending', 'Processing', 'Completed', 'Failed')),
    
    processing_attempts INTEGER DEFAULT 0,
    error_message TEXT,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_vendor
        FOREIGN KEY (cnpj)
        REFERENCES vendors (cnpj)
        ON DELETE CASCADE
);

-- ==============================================================================
-- FASE 3: ÍNDICES DE ALTA PERFORMANCE
-- ==============================================================================
-- Acelera a busca de dados do fornecedor
CREATE INDEX IF NOT EXISTS idx_vendors_cnpj ON vendors(cnpj);

-- Acelera a fila do Robô (Busca registros que precisam de processamento)
CREATE INDEX IF NOT EXISTS idx_compliance_queue 
ON compliance_audit_trail(processing_status, created_at) 
WHERE processing_status = 'Pending';

-- ==============================================================================
-- FASE 4: TRIGGERS DE AUDITORIA
-- ==============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_vendors_updated_at
    BEFORE UPDATE ON vendors
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();