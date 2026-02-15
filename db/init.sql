-- 1. ENUMS (Padronizados conforme requisitos da Gold) [cite: 160-164]
CREATE TYPE status_enum    AS ENUM ('PROCESSING', 'COMPLETED', 'FAILED', 'CANCELED');
CREATE TYPE status_enum_PT AS ENUM ('CONCLUIDO', 'FALHOU', 'EM_PROCESSAMENTO', 'CANCELADO');

-- Novo Enum para Tradução de Tipo de Contato 
CREATE TYPE tipo_contato_enum_PT AS ENUM ('PESSOA', 'EMPRESA');

-- 2. TABELA DE SEED (Fonte para a API) [cite: 101, 171]
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

-- 3. TABELA BRONZE (Captura Fiel) [cite: 116-121]
CREATE TABLE IF NOT EXISTS bronze (
    id UUID PRIMARY KEY,
    id_workspace UUID NOT NULL,
    workspace_name TEXT NOT NULL,
    total_contacts INTEGER NOT NULL,
    contact_type TEXT NOT NULL,
    status status_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    
    -- Campos Obrigatórios de Controle [cite: 121-124]
    dw_ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Trigger para atualização automática do timestamp na Bronze [cite: 124]
CREATE OR REPLACE FUNCTION update_dw_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.dw_updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_dw_timestamp
BEFORE UPDATE ON bronze
FOR EACH ROW EXECUTE FUNCTION update_dw_timestamp();

-- 4. TABELA GOLD (Dados Processados e Traduzidos) [cite: 126-129]
CREATE TABLE IF NOT EXISTS gold (
    id_enriquecimento UUID PRIMARY KEY REFERENCES bronze(id),  -- [cite: 131]
    id_workspace UUID NOT NULL,                                -- [cite: 134]
    nome_workspace TEXT NOT NULL,                              -- [cite: 136]
    
    total_contatos INTEGER NOT NULL,                           -- [cite: 138]
    tipo_contato tipo_contato_enum_PT NOT NULL,                -- [cite: 140, 156]
    status_processamento status_enum_PT NOT NULL,              -- [cite: 141, 160]
    
    data_criacao TIMESTAMPTZ NOT NULL,                         -- [cite: 143]
    data_atualizacao TIMESTAMPTZ NOT NULL,                     -- [cite: 146]
    
    -- Campos Calculados [cite: 147]
    duracao_processamento_minutos NUMERIC(10,2),               -- [cite: 148]
    tempo_por_contato_minutos NUMERIC(10,4),                   -- [cite: 149]
    processamento_sucesso BOOLEAN NOT NULL,                    -- [cite: 150]
    categoria_tamanho_job TEXT CHECK (categoria_tamanho_job IN ('PEQUENO', 'MEDIO', 'GRANDE', 'MUITO_GRANDE')), -- [cite: 151]
    necessita_reprocessamento BOOLEAN NOT NULL,                -- [cite: 165]
    
    -- Snapshot de Processamento [cite: 166]
    data_atualizacao_dw TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. TABELA DE ESTADO (Orquestração n8n) [cite: 170, 198]
CREATE TABLE IF NOT EXISTS estado_pipeline_dw (
    nome_pipeline VARCHAR(50) PRIMARY KEY,
    data_ultimo_processo TIMESTAMPTZ NOT NULL,
    valor_marcador TEXT NOT NULL,
    status TEXT NOT NULL,                             
    total_registros_processados INTEGER NOT NULL DEFAULT 0
);

-- Inicialização dos Marcadores (Watermark) [cite: 175]
INSERT INTO estado_pipeline_dw (nome_pipeline, data_ultimo_processo, valor_marcador, status)
VALUES 
    ('bronze', '1970-01-01 00:00:00+00', '0', 'AGUARDANDO'),
    ('gold', '1970-01-01 00:00:00+00', '0', 'AGUARDANDO')
ON CONFLICT DO NOTHING;