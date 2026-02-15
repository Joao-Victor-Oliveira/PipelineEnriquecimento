from django.db import models

class GoldEnrichment(models.Model):
    # Campos conforme exigido no desafio [cite: 131-146]
    id_enriquecimento = models.UUIDField(primary_key=True)
    nome_workspace = models.CharField(max_length=255)
    total_contatos = models.IntegerField()
    status_processamento = models.CharField(max_length=50) # CONCLUIDO, FALHOU, etc.
    duracao_processamento_minutos = models.FloatField()
    processamento_sucesso = models.BooleanField()
    categoria_tamanho_job = models.CharField(max_length=20) # PEQUENO a MUITO_GRANDE [cite: 151-155]
    data_criacao = models.DateTimeField()

    class Meta:
        managed = False # O Django não tentará criar a tabela, pois o n8n/SQL já criou
        db_table = 'gold'