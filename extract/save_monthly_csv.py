import os

def salvar_csv_mensal(df, nome_dataset, data_ref):
    
    competencia = data_ref.strftime("%Y_%m")

    pasta = os.path.join("data", nome_dataset)
    os.makedirs(pasta, exist_ok=True)

    arquivo = os.path.join(
        pasta,
        f"{nome_dataset}_{competencia}.csv"
    )

    df.to_csv(
        arquivo,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print(f"Arquivo gerado: {arquivo}")

    return arquivo