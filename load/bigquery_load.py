from google.cloud import bigquery

client = bigquery.Client()

def carregar_csv(
    arquivo,
    project_id,
    dataset,
    tabela
):

    table_id = f"{project_id}.{dataset}.{tabela}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition="WRITE_APPEND"
    )

    with open(arquivo, "rb") as source_file:

        job = client.load_table_from_file(
            source_file,
            table_id,
            job_config=job_config
        )

    job.result()

    print(f"Carga concluída: {table_id}")