import sys

import pandas as pd
from google.cloud import bigquery

from config.settings import GCP_PROJECT_ID, BQ_LOCATION, TABLE_MAP

from extract.generate_csv import (
    geracao_custo, 
    geracao_risco, 
    geracao_sinistralidade, 
    geracao_vidas
)

from extract.save_monthly_csv import salvar_csv_mensal

from load.bigquery_load import carregar_incremental

from utils.bigquery_control import (
    garantir_tabela_controle,
    ja_processado,
    registrar_execucao
)

from utils.logger import get_logger

log = get_logger('pipeline.main')

def competencia_alvo() -> pd.Timestamp:
    import os

    override = os.getenv('COMPETENCIA')

    if override:
        return pd.Timestamp(override + '-01')

    return pd.Timestamp.today().replace(day=1) - pd.DateOffset(months=1)

def executar_pipeline() -> None:
    client = bigquery.Client(
        project=GCP_PROJECT_ID,
        location=BQ_LOCATION
    )

    garantir_tabela_controle(client)

    competencia = competencia_alvo()
    competencia_txt = competencia.strftime('%Y-%m')

    if ja_processado(client, competencia_txt):
        log.info(
            f"Competência {competencia_txt} já processada. Nada a fazer."
        )
        return

    log.info(
        f"Iniciando processamento da competência {competencia_txt}"
    )

    try:
        sin = geracao_sinistralidade(competencia)
        vidas = geracao_vidas(competencia)
        custo = geracao_custo(competencia)
        risco = geracao_risco(
            sin, custo, vidas
        )

        dataframes = {
            'sinistralidade': sin,
            'vidas': vidas,
            'custo': custo,
            'risco': risco
        }

        total_linhas = {}

        for chave, df in dataframes.items():
            destino = TABLE_MAP[chave]
            arquivo = salvar_csv_mensal(df, chave, competencia)

            linhas = carregar_incremental(
                arquivo=arquivo,
                tabela=destino['table'],
                partition_field=destino['partition_field'],
                competencia=competencia,
                client=client
            )

            total_linhas[destino['table']] = linhas

        registrar_execucao(
            client,
            competencia_txt,
            status='SUCCESS',
            detalhes=(total_linhas)
        )

        log.info(
            f"Competência {competencia_txt} registrada com sucesso: {total_linhas}"
        )

    except Exception as exc:
        log.error(
            f"Falha ao processar competência {competencia_txt}: {exc}",
            exc_info=True
        )

        registrar_execucao(
            client,
            competencia_txt,
            status='FAILED',
            detalhes=str(exc)
        )

        raise

if __name__ == '__main__':
    try:
        executar_pipeline()
    except Exception:
        sys.exit(1)