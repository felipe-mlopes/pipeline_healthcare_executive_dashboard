from utils.bigquery_control import (
    ja_processado,
    registrar_execucao,
    garantir_tabela_controle
)

def test_ja_processado_false_quando_sem_resultado(fake_bq_client):
    fake_bq_client.query.return_value.result.return_value = []

    assert ja_processado(fake_bq_client, '2026-07') is False

def test_ja_processado_true_quando_ha_resultado(fake_bq_client):
    fake_bq_client.query.return_value.result.return_value = [
        {'1': 1}
    ]

    assert ja_processado(fake_bq_client, '2026-07') is True

def test_registrar_execucao_chama_query_com_status(fake_bq_client):
    registrar_execucao(
        fake_bq_client,
        '2026-07',
        status='SUCCESS',
        detalhes='ok'
    )

    assert fake_bq_client.query.called
    sql = fake_bq_client.query.call_args.args[0]
    assert "INSERT INTO" in sql

def test_garantir_tabela_controle_cria_quando_nao_existe(fake_bq_client):
    fake_bq_client.get_table.side_effect = Exception('not found')
    garantir_tabela_controle(fake_bq_client)

    assert fake_bq_client.create_table.called