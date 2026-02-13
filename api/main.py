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

# Endpoint para testar o Dashboard
# PROVISÓRIO
@app.get("/analytics/overview")
async def get_analytics_overview():
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Lê da tabela 'bronze' 
        cursor.execute("SELECT count(*) as total_ingested FROM bronze")
        result = cursor.fetchone()
        return {"kpis": result}
    finally:
        if conn: conn.close()