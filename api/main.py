import os
import random
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Security, Query 
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import psycopg2
from psycopg2.extras import RealDictCursor

# 1. CONFIGURAÇÃO DE SEGURANÇA (Padrão Bearer Token) [cite: 68, 69, 70]
security = HTTPBearer()

try:
    API_KEY_REQUIRED = os.environ["API_KEY"]
    DB_HOST = os.environ["DB_HOST"]
    DB_USER = os.environ["DB_USER"]
    DB_PASS = os.environ["DB_PASS"]
    DB_NAME = os.environ["DB_NAME"]
except KeyError as e:
    raise RuntimeError(f"Erro de Configuração: A variável de ambiente {e} não foi encontrada.")

def verify_token(auth: HTTPAuthorizationCredentials = Security(security)):
    """Valida o token enviado no Header 'Authorization: Bearer <token>'"""
    if auth.credentials != API_KEY_REQUIRED:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")
    return auth.credentials

# 2. INSTÂNCIA DO APP COM DEPENDÊNCIA GLOBAL [cite: 67]
app = FastAPI(
    title="Desafio Pipeline de Enriquecimento",
    dependencies=[Depends(verify_token)]
)

# CONEXÃO AO BANCO [cite: 46, 53, 57]
def get_db_connection():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

# SEED: GERADOR DE DADOS CORRIGIDO [cite: 77, 101, 171]
@app.on_event("startup")
async def startup_event():
    print("Iniciando API... Aguardando Banco de Dados.")
    time.sleep(5) # Espera o Postgres subir [cite: 42]
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM api_enrichments_seed")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Populando banco com 5.000 registros simulados...")
            
            # Status e tipos permitidos conforme as regras [cite: 157, 159, 161-164]
            statuses = ['COMPLETED', 'COMPLETED', 'FAILED', 'PROCESSING', 'CANCELED']
            types = ['COMPANY', 'PERSON']
            
            sql = """
                INSERT INTO api_enrichments_seed 
                (id, id_workspace, workspace_name, total_contacts, contact_type, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch = []
            for _ in range(5000):
                # Criação aleatória nos últimos 30 dias
                created = datetime.now() - timedelta(
                    days=random.randint(1, 30), 
                    minutes=random.randint(0, 59)
                )
                
                # ATUALIZAÇÃO: Entre 5 e 120 minutos DEPOIS da criação 
                # Isso garante que a duração do processamento seja calculável
                processing_time = random.randint(5, 120)
                updated = created + timedelta(minutes=processing_time)
                
                batch.append((
                    str(uuid.uuid4()),
                    str(uuid.uuid4()),
                    f"Empresa {random.randint(1, 1000)} Ltda",
                    random.randint(10, 2000),
                    random.choice(types),
                    random.choice(statuses), 
                    created,
                    updated
                ))
            
            cursor.executemany(sql, batch)
            conn.commit()
            print(f"Seed concluído com sucesso! {len(batch)} registros inseridos.")
        else:
            print(f"Banco já contém {count} registros. Seed pulado.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro no startup: {e}")

# --- ENDPOINTS ---

@app.get("/people/v1/enrichments")
async def get_enrichments(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=100)
):
    """Endpoint de fonte simulado com paginação e meta-informações [cite: 72, 78, 80]"""
    if random.random() < 0.05: # Simulação de Rate Limit [cite: 79]
        raise HTTPException(status_code=429, detail="Too Many Requests")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        offset = (page - 1) * limit
        cursor.execute("SELECT count(*) as total FROM api_enrichments_seed")
        total_items = cursor.fetchone()['total']
        total_pages = (total_items + limit - 1) // limit
        
        cursor.execute("SELECT * FROM api_enrichments_seed ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
        items = cursor.fetchall()
        
        return {
            "meta": {
                "current_page": page,
                "items_per_page": limit,
                "total_items": total_items,
                "total_pages": total_pages
            },
            "data": items
        }
    finally:
        conn.close()

@app.get("/analytics/overview")
async def get_analytics_overview():
    """Retorna KPIs consolidados da camada Gold [cite: 105, 106, 112]"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
        SELECT 
            COUNT(*)::int as total_jobs,
            COALESCE(ROUND(AVG(duracao_processamento_minutos)::numeric, 2), 0) as tempo_medio_min,
            COALESCE(ROUND((COUNT(*) FILTER (WHERE processamento_sucesso = TRUE) * 100.0 / NULLIF(COUNT(*), 0))::numeric, 2), 0) as taxa_sucesso_perc
        FROM gold;
        """
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.execute("SELECT categoria_tamanho_job as categoria, COUNT(*)::int as qtd FROM gold GROUP BY categoria_tamanho_job")
        distribuicao = {row['categoria']: row['qtd'] for row in cursor.fetchall()}
        return {
            "status": "success", 
            "data": {
                "total_enriquecimentos": result['total_jobs'], 
                "taxa_sucesso": f"{result['taxa_sucesso_perc']}%", 
                "tempo_medio_processamento": f"{result['tempo_medio_min']} min", 
                "grafico_distribuicao": distribuicao
            }
        }
    finally:
        conn.close()

@app.get("/analytics/enrichments")
async def get_analytics_enrichments(limit: int = 10, offset: int = 0, status: Optional[str] = None):
    """Lista enriquecimentos da camada Gold com filtros [cite: 107, 108]"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM gold "
        params = []
        if status:
            sql += " WHERE status_processamento = %s "
            params.append(status)
        sql += " ORDER BY data_criacao DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    finally:
        conn.close()

@app.get("/analytics/summary")
async def get_analytics_summary():
    """Resumo para gráficos do Dashboard [cite: 203]"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) as total, AVG(duracao_processamento_minutos) as media FROM gold")
        res = cursor.fetchone()
        cursor.execute("SELECT categoria_tamanho_job, COUNT(*) as qtd FROM gold GROUP BY categoria_tamanho_job")
        categorias = cursor.fetchall()
        cursor.execute("SELECT status_processamento, COUNT(*) as qtd FROM gold GROUP BY status_processamento")
        status = cursor.fetchall()
        return {
            "total_jobs": res['total'], 
            "tempo_medio": round(res['media'] or 0, 2), 
            "categorias": categorias, 
            "status": status
        }
    finally:
        conn.close()

@app.get("/analytics/workspaces/top")
async def get_top_workspaces(limit: int = Query(5, le=20)):
    """Ranking bônus de workspaces [cite: 109, 110]"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """
            SELECT nome_workspace, COUNT(*) as total_jobs, SUM(total_contatos) as volume_contatos 
            FROM gold 
            GROUP BY nome_workspace 
            ORDER BY volume_contatos DESC 
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        return {"status": "success", "data": cursor.fetchall()}
    finally:
        conn.close()