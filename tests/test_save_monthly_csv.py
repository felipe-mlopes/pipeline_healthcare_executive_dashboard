import os
import pandas as pd
from extract.save_monthly_csv import salvar_csv_mensal

def test_salvar_csv_mensal_gera_arquivo_correto(tmp_path, monkeypatch, competencia):
    monkeypatch.chdir(tmp_path)

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    arquivo = salvar_csv_mensal(df, "vidas", competencia)

    assert os.path.exists(arquivo)
    assert arquivo.endswith("vidas_2026_07.csv")

    conteudo = pd.read_csv(arquivo, sep=";", encoding="utf-8-sig")
    assert conteudo.shape == (2, 2)


def test_salvar_csv_mensal_datasets_diferentes_nao_se_sobrescrevem(tmp_path, monkeypatch, competencia):
    monkeypatch.chdir(tmp_path)

    df_sin = pd.DataFrame({"valor": [1]})
    df_vidas = pd.DataFrame({"valor": [2]})

    arq_sin = salvar_csv_mensal(df_sin, "sinistralidade", competencia)
    arq_vidas = salvar_csv_mensal(df_vidas, "vidas", competencia)

    assert arq_sin != arq_vidas
    assert os.path.exists(arq_sin)
    assert os.path.exists(arq_vidas)