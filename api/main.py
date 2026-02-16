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

# 1. CONFIGURAÇÃO DE SEGURANÇA (Padrão Bearer Token)
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

# 2. INSTÂNCIA DO APP COM DEPENDÊNCIA GLOBAL
# Adicionando a dependência aqui, todas as rotas ficam protegidas automaticamente!
app = FastAPI(
    title="Desafio Pipeline de Enriquecimento",
    dependencies=[Depends(verify_token)]
)

# CONEXÃO AO BANCO 
def get_db_connection():
    return psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

# SEED: GERADOR DE DADOS (Mantido igual)
@app.on_event("startup")
async def startup_event():
    print("Iniciando API... Aguardando Banco de Dados.")
    time.sleep(5)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM api_enrichments_seed")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Populando banco com 5.000 registros...")
            statuses = ['COMPLETED', 'COMPLETED', 'COMPLETED', 'FAILED', 'PROCESSING', 'CANCELED']
            types = ['COMPANY', 'COMPANY', 'COMPANY', 'PERSON']
            sql = """INSERT INTO api_enrichments_seed (id, id_workspace, workspace_name, total_contacts, contact_type, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            batch = [(str(uuid.uuid4()), str(uuid.uuid4()), f"Empresa {random.randint(1, 1000)} Ltda", random.randint(10, 2000), random.choice(types), random.choice(statuses), datetime.now() - timedelta(days=random.randint(0, 30)), datetime.now()) for _ in range(5000)]
            cursor.executemany(sql, batch)
            conn.commit()
            print("Seed concluído!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro no startup: {e}")

# --- ENDPOINTS (Sem necessidade de repetir verify_token dentro deles) ---

@app.get("/people/v1/enrichments")
async def get_enrichments(page: int = Query(1, ge=1), limit: int = Query(50, le=100)):
    if random.random() < 0.05:
        raise HTTPException(status_code=429, detail="Too Many Requests - Simulação")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        offset = (page - 1) * limit
        cursor.execute("SELECT count(*) as total FROM api_enrichments_seed")
        total_items = cursor.fetchone()['total']
        cursor.execute("SELECT * FROM api_enrichments_seed ORDER BY created_at DESC LIMIT %s OFFSET %s", (limit, offset))
        return {"meta": {"current_page": page, "total_items": total_items}, "data": cursor.fetchall()}
    finally:
        conn.close()

@app.get("/analytics/overview")
async def get_analytics_overview():
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
        return {"status": "success", "data": {"total_enriquecimentos": result['total_jobs'], "taxa_sucesso": f"{result['taxa_sucesso_perc']}%", "tempo_medio_processamento": f"{result['tempo_medio_min']} min", "grafico_distribuicao": distribuicao}}
    finally:
        conn.close()

@app.get("/analytics/enrichments")
async def get_analytics_enrichments(limit: int = 10, offset: int = 0, status: Optional[str] = None):
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) as total, AVG(duracao_processamento_minutos) as media FROM gold")
        res = cursor.fetchone()
        cursor.execute("SELECT categoria_tamanho_job, COUNT(*) as qtd FROM gold GROUP BY categoria_tamanho_job")
        categorias = cursor.fetchall()
        cursor.execute("SELECT status_processamento, COUNT(*) as qtd FROM gold GROUP BY status_processamento")
        status = cursor.fetchall()
        return {"total_jobs": res['total'], "tempo_medio": round(res['media'] or 0, 2), "categorias": categorias, "status": status}
    finally:
        conn.close()

@app.get("/analytics/workspaces/top")
async def get_top_workspaces(limit: int = Query(5, le=20)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        query = """SELECT nome_workspace, COUNT(*) as total_jobs, SUM(total_contatos) as volume_contatos FROM gold GROUP BY nome_workspace ORDER BY volume_contatos DESC LIMIT %s"""
        cursor.execute(query, (limit,))
        return {"status": "success", "data": cursor.fetchall()}
    finally:
        conn.close()