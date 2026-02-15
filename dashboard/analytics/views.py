from django.shortcuts import render
from django.db.models import Count, Avg
from .models import GoldEnrichment

def dashboard_view(request):
    # 1. Busca os dados
    qs = GoldEnrichment.objects.all()
    
    # LINHA CORRIGIDA: Removido o
    total_jobs = qs.count() 

    # 2. KPIs
    sucessos = qs.filter(processamento_sucesso=True).count()
    taxa_sucesso = f"{(sucessos / total_jobs * 100):.1f}%" if total_jobs > 0 else "0%"
    
    tempo_medio_val = qs.aggregate(Avg('duracao_processamento_minutos'))['duracao_processamento_minutos__avg'] or 0
    tempo_medio = f"{tempo_medio_val:.2f} min"

    # 3. Gráficos
    cat_data = qs.values('categoria_tamanho_job').annotate(total=Count('id_enriquecimento'))
    labels_categoria = [c['categoria_tamanho_job'] for c in cat_data]
    valores_categoria = [c['total'] for c in cat_data]

    stat_data = qs.values('status_processamento').annotate(total=Count('id_enriquecimento'))
    labels_status = [s['status_processamento'] for s in stat_data]
    valores_status = [s['total'] for s in stat_data]

    # 4. Tabela
    enriquecimentos = qs.order_by('-data_criacao')[:15]

    context = {
        'total_jobs': total_jobs,
        'taxa_sucesso': taxa_sucesso,
        'tempo_medio': tempo_medio,
        'labels_categoria': labels_categoria,
        'valores_categoria': valores_categoria,
        'labels_status': labels_status,
        'valores_status': valores_status,
        'enriquecimentos': enriquecimentos,
    }
    
    return render(request, 'dashboard.html', context)