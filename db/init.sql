-- ENUMS PARA PADRONIZAÇÃO DE STATUS

CREATE TYPE status_enum    AS ENUM ('PROCESSING', 'COMPLETED', 'FAILED', 'CANCELED');
CREATE TYPE status_enum_PT AS ENUM ('SUCESSO', 'FALHOU', 'EM_PROCESSAMENTO', 'CANCELADO');

--  TABELA DE SEED
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

--  TABELA BRONZE (Dados Brutos)

CREATE TABLE IF NOT EXISTS bronze (
    id UUID PRIMARY KEY,
    id_workspace UUID NOT NULL,
    workspace_name TEXT NOT NULL,
    total_contacts INTEGER NOT NULL CHECK (total_contacts >= 0),
    contact_type TEXT NOT NULL,
    status status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    
    -- Dados de Controle 
    dw_ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Data de Insert
    dw_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP   -- Data de Upsert
);

-- Indice para acelerar a busca incremental 
CREATE INDEX IF NOT EXISTS idx_bronze_updated_at ON bronze(updated_at);

CREATE INDEX IF NOT EXISTS idx_bronze_workspace_updated 
ON bronze(id_workspace, updated_at);

-- Trigger para atualizar automaticamente dw_updated_at em UPDATE
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

-- TABELA GOLD (Dados Tratados)

CREATE TABLE IF NOT EXISTS gold (
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

-- Indices para performance do Dashboard
CREATE INDEX IF NOT EXISTS idx_gold_workspace ON gold(id_workspace);
CREATE INDEX IF NOT EXISTS idx_gold_status ON gold(status_processamento);
CREATE INDEX IF NOT EXISTS idx_gold_data_criacao ON gold(data_criacao);

-- TABELA DE CONTROLE 

CREATE TABLE IF NOT EXISTS estado_pipeline_dw (
    nome_pipeline VARCHAR(50) PRIMARY KEY,            -- Nome (bronze ou gold)
    data_ultimo_processo TIMESTAMPTZ NOT NULL,        -- Data da última execução com sucesso
    valor_marcador TEXT NOT NULL,                     -- O valor do marcador (pode ser data ou ID)
    status TEXT NOT NULL,                             
    total_registros_processados INTEGER NOT NULL DEFAULT 0 CHECK (total_registros_processados >= 0)
);


-- Inseririndo estados iniciais
INSERT INTO estado_pipeline_dw (nome_pipeline, data_ultimo_processo, valor_marcador, status)
VALUES 
    ('bronze', '1970-01-01 00:00:00+00', '1970-01-01T00:00:00Z', 'CANCELADO'),
    ('gold', '1970-01-01 00:00:00+00', '1970-01-01T00:00:00Z', 'CANCELADO')
ON CONFLICT (nome_pipeline) DO NOTHING;