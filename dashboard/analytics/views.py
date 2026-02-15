import requests
from django.shortcuts import render

API_BASE_URL = "http://driva_api:3000"
HEADERS = {"Authorization": "Bearer driva_test_key_abc123xyz789"}

def dashboard_view(request):
    page = int(request.GET.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    status_filter = request.GET.get('status', '')

    try:
        # 1. Chamada ao OVERVIEW (Para pegar a Taxa de Sucesso real)
        res_ov = requests.get(f"{API_BASE_URL}/analytics/overview", headers=HEADERS, timeout=5)
        ov_data = res_ov.json().get('data', {}) # Captura o objeto 'data' da API

        # 2. Chamada ao SUMÁRIO (Para os Gráficos de barra/rosca)
        res_summary = requests.get(f"{API_BASE_URL}/analytics/summary", headers=HEADERS, timeout=5)
        summary = res_summary.json()

        # 3. Chamada à LISTA (Para a Tabela)
        api_list_url = f"{API_BASE_URL}/analytics/enrichments?limit={limit}&offset={offset}"
        if status_filter:
            api_list_url += f"&status={status_filter}"
        res_list = requests.get(api_list_url, headers=HEADERS, timeout=5)
        enriquecimentos = res_list.json()

        context = {
            # KPIs REAIS vindos da API Overview
            'total_jobs': ov_data.get('total_enriquecimentos', 0),
            'taxa_sucesso': ov_data.get('taxa_sucesso', "0%"), # Agora pega os 49%!
            'tempo_medio': ov_data.get('tempo_medio_processamento', "0 min"),

            # Gráficos vindos do Summary (Todos os 5000 registros)
            'labels_categoria': [c['categoria_tamanho_job'] for c in summary.get('categorias', [])],
            'valores_categoria': [c['qtd'] for c in summary.get('categorias', [])],
            'labels_status': [s['status_processamento'] for s in summary.get('status', [])],
            'valores_status': [s['qtd'] for s in summary.get('status', [])],

            # Tabela e Paginação
            'page_obj': enriquecimentos,
            'current_page': page,
            'status_list': ['CONCLUIDO', 'FALHOU', 'PROCESSANDO', 'CANCELADO'],
            'current_status': status_filter
        }

    except Exception as e:
        print(f"Erro na integração: {e}")
        context = {'error': "Erro ao carregar dados reais da API."}

    return render(request, 'dashboard.html', context)