from unittest.mock import patch
import pandas as pd
import main as main_module

def _df(col="valor"):
    return pd.DataFrame({col: [1, 2, 3]})

def test_pipeline_pula_quando_ja_processado(fake_bq_client, monkeypatch):
    monkeypatch.setenv("COMPETENCIA", "2026-07")

    with patch("main.bigquery.Client", return_value=fake_bq_client), \
         patch("main.ja_processado", return_value=True) as mock_ja_processado, \
         patch("main.geracao_sinistralidade") as mock_gera:

        main_module.executar_pipeline()

        mock_ja_processado.assert_called_once()
        mock_gera.assert_not_called()

def test_pipeline_processa_e_carrega_cada_tabela_uma_vez(fake_bq_client, monkeypatch, tmp_path):
    monkeypatch.setenv("COMPETENCIA", "2026-07")
    monkeypatch.chdir(tmp_path)

    with patch("main.bigquery.Client", return_value=fake_bq_client), \
         patch("main.ja_processado", return_value=False), \
         patch("main.registrar_execucao") as mock_registrar, \
         patch("main.geracao_sinistralidade", return_value=_df()), \
         patch("main.geracao_vidas", return_value=_df()), \
         patch("main.geracao_custo", return_value=_df()), \
         patch("main.geracao_risco", return_value=_df()), \
         patch("main.carregar_incremental", return_value=3) as mock_carregar:

        main_module.executar_pipeline()

        # As 4 tabelas de destino devem ter sido carregadas exatamente uma vez cada
        tabelas_chamadas = {c.kwargs["tabela"] for c in mock_carregar.call_args_list}
        assert tabelas_chamadas == {
            "sinistralidade_operadora_pre_pgto",
            "vidas_operadoras",
            "custo_operadora_pos_pgto",
            "custo_por_risco_todas_operadoras",
        }
        assert mock_carregar.call_count == 4

        # Execução deve ser registrada como sucesso
        mock_registrar.assert_called_once()
        assert mock_registrar.call_args.kwargs["status"] == "SUCCESS"