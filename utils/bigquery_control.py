from __future__ import annotations

from google.cloud import bigquery

from config.settings import GCP_PROJECT_ID, BQ_DATASET, CONTROL_TABLE

from utils.logger import get_logger

log = get_logger(__name__)

_CONTROL_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{CONTROL_TABLE}"

_SCHEMA = [
    bigquery.SchemaField('competencia', 'STRING', mode='REQUIRED'),
    bigquery.SchemaField("status", "STRING", mode="REQUIRED"),  # SUCCESS | FAILED
    bigquery.SchemaField("executado_em", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("detalhes", "STRING", mode="NULLABLE")
]

def garantir_tabela_controle(client: bigquery.Client) -> None:
    dataset_ref = bigquery.DatasetReference(GCP_PROJECT_ID, BQ_DATASET)
    table_ref = dataset_ref.table(CONTROL_TABLE)

    try:
        client.get_table(table_ref)
    except Exception:
        table = bigquery.Table(table_ref, schema=_SCHEMA)
        client.create_table(table, exists_ok=True)
        log.info(f"Tabela de controle criada: {_CONTROL_TABLE_ID}")

def ja_processado(client: bigquery.Client, competencia: str) -> bool:
    query = f"""
        SELECT 1
        FROM `{_CONTROL_TABLE_ID}`
        WHERE 
            competencia = @competencia
            AND status = 'SUCCESS'
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                'competencia', 
                'STRING', 
                competencia
            )
        ]
    )

    resultado = list(
        client.query(
            query, job_config=job_config
        ).result()
    )

    return len(resultado) > 0

def registrar_execucao(
        client: bigquery.Client,
        competencia: str,
        status: str,
        detalhes: str = ""
) -> None:

    query = f"""
        INSERT INTO `{_CONTROL_TABLE_ID}`
        (
            competencia, 
            status, 
            executado_em, 
            detalhes
        )
        VALUES (
            @competencia,
            @status,
            CURRENT_TIMESTAMP(),
            @detalhes
        )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                'competencia',
                'STRING',
                competencia
            ),
            bigquery.ScalarQueryParameter(
                'status',
                'STRING',
                status
            ),
            bigquery.ScalarQueryParameter(
                'detalhes',
                'STRING',
                detalhes
            )
        ]
    )

    client.query(
        query,
        job_config=job_config
    ).result()

    log.info(
        f"Execução registrada: competencia={competencia} status={status}"
    )