from __future__ import annotations

import pandas as pd
from google.cloud import bigquery

from config.settings import (
    GCP_PROJECT_ID,
    BQ_DATASET,
    BQ_LOCATION
)

from utils.logger import get_logger

log = get_logger(__name__)

SCHEMAS: dict[str, list[bigquery.SchemaField]] = {
    "sinistralidade_operadora_pre_pgto": [
        bigquery.SchemaField("data_pagamento", "DATE"),
        bigquery.SchemaField("plano", "STRING"),
        bigquery.SchemaField("uf_benef", "STRING"),
        bigquery.SchemaField("despesa", "FLOAT64"),
        bigquery.SchemaField("receita", "FLOAT64"),
    ],
    "vidas_operadoras": [
        bigquery.SchemaField("Operadora", "STRING"),
        bigquery.SchemaField("Mes", "DATE"),
        bigquery.SchemaField("Tipo_plano", "STRING"),
        bigquery.SchemaField("Nome_plano", "STRING"),
        bigquery.SchemaField("Valor", "INT64"),
        bigquery.SchemaField("UF_Benef", "STRING"),
        bigquery.SchemaField("Nome_empresa", "STRING"),
    ],
    "custo_operadora_pos_pgto": [
        bigquery.SchemaField("operadora", "STRING"),
        bigquery.SchemaField("plano", "STRING"),
        bigquery.SchemaField("modulo", "STRING"),
        bigquery.SchemaField("empresa", "STRING"),
        bigquery.SchemaField("cassi", "STRING"),
        bigquery.SchemaField("data_pagamento", "DATE"),
        bigquery.SchemaField("uf_beneficiario", "STRING"),
        bigquery.SchemaField("VPP", "FLOAT64"),
        bigquery.SchemaField("VPG", "FLOAT64"),
        bigquery.SchemaField("Copart", "FLOAT64"),
        bigquery.SchemaField("despesa", "FLOAT64"),
    ],
    "custo_por_risco_todas_operadoras": [
        bigquery.SchemaField("data_ref", "DATE"),
        bigquery.SchemaField("Operadora", "STRING"),
        bigquery.SchemaField("plano", "STRING"),
        bigquery.SchemaField("uf_benef", "STRING"),
        bigquery.SchemaField("empresa", "STRING"),
        bigquery.SchemaField("Tipo_plano", "STRING"),
        bigquery.SchemaField("Benef_farmacia", "STRING"),
        bigquery.SchemaField("Risco", "STRING"),
        bigquery.SchemaField("cassi", "STRING"),
        bigquery.SchemaField("VPP", "FLOAT64"),
        bigquery.SchemaField("Valor", "FLOAT64"),
    ]
}

def _garantir_tabela(
        client: bigquery.Client,
        tabela: str,
        partition_field: str
) -> None:
    dataset_ref = bigquery.DatasetReference(
        GCP_PROJECT_ID,
        BQ_DATASET
    )
    table_ref = dataset_ref.table(tabela)
    
    try:
        client.get_table(table_ref)
        return
    except Exception:
        pass

    schema = SCHEMAS[tabela]
    table = bigquery.Table(
        table_ref,
        schema=schema
    )
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.MONTH,
        field=partition_field
    )
    client.create_table(
        table,
        exists_ok=True
    )

    log.info(
        f"Tabela criada: {GCP_PROJECT_ID}. {BQ_DATASET}.{tabela} (particionada por {partition_field}/MONTH)"
    )

def carregar_incremental(
        arquivo: str,
        tabela: str,
        partition_field: str,
        competencia: pd.Timestamp,
        client: bigquery.Client | None = None
) -> int:
    if tabela not in SCHEMAS:
        raise ValueError(
            f"Tabela desconhecida (sem schema definido): {tabela}"
        )

    client = client or bigquery.Client(
        project=GCP_PROJECT_ID,
        location=BQ_LOCATION
    )

    _garantir_tabela(
        client,
        tabela,
        partition_field
    )

    partition_field = competencia.strftime('%Y%m')
    destino = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{tabela}${partition_field}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter=';',
        skip_leading_rows=1,
        schema=SCHEMAS[tabela],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.MONTH,
            field=partition_field,
        )
    )

    with open(arquivo, 'rb') as source_file:
        job = client.load_table_from_file(
            source_file,
            destino,
            job_config=job_config
        )

    job.result()

    linhas = job.output_rows or 0

    log.info(
        f"Carga concluída: {destino} ({linhas}) linhas"
    )

    return linhas