import pandas as pd

from extract.generate_csv import geracao_custo, geracao_risco, geracao_sinistralidade, geracao_vidas
from extract.save_monthly_csv import salvar_csv_mensal

from load.bigquery_load import carregar_csv

from utils.execution_control import ja_processado, registrar_execucao

def executar_pipeline():

    competencia = (
        pd.Timestamp.today()
        .replace(day=1)
        - pd.DateOffset(month=1)
    )

    competencia_txt = competencia.strftime("%Y-%m")

    if ja_processado(competencia_txt):
        print(
            f"Competência: {competencia_txt} já processada."
        )

        return

    print(f"Competência: {competencia:%Y-%m}")

    sin = geracao_sinistralidade()
    vidas = geracao_vidas()
    custo = geracao_custo()
    risco = geracao_risco(
        sin, custo, vidas
    )

    arq_sin = salvar_csv_mensal(
        sin,
        'sinistralidade',
        competencia
    )

    arq_vidas = salvar_csv_mensal(
        vidas,
        'sinistralidade',
        competencia
    )

    arq_custo = salvar_csv_mensal(
        custo,
        'sinistralidade',
        competencia
    )

    arq_risco = salvar_csv_mensal(
        risco,
        'sinistralidade',
        competencia
    )

    carregar_csv(arq_sin)
    carregar_csv(arq_vidas)
    carregar_csv(arq_custo)
    carregar_csv(arq_risco)

    registrar_execucao(
        competencia_txt
    )

    print(
        f"Competência {competencia_txt} registrada."
    )


if __name__ == '__main__':
    executar_pipeline()