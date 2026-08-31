from extract.generate_csv import (
    geracao_custo,
    geracao_risco,
    geracao_sinistralidade,
    geracao_vidas,
)

def test_geracao_sinistralidade_colunas_e_valores():
    df = geracao_sinistralidade()

    assert list(df.columns) == [
        "data_pagamento",
        "plano",
        "uf_benef",
        "despesa",
        "receita",
    ]
    assert not df.empty
    assert df.isnull().sum().sum() == 0
    assert (df["despesa"] >= 0).all()
    assert (df["receita"] >= 0).all()
    assert df["uf_benef"].nunique() == 27  # 27 UFs definidas no gerador

def test_geracao_vidas_colunas_e_valores():
    df = geracao_vidas()

    assert list(df.columns) == [
        "Operadora",
        "Mes",
        "Tipo_plano",
        "Nome_plano",
        "Valor",
        "UF_Benef",
        "Nome_empresa",
    ]
    assert not df.empty
    assert (df["Valor"] >= 0).all()
    assert set(df["Operadora"].unique()) <= {"Operadora X", "Operadora Y"}

def test_geracao_custo_colunas_e_valores():
    df = geracao_custo()

    assert not df.empty
    for col in ["VPP", "VPG", "despesa"]:
        assert (df[col] >= 0).all()

    # NOTA / achado: `Copart = despesa - vpp` no gerador original sempre dá
    # negativo, pois `despesa = vpp * uniform(0.8, 0.95)` é sempre < vpp.
    # Isso é um bug de regra de negócio pré-existente (fora do escopo desta
    # automação de infra) — mantemos o teste documentando o comportamento
    # ATUAL para não mascarar uma regressão futura, mas o time de dados
    # deveria revisar essa fórmula antes de considerar "Copart" confiável
    # no dashboard.
    assert (df["Copart"] < 0).all()

    # VPP deve ser sempre maior ou igual ao VPG (fator 1.02 a 1.05 aplicado no gerador)
    assert (df["VPP"] >= df["VPG"]).all()

def test_geracao_risco_soma_bate_com_insumos():
    sin = geracao_sinistralidade()
    vidas = geracao_vidas()
    custo = geracao_custo()

    risco = geracao_risco(sin, custo, vidas)

    assert not risco.empty
    assert (risco["Valor"] >= 0).all()
    assert set(risco["Risco"].unique()) <= {
        "Grande Risco",
        "Pequeno Risco",
        "Odontológico",
        "Farmácia",
    }