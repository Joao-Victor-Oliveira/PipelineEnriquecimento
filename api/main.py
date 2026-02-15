import os
import random
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Query # type: ignore
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Desafio Pipeline de Enriquecimento")

try:
    API_KEY_REQUIRED = os.environ["API_KEY"]
    DB_HOST = os.environ["DB_HOST"]
    DB_USER = os.environ["DB_USER"]
    DB_PASS = os.environ["DB_PASS"]
    DB_NAME = os.environ["DB_NAME"]
except KeyError as e:
    raise RuntimeError(f"Erro de Configuração: A variável de ambiente {e} não foi encontrada. Verifique seu docker-compose.yml e .env")

# CONEXÃO AO BANCO 
def get_db_connection():
    # Tenta conectar ao banco
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar no DB ({DB_HOST}): {e}")
        raise e

# SEED: GERADOR DE DADOS
@app.on_event("startup")
async def startup_event():
    #Verifica se a tabela seed está vazia, se estiver popula ela
    print("Iniciando API... Aguardando Banco de Dados.")
    time.sleep(5) # Espera o Postgres subir e rodar o init.sql
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verifica se já tem dados
        cursor.execute("SELECT count(*) FROM api_enrichments_seed")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Populando banco com 5.000 registros simulados...")
            
            statuses = ['COMPLETED', 'COMPLETED', 'COMPLETED', 'FAILED', 'PROCESSING', 'CANCELED']
            types = ['COMPANY', 'COMPANY', 'COMPANY', 'PERSON']
            
            sql = """
                INSERT INTO api_enrichments_seed 
                (id, id_workspace, workspace_name, total_contacts, contact_type, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            batch = []
            for _ in range(5000):
                created = datetime.now() - timedelta(days=random.randint(0, 30))
                
                updated = created + timedelta(minutes=random.randint(1, 120))
                
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
            print("Seed concluído com sucesso!")
        else:
            print(f"Banco já contem {count} registros. Seed pulado.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro crítico no startup: {e}")

# ENDPOINTS

def verify_token(authorization: str):
    if not authorization or authorization != f"Bearer {API_KEY_REQUIRED}":
        raise HTTPException(status_code=401, detail="Unauthorized")

# Simulação da API de Enriquecimento
@app.get("/people/v1/enrichments")
async def get_enrichments(
    authorization: Optional[str] = Header(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=100)
):
    verify_token(authorization)

    # Simulação de Rate Limit (Erro 429) - 5% de chance
    if random.random() < 0.05:
        raise HTTPException(status_code=429, detail="Too Many Requests - Simulação")

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Paginação via SQL
        offset = (page - 1) * limit
        
        # Contagem total para metadados
        cursor.execute("SELECT count(*) as total FROM api_enrichments_seed")
        total_items = cursor.fetchone()['total']
        total_pages = (total_items + limit - 1) // limit
        
        # Busca paginada
        query = """
            SELECT * FROM api_enrichments_seed 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """
        cursor.execute(query, (limit, offset))
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
        if conn: conn.close()


@app.get("/analytics/overview")
async def get_analytics_overview():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            COUNT(*)::int as total_jobs,
            COALESCE(ROUND(AVG(duracao_processamento_minutos)::numeric, 2), 0) as tempo_medio_min,
            COALESCE(ROUND(
                (COUNT(*) FILTER (WHERE processamento_sucesso = TRUE) * 100.0 / NULLIF(COUNT(*), 0))::numeric, 
                2
            ), 0) as taxa_sucesso_perc
        FROM gold;
        """
        cursor.execute(query)
        result = cursor.fetchone()

        # Query separada para a distribuição 
        cursor.execute("SELECT categoria_tamanho_job as categoria, COUNT(*)::int as qtd FROM gold GROUP BY categoria_tamanho_job")
        dist_rows = cursor.fetchall()
        distribuicao = {row['categoria']: row['qtd'] for row in dist_rows}
        
        return {
            "status": "success",
            "data": {
                "total_enriquecimentos": result['total_jobs'],
                "taxa_sucesso": f"{result['taxa_sucesso_perc']}%",
                "tempo_medio_processamento": f"{result['tempo_medio_min']} min",
                "grafico_distribuicao": distribuicao
            }
        }
    except Exception as e:
        print(f"Erro no Analytics: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        if conn: conn.close()

@app.get("/analytics/enrichments")
async def get_analytics_enrichments(
    limit: int = 10, 
    offset: int = 0, 
    status: Optional[str] = None
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Base da consulta na camada Gold [cite: 131-146]
        sql = "SELECT * FROM gold "
        params = []

        # Se houver filtro de status, adicionamos a cláusula WHERE [cite: 108]
        if status:
            sql += " WHERE status_processamento = %s "
            params.append(status)

        sql += " ORDER BY data_criacao DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(sql, tuple(params))
        return cursor.fetchall()
    finally:
        if conn: conn.close()

@app.get("/analytics/summary")
async def get_analytics_summary():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Total e Tempo Médio
        cursor.execute("SELECT COUNT(*) as total, AVG(duracao_processamento_minutos) as media FROM gold")
        res = cursor.fetchone()
        
        # 2. Distribuição por Categoria
        cursor.execute("SELECT categoria_tamanho_job, COUNT(*) as qtd FROM gold GROUP BY categoria_tamanho_job")
        categorias = cursor.fetchall()
        
        # 3. Distribuição por Status
        cursor.execute("SELECT status_processamento, COUNT(*) as qtd FROM gold GROUP BY status_processamento")
        status = cursor.fetchall()

        return {
            "total_jobs": res['total'],
            "tempo_medio": round(res['media'] or 0, 2),
            "categorias": categorias,
            "status": status
        }
    finally:
        if conn: conn.close()

@app.get("/analytics/workspaces/top")
async def get_top_workspaces(limit: int = Query(5, le=20)):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT nome_workspace, 
                   COUNT(*) as total_jobs,
                   SUM(total_contatos) as volume_contatos
            FROM gold 
            GROUP BY nome_workspace 
            ORDER BY volume_contatos DESC 
            LIMIT %s
        """
        cursor.execute(query, (limit,))
        ranking = cursor.fetchall()
        
        return {
            "status": "success",
            "data": ranking
        }
    finally:
        if conn: conn.close()