from load.bigquery_load import carregar_incremental

def test_carregar_incremental_usa_partition_decorator_e_write_truncate(
    tmp_path, fake_bq_client, competencia
):
    arquivo_csv = tmp_path / "sinistralidade_2026_07.csv"
    arquivo_csv.write_text("data_pagamento;plano;uf_benef;despesa;receita\n2026-07-01;Alfa;SP;10;20\n")

    linhas = carregar_incremental(
        arquivo=str(arquivo_csv),
        tabela="sinistralidade_operadora_pre_pgto",
        partition_field="data_pagamento",
        competencia=competencia,
        client=fake_bq_client,
    )

    assert linhas == 10
    assert fake_bq_client.load_table_from_file.called

    args, kwargs = fake_bq_client.load_table_from_file.call_args
    destino = args[1]
    assert destino.endswith("sinistralidade_operadora_pre_pgto$202607")

    job_config = kwargs["job_config"]
    assert job_config.write_disposition == "WRITE_TRUNCATE"

def test_carregar_incremental_tabela_desconhecida_leva_erro(tmp_path, fake_bq_client, competencia):
    arquivo_csv = tmp_path / "x.csv"
    arquivo_csv.write_text("a;b\n1;2\n")

    try:
        carregar_incremental(
            arquivo=str(arquivo_csv),
            tabela="tabela_que_nao_existe",
            partition_field="data_pagamento",
            competencia=competencia,
            client=fake_bq_client,
        )
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass