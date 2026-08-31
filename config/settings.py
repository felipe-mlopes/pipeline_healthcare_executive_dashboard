import os

def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)

    if required and not value:
        raise RuntimeError(
            f"Variável de ambiente obrigatória não definida:{name}"
        )

    return value


# --- Ambiente | GCP ---
GCP_PROJECT_ID = _env("GCP_PROJECT_ID", required=True)
BQ_DATASET = _env("BQ_DATASET", default="health_care_lifes")
BQ_LOCATION = _env("BQ_LOCATION", default="US")

# --- Diretório de staging local (efêmero dentro da execução do container) ---
DATA_PATH = _env("DATA_PATH", default="/tmp/data")

# --- Nome da tabela de controle de execução (idempotência) ---
CONTROL_TABLE = _env("BQ_CONTROL_TABLE", default="pipeline_execution_control")

# --- Mapeamento: dataframe gerado -> (nome de tabela destino, coluna de
# partição)
TABLE_MAP = {
    "sinistralidade": {
        "table": "sinistralidade_operadora_pre_pgto",
        "partition_field": "data_pagamento",
    },
    "vidas": {
        "table": "vidas_operadoras",
        "partition_field": "Mes",
    },
    "custo": {
        "table": "custo_operadora_pos_pgto",
        "partition_field": "data_pagamento",
    },
    "risco": {
        "table": "custo_por_risco_todas_operadoras",
        "partition_field": "data_ref",
    },
}