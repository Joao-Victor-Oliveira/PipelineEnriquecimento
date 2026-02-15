Desafio Tech: Pipeline de Dados HubDriva
1. Contexto e Objetivo

Este projeto foi desenvolvido como parte de um teste técnico para a Driva. O objetivo central é fornecer ao time de Visibilidade uma ferramenta para monitorar a performance e a qualidade dos processos de Enriquecimento de Dados do HubDriva.

A solução consiste em uma pipeline automatizada que coleta dados brutos de uma API, processa-os em camadas de Data Warehouse e os disponibiliza em um dashboard analítico.

O que o projeto faz:

    Ingestão: Coleta periódica de dados de enriquecimento via n8n.

    Tratamento: Organização dos dados nas camadas Bronze (brutos) e Gold (processados e traduzidos).

    Exposição: Uma API robusta que serve dados analíticos.

    Visualização: Um dashboard para acompanhamento de KPIs como taxa de sucesso e tempo de processamento.

2. Como Rodar o Projeto
Pré-requisitos

    Docker e Docker Compose instalados.

    Arquivo .env configurado com a API_KEY (utilize: driva_test_key_abc123xyz789).

Passo a Passo

    Clone o repositório.

    No terminal, execute o comando para subir todos os serviços:
    Bash

    docker-compose up -d --build

    Acesso aos Serviços:

        Dashboard: http://localhost:8000.

        API (Swagger): http://localhost:3000/docs.

        n8n: http://localhost:5678 (Login: admin / admin).

    Importação do n8n: Importe os arquivos JSON fornecidos na pasta /n8n para o ambiente local do n8n para ativar a pipeline.

3. Testando a API (Exemplos cURL)

Toda a comunicação com a API exige o Header de Autorização:
Authorization: Bearer driva_test_key_abc123xyz789.

Verificar KPIs Gerais (Overview):
Bash

curl -X GET "http://localhost:3000/analytics/overview" \
     -H "Authorization: Bearer driva_test_key_abc123xyz789"

Listar Enriquecimentos na Camada Gold (com filtro):
Bash

curl -X GET "http://localhost:3000/analytics/enrichments?status=CONCLUIDO&limit=5" \
     -H "Authorization: Bearer driva_test_key_abc123xyz789"

Ranking de Workspaces (Bônus):
Bash

curl -X GET "http://localhost:3000/analytics/workspaces/top" \
     -H "Authorization: Bearer driva_test_key_abc123xyz789"

4. Detalhes Técnicos e Decisões

Arquitetura Medalhão 

    Camada Bronze: Armazena os dados exatamente como vieram da API, garantindo a rastreabilidade com os campos dw_ingested_at e dw_updated_at.

    Camada Gold: É a "única fonte da verdade" para o negócio. Aqui, todos os nomes de colunas e valores foram traduzidos para o português (ex: status para status_processamento).

Regras de Negócio Implementadas na Gold

    Cálculo de Eficiência: Criado o campo tempo_por_contato_minutos para medir a velocidade real de processamento.

    Categorização: Os jobs são classificados automaticamente entre PEQUENO e MUITO_GRANDE com base no volume de contatos .

    Tratamento de Falhas: O campo necessita_reprocessamento é marcado como true sempre que um job falha ou é cancelado.

Orquestração (n8n)

    A pipeline roda em um pooling de 5 minutos.

    Resiliência: Foi configurado retry com backoff para lidar com o erro simulado de 429 Too Many Requests da API.