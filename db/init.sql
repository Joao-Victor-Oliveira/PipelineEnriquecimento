-- 1. ENUMS (Ajustado para bater com o PDF)
CREATE TYPE status_enum    AS ENUM ('PROCESSING', 'COMPLETED', 'FAILED', 'CANCELED');

-- ATENÇÃO: O PDF pede "CONCLUIDO" e não "SUCESSO"
CREATE TYPE status_enum_PT AS ENUM ('CONCLUIDO', 'FALHOU', 'EM_PROCESSAMENTO', 'CANCELADO');

-- 2. TABELA DE SEED (Caso você vá popular o banco para a API ler daqui)
CREATE TABLE IF NOT EXISTS api_enrichments_seed (
    id UUID PRIMARY KEY,
    id_workspace UUID NOT NULL,
    workspace_name TEXT NOT NULL,
    total_contacts INTEGER NOT NULL CHECK (total_contacts >= 0),
    contact_type TEXT NOT NULL,       
    status status_enum NOT NULL,             
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- 3. TABELA BRONZE (Dados Brutos)
CREATE TABLE IF NOT EXISTS bronze (
    id UUID PRIMARY KEY,
    id_workspace UUID NOT NULL,
    workspace_name TEXT NOT NULL,
    total_contacts INTEGER NOT NULL CHECK (total_contacts >= 0),
    contact_type TEXT NOT NULL,
    status status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    
    -- Dados de Controle do DW
    dw_ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indices Bronze
CREATE INDEX IF NOT EXISTS idx_bronze_updated_at ON bronze(updated_at);
CREATE INDEX IF NOT EXISTS idx_bronze_workspace_updated ON bronze(id_workspace, updated_at);

-- Trigger Bronze (Atualiza data de update automaticamente)
CREATE OR REPLACE FUNCTION update_dw_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.dw_updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_dw_timestamp
BEFORE UPDATE ON bronze
FOR EACH ROW
EXECUTE FUNCTION update_dw_timestamp();

-- 4. TABELA GOLD (Dados Tratados)
CREATE TABLE IF NOT EXISTS gold (
    -- PK da Gold é a mesma da Bronze (relação 1:1)
    id_enriquecimento UUID PRIMARY KEY REFERENCES bronze(id),  
    id_workspace UUID NOT NULL,                   
    nome_workspace TEXT NOT NULL,                 
    
    total_contatos INTEGER NOT NULL CHECK (total_contatos >= 0),              
    tipo_contato TEXT NOT NULL,                   
    status_processamento status_enum_PT NOT NULL,           
    
    data_criacao TIMESTAMPTZ NOT NULL,              
    data_atualizacao TIMESTAMPTZ NOT NULL,          
    
    -- Campos Calculados 
    duracao_processamento_minutos NUMERIC(10,4), 
    tempo_por_contato_minutos NUMERIC(10,4),     
    processamento_sucesso BOOLEAN NOT NULL,       
    categoria_tamanho_job TEXT,          
    necessita_reprocessamento BOOLEAN NOT NULL,   
    
    -- Dados de Controle
    data_atualizacao_dw TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indices Gold
CREATE INDEX IF NOT EXISTS idx_gold_workspace ON gold(id_workspace);
CREATE INDEX IF NOT EXISTS idx_gold_status ON gold(status_processamento);
CREATE INDEX IF NOT EXISTS idx_gold_data_criacao ON gold(data_criacao);

-- 5. TABELA DE CONTROLE (Estado do Pipeline)
CREATE TABLE IF NOT EXISTS estado_pipeline_dw (
    nome_pipeline VARCHAR(50) PRIMARY KEY,
    data_ultimo_processo TIMESTAMPTZ NOT NULL,
    valor_marcador TEXT NOT NULL,
    status TEXT NOT NULL,                             
    total_registros_processados INTEGER NOT NULL DEFAULT 0 CHECK (total_registros_processados >= 0)
);

-- 6. INICIALIZAÇÃO DE ESTADO 
INSERT INTO estado_pipeline_dw (nome_pipeline, data_ultimo_processo, valor_marcador, status)
VALUES 
    ('bronze', '1970-01-01 00:00:00+00', '1970-01-01T00:00:00Z', 'AGUARDANDO'),
    ('gold', '1970-01-01 00:00:00+00', '1970-01-01T00:00:00Z', 'AGUARDANDO')
ON CONFLICT (nome_pipeline) DO NOTHING;