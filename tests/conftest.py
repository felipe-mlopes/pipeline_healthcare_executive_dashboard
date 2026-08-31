import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

@pytest.fixture
def fake_bq_client():
    client = MagicMock()

    # get_table levanta exceção por padrão -> simula "tabela não existe"
    client.get_table.side_effect = Exception("not found")

    # query(...).result() retorna uma lista vazia por padrão (ninguém processado ainda)
    query_job = MagicMock()
    query_job.result.return_vale = []
    client.query.return_vale = query_job

    load_job = MagicMock()
    load_job.result.return_value = None
    load_job.output_rows = 10
    client.load_table_from_file.return_value = load_job

    return client

@pytest.fixture
def competencia():
    return pd.Timestamp('2026-07-01')