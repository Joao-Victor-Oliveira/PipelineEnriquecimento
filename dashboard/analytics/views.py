import requests
from django.shortcuts import render

# Configurações de acesso à API interna baseadas nos requisitos de autenticação [cite: 56, 69, 70]
API_BASE_URL = "http://driva_api:3000"
HEADERS = {"Authorization": "Bearer driva_test_key_abc123xyz789"}

def dashboard_view(request):
    """
    View principal que orquestra o consumo da API de Analytics para popular o dashboard[cite: 21, 37, 200].
    """
    # 1. Captura parâmetros de paginação e filtros da requisição GET [cite: 73, 74, 204]
    page = int(request.GET.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    status_filter = request.GET.get('status', '')

    try:
        # 2. Chamada ao OVERVIEW: Obtém KPIs de performance da camada Gold [cite: 105, 106, 202]
        res_ov = requests.get(f"{API_BASE_URL}/analytics/overview", headers=HEADERS, timeout=5)
        ov_data = res_ov.json().get('data', {})

        # 3. Chamada ao SUMÁRIO: Dados globais para os gráficos de distribuição [cite: 106, 203]
        res_summary = requests.get(f"{API_BASE_URL}/analytics/summary", headers=HEADERS, timeout=5)
        summary = res_summary.json()

        # 4. Chamada à LISTA: Recupera registros paginados e aplica o filtro de status [cite: 107, 108, 204]
        api_list_url = f"{API_BASE_URL}/analytics/enrichments?limit={limit}&offset={offset}"
        if status_filter:
            api_list_url += f"&status={status_filter}"
        
        res_list = requests.get(api_list_url, headers=HEADERS, timeout=5)
        enriquecimentos = res_list.json()

        # 5.  Ranking de Workspaces por volume de contatos [cite: 109, 110]
        res_top = requests.get(f"{API_BASE_URL}/analytics/workspaces/top?limit=5", headers=HEADERS, timeout=5)
        top_data = res_top.json().get('data', [])

        # 6. Montagem do contexto para o template [cite: 201]
        context = {
            # KPIs reais da camada Gold [cite: 106, 202]
            'total_jobs': ov_data.get('total_enriquecimentos', 0),
            'taxa_sucesso': ov_data.get('taxa_sucesso', "0%"),
            'tempo_medio': ov_data.get('tempo_medio_processamento', "0 min"),

            # Dados para os gráficos de Categoria e Status [cite: 151, 160, 203]
            'labels_categoria': [c['categoria_tamanho_job'] for c in summary.get('categorias', [])],
            'valores_categoria': [c['qtd'] for c in summary.get('categorias', [])],
            'labels_status': [s['status_processamento'] for s in summary.get('status', [])],
            'valores_status': [s['qtd'] for s in summary.get('status', [])],

            # Dados para o gráfico de Ranking (Bônus) [cite: 110, 138]
            'labels_top': [w['nome_workspace'] for w in top_data],
            'valores_top': [w['volume_contatos'] for w in top_data],

            # Variáveis de controle da Tabela e Paginação [cite: 204]
            'page_obj': enriquecimentos,
            'current_page': page,
            'current_status': status_filter,
            # Lista de status traduzidos conforme regras da camada Gold 
            'status_list': ['EM_PROCESSAMENTO', 'CONCLUIDO', 'FALHOU', 'CANCELADO']
        }

    except Exception as e:
        # Tratamento básico de erro para evitar que o dashboard quebre se a API estiver offline [cite: 212]
        print(f"Erro na integração com a API Analytics: {e}")
        context = {
            'error': "Erro ao carregar dados da API. Verifique se o serviço driva_api está online.",
            'status_list': ['EM_PROCESSAMENTO', 'CONCLUIDO', 'FALHOU', 'CANCELADO']
        }

    return render(request, 'dashboard.html', context)