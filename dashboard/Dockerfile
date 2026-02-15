# 1. Usar uma imagem Python leve e estável
FROM python:3.11-slim

# 2. Configurar variáveis de ambiente do Python
# Evita que o Python gere arquivos .pyc e garante que o log saia em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Instalar dependências do sistema para o driver do PostgreSQL (psycopg2)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 4. Definir o diretório de trabalho dentro do container
WORKDIR /app

# 5. Instalar as dependências do projeto
RUN pip install --no-cache-dir \
    django \
    psycopg2-binary \
    dj-database-url \
    requests \
    whitenoise


COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]