import json
from pathlib import Path

ARQUIVO_CONTROLE = Path(
    "logs/controle_execucao.json"
)


def ja_processado(competencia):

    if not ARQUIVO_CONTROLE.exists():
        return False

    with open(
        ARQUIVO_CONTROLE,
        "r",
        encoding="utf-8"
    ) as f:

        controle = json.load(f)

    return (
        controle.get("ultima_competencia")
        == competencia
    )


def registrar_execucao(competencia):

    with open(
        ARQUIVO_CONTROLE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "ultima_competencia": competencia
            },
            f,
            ensure_ascii=False,
            indent=4
        )