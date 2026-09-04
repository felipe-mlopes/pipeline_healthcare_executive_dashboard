from itertools import islice, product

import numpy as np
import pandas as pd

## Variáveis
ufs = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']
planos_pre = ['Alfa', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Omega', 'Capa', 'Iota']
planos_pos = ['Plano-1', 'Plano-2', 'Plano-3', 'Plano-4', 'Plano-5', 'Plano-6']
operadoras = ['Operadora X','Operadora Y']
tipos = ['médico','odontológico']
empresas_pre = ['Empresa A']
empresas_pos = ['Empresa B', 'Empresa C', 'Empresa D', 'Empresa E']
boleano = ['Sim', 'Não']
riscos = ['Grande Risco', 'Pequeno Risco', 'Odontológico', 'Farmácia']
modulos = ['Modulo-1','Modulo-2','Modulo-3','Modulo-4']
operadora_pre = ['Operadora X']
operadora_pos = ['Operadora Y']

## Período corrente
##
## A competência (mês de referência) é decidida em um único lugar: main.py
## (função competencia_alvo). Cada função de geração recebe esse valor como
## parâmetro explícito, evitando duas fontes de verdade divergentes sobre
## "qual mês estamos processando".

rng = np.random.default_rng(42)
MAX_ROWS = 200_000

## --- Sinistralidade Operadora X

## data_pagamento
## plano
## uf_benef
## despesa
## receita
def geracao_sinistralidade(competencia: pd.Timestamp):

    datas = [competencia]
    rows_sinistralidade = []

    for d in datas:

        # MÉDICO
        planos_medicos = ['Alfa','Beta','Gamma','Delta','Epsilon','Omega']

        receita_total_med = float(
            rng.integers(40_000_000, 42_000_001)
        )

        # Peso maior para Alfa e Beta
        pesos_planos_med = np.array([
            2.0,  # Alfa
            1.8,  # Beta
            1.0,  # Gamma
            1.0,  # Delta
            1.0,  # Epsilon
            1.0   # Omega
        ])

        pesos_planos_med = pesos_planos_med / pesos_planos_med.sum()

        receita_planos_med = np.round(
            receita_total_med * pesos_planos_med, 2
        )

        receita_planos_med[0] += round(
            receita_total_med - receita_planos_med.sum(), 2
        )

        for plano, receita_plano in zip(planos_medicos, receita_planos_med):

            # Faixas desejadas
            if plano in ['Alfa', 'Beta']:
                sinistralidade = rng.uniform(1.05, 1.20)
            else:
                sinistralidade = rng.uniform(0.80, 0.95)

            despesa_plano = round(receita_plano * sinistralidade, 2)

            pesos_ufs = rng.dirichlet(np.ones(len(ufs)))

            receitas_uf = np.round(receita_plano * pesos_ufs, 2)
            despesas_uf = np.round(despesa_plano * pesos_ufs, 2)

            receitas_uf[0] += round(
                receita_plano - receitas_uf.sum(), 2
            )

            despesas_uf[0] += round(
                despesa_plano - despesas_uf.sum(), 2
            )

            for uf, receita, despesa in zip(
                ufs,
                receitas_uf,
                despesas_uf
            ):
                rows_sinistralidade.append(
                    [
                        d.date(),
                        plano,
                        uf,
                        despesa,
                        receita
                    ]
                )

        # ODONTO
        planos_odonto = ['Capa', 'Iota']
        
        receita_total_odonto = float(
            rng.integers(400_000, 420_001)
        )

        pesos_planos_odonto = np.array([
            1.2,  # Capa
            1.0   # Iota
        ])

        pesos_planos_odonto /= pesos_planos_odonto.sum()

        receita_planos_odonto = np.round(
            receita_total_odonto * pesos_planos_odonto, 2
        )

        receita_planos_odonto[0] += round(
            receita_total_odonto - receita_planos_odonto.sum(), 2
        )

        for plano, receita_plano in zip(
            planos_odonto,
            receita_planos_odonto
        ):

            if plano == 'Capa':
                sinistralidade = rng.uniform(0.35, 0.45)

            elif plano == 'Iota':
                sinistralidade = rng.uniform(0.45, 0.60)

            despesa_plano = round(
                receita_plano * sinistralidade, 2
            )

            pesos_ufs = rng.dirichlet(np.ones(len(ufs)))

            receitas_uf = np.round(receita_plano * pesos_ufs, 2)
            despesas_uf = np.round(despesa_plano * pesos_ufs, 2)

            receitas_uf[0] += round(
                receita_plano - receitas_uf.sum(), 2
            )

            despesas_uf[0] += round(
                despesa_plano - despesas_uf.sum(), 2
            )

            for uf, receita, despesa in zip(
                ufs,
                receitas_uf,
                despesas_uf
            ):
                rows_sinistralidade.append(
                    [
                        d.date(),
                        plano,
                        uf,
                        despesa,
                        receita
                    ]
                )

    return pd.DataFrame(
        rows_sinistralidade,
                columns=[
            'data_pagamento',
            'plano',
            'uf_benef',
            'despesa',
            'receita'
        ]
    )


## --- Vidas

## Operadora
## Mes
## Tipo_plano
## Nome_plano
## Valor
## UF_Benef
## Nome_empresa
def geracao_vidas(competencia: pd.Timestamp):

    datas = [competencia]
    rows_vidas = []

    for d, op in product(datas, operadoras):
        if op == 'Operadora X':

            grupos_planos = [
                (
                    ['Alfa', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Omega'],
                    int(rng.integers(28000, 35001))
                ),
                (
                    ['Capa', 'Iota'],
                    int(rng.integers(6000, 7501))
                )
            ]

            empresas_operadora = empresas_pre

        else:

            grupos_planos = [
                (
                    planos_pos,
                    int(rng.integers(190000, 210001))
                )
            ]
            empresas_operadora = empresas_pos

        for planos, total_operadora in grupos_planos:

            # Quantidade de combinações
            n_combinacoes = (
                len(tipos) *
                len(planos) *
                len(ufs) *
                len(empresas_operadora)
            )

            # Distribuição aleatória entre todas as combinações
            pesos = rng.dirichlet(np.ones(n_combinacoes))
            valores = np.floor(total_operadora * pesos).astype(int)

            valores[0] += total_operadora - valores.sum()

            idx = 0

            for tp, plano, uf, emp in product(
                tipos,
                planos,
                ufs,
                empresas_operadora
            ):

                rows_vidas.append(
                    [
                        op,
                        d.date(),
                        tp, 
                        plano,
                        int(valores[idx]),
                        uf,
                        emp
                    ]
                )

                idx += 1

    return pd.DataFrame(
        rows_vidas,
        columns=[
            'Operadora', 
            'Mes', 
            'Tipo_plano', 
            'Nome_plano', 
            'Valor', 
            'UF_Benef', 
            'Nome_empresa'
        ]
    )


## --- Custo Operadora Y

## operadora
## plano x
## modulo x
## empresa x
## cassi
## data_pagamento
## uf_beneficiario x
## VPP
## VPG
## Copart
## despesa
def geracao_custo(competencia: pd.Timestamp):

    datas = [competencia]
    rows_custo = []

    for o, r, d in islice(
        product(
            operadora_pos,
            boleano,
            datas,
        ),
        MAX_ROWS
    ):       
        vpg = float(rng.integers(35_000_000,50_000_001))

        vpp = float(vpg * rng.uniform(1.02, 1.05))

        despesa = float(vpp * rng.uniform(0.8, 0.95))

        copart = despesa - vpp

        # Quantidade de combinações
        n_combinacoes = (
            len(planos_pos) *
            len(modulos) *
            len(empresas_pos) *
            len(ufs)
        )

        # Distribuição aleatória entre todas as combinações
        pesos = rng.dirichlet(np.ones(n_combinacoes))
        valores_vpg = np.round(vpg * pesos, 2)
        valores_vpp = np.round(vpp * pesos, 2)
        valores_despesa = np.round(despesa * pesos, 2)
        valores_copart = np.round(copart * pesos, 2)

        valores_vpg[0] += round(vpg - valores_vpg.sum(), 2)
        valores_vpp[0] += round(vpp - valores_vpp.sum(), 2)
        valores_despesa[0] += round(despesa - valores_despesa.sum(), 2)
        valores_copart[0] += round(copart - valores_copart.sum(), 2)

        idx = 0

        for plano, modulo, empresa, uf in product(planos_pos, modulos, empresas_pos, ufs):
            rows_custo.append(
                [
                    o,
                    plano,
                    modulo,
                    empresa,
                    r,
                    d.date(),
                    uf,
                    valores_vpp[idx],
                    valores_vpg[idx],
                    valores_copart[idx],
                    valores_despesa[idx]
                ]
            )

            idx += 1

    return pd.DataFrame(
        rows_custo,
        columns=[
            'operadora',
            'plano',
            'modulo',
            'empresa',
            'cassi',
            'data_pagamento',
            'uf_beneficiario',
            'VPP',
            'VPG',
            'Copart',
            'despesa'
        ]
    )


## --- Abertura por Risco

## data_ref
## Operadora
## plano
## uf_benef
## empresa
## Tipo_plano
## Benef_farmacia
## Risco
## cassi
## VPP
## Valor
def geracao_risco(sin, custo, vidas):
    """
        --- Operadora X ----
        Planos capa e iota:
            . Tipo_plano = 'odontológico'
            . Riscos = 'Odontológico'
            . Valor = 100% da despesa
        
        Planos alfa, beta, gamma, delta e epsilon:
            . Tipo_plano = 'médico'
            . Riscos = ['Grande Risco', 'Pequeno Risco']

        --- Operadora Y ----
        Empresas B e C
            . Riscos = ['Grande Risco', 'Pequeno Risco', 'Odontológico']

        Empresas D e E
            . Riscos = ['Grande Risco', 'Pequeno Risco', 'Odontológico', 'Farmácia']
    """

    rows_risco = []

    ## OPERADORA X
    for _, row in sin.iterrows():
        despesa = float(row['despesa'])
        plano = row['plano']

        #  => só odontológico
        if plano in ['Capa', 'Iota']:
            rows_risco.append([
                row['data_pagamento'],
                'Operadora X',
                plano,
                row['uf_benef'],
                'Empresa A',
                'odontológico',
                'Não',
                'Odontológico',
                'Não',
                float(despesa * rng.uniform(1.05, 1.20)),
                despesa
            ])

        # Alfa, Beta, Gamma, Delta, Epsilon e Omega: apenas Médico
        else:
            # Médico
            if rng.random() < 0.5:
                peso_grande = rng.uniform(0.55, 0.70)
                peso_pequeno = (1 - peso_grande)
            else:
                peso_pequeno = rng.uniform(0.55, 0.70)
                peso_grande = (1 - peso_pequeno)

            valor_grande = float(despesa * peso_grande)
            valor_pequeno = despesa - valor_grande

            # Médico - Grande Risco
            rows_risco.append(
                [
                    row['data_pagamento'],
                    'Operadora X',
                    plano,
                    row['uf_benef'],
                    'Empresa A',
                    'médico',
                    'Não',
                    'Grande Risco',
                    'Não',
                    float(valor_grande * rng.uniform(1.05, 1.20)),
                    valor_grande
                ]
            )

            # Médico - Pequeno Risco
            rows_risco.append(
                [
                    row['data_pagamento'],
                    'Operadora X',
                    plano,
                    row['uf_benef'],
                    'Empresa A',
                    'médico',
                    'Não',
                    'Pequeno Risco',
                    'Não',
                    float(valor_pequeno * rng.uniform(1.05, 1.20)),
                    valor_pequeno
                ]
            )


    ## OPERADORA Y
    vidas_odonto = (
        vidas[
            (vidas['Operadora'] == 'Operadora Y') &
            (vidas['Tipo_plano'] == 'odontológico')
        ]
        .groupby(
            [
                'Mes',
                'Nome_plano',
                'Nome_empresa',
                'UF_Benef'
            ],
            as_index=False
        )['Valor']
        .sum()
        .rename(
            columns={
                'Mes': 'data_pagamento',
                'Nome_plano': 'plano',
                'Nome_empresa': 'empresa',
                'UF_Benef': 'uf_beneficiario',
                'Valor': 'vidas_odonto'
            }
        )
    )

    custo_agr = (
        custo
            .groupby(
                [
                    'data_pagamento',
                    'plano',
                    'empresa',
                    'uf_beneficiario'
                ],
                as_index=False
            )['despesa']
            .sum()
            .merge(
                vidas_odonto,
                how='left',
                on=[
                    'data_pagamento',
                    'plano',
                    'empresa',
                    'uf_beneficiario'
                ]
            )
    )

    custo_agr['vidas_odonto'] = (
        custo_agr['vidas_odonto']
        .fillna(0)
        .astype(int)
    )

    for _, row in custo_agr.iterrows():

        despesa = float(row['despesa'])
        empresa = row['empresa']
        plano = row['plano']
        vidas_odonto = int(row['vidas_odonto'])

        if vidas_odonto > 0:
            custo_per_capita = rng.uniform(25, 40)

            valor_odonto = round(vidas_odonto * custo_per_capita, 2)
            valor_odonto = min(valor_odonto, despesa * 0.40)

        else:
            valor_odonto = 0

        saldo = max(despesa - valor_odonto, 0)

        # Empresas D e E possuem Farmácia
        if empresa in ['Empresa D', 'Empresa E']:

            peso_farmacia = rng.uniform(0.03, 0.05)
            peso_grande = rng.uniform(0.35, 0.55)

            valor_farmacia = despesa * peso_farmacia

            saldo = max(despesa - valor_odonto - valor_farmacia, 0)

            valor_grande = saldo * peso_grande
            valor_pequeno = saldo - valor_grande

            distribuicao = [
                ('médico', 'Grande Risco', 'Não', valor_grande),
                ('médico', 'Pequeno Risco', 'Não', valor_pequeno),
                ('médico', 'Farmácia', 'Sim', valor_farmacia),
                ('odontológico', 'Odontológico', 'Não', valor_odonto)
            ]

        else:
            peso_grande = rng.uniform(0.35, 0.55)
            peso_pequeno = rng.uniform(0.25, 0.50)

            valor_grande = saldo * peso_grande
            valor_pequeno = saldo - valor_grande

            distribuicao = [
                ('médico', 'Grande Risco', 'Não', valor_grande),
                ('médico', 'Pequeno Risco', 'Não', valor_pequeno),
                ('odontológico', 'Odontológico', 'Não', valor_odonto)
            ]

        for tipo_plano, risco, benef_farmacia, valor in distribuicao:
            rows_risco.append([
                row['data_pagamento'],
                'Operadora Y',
                row['plano'],
                row['uf_beneficiario'],
                empresa,
                tipo_plano,
                benef_farmacia,
                risco,
                rng.choice(boleano),
                int(valor * rng.uniform(1.05, 1.20)),
                valor
            ])

    return pd.DataFrame(
        rows_risco, 
        columns=[
            'data_ref',
            'Operadora',
            'plano',
            'uf_benef',
            'empresa',
            'Tipo_plano',
            'Benef_farmacia',
            'Risco',
            'cassi',
            'VPP',
            'Valor'
        ]
    )