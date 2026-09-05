# Pipeline Healthcare — Resumo Executivo (Sinistralidade e Custos)

Pipeline batch mensal, serverless e idempotente, que gera os dados de sinistralidade, vidas, custo e risco de operadoras de saúde, carrega no BigQuery (particionado por dia) e alimenta um relatório executivo no Power BI.

Este documento explica a arquitetura sob a ótica de engenharia de dados: como os dados fluem, por que cada peça existe e como o projeto é operado e mantido.

### Contexto e motivação

O dashboard "Resumo Executivo" (pasta `view/`) foi originalmente construído no meu ambiente de trabalho, consumindo dados reais de um Lakehouse da empresa. Este repositório é uma **réplica de portfólio** desse projeto: para poder demonstrar a solução publicamente sem ferir a LGPD (já que os dados de origem são sensíveis — sinistralidade, custos e vidas de beneficiários de plano de saúde), substituí a fonte real por uma **extração local com dados fictícios gerados via Python** (`extract/generate_csv.py`), com seed fixa para reprodutibilidade.

O objetivo deste projeto é reproduzir, de ponta a ponta, um **ETL automático de geração mensal em batch**: extrai/gera os dados, transforma e carrega em um **data warehouse** (BigQuery, particionado por dia) e disponibiliza para consumo em uma ferramenta de **BI analytics** (Power BI), com toda a infraestrutura, orquestração, segurança e CI/CD que uma solução desse tipo teria em produção — só trocando a fonte de dados real do Lakehouse pela geração sintética.

---

## 1. Visão geral do fluxo

```
Cloud Scheduler (cron, dia 5, 06:00 America/Sao_Paulo)
        │  aciona via OIDC (identidade dedicada, sem acesso a dados)
        ▼
Cloud Run Job (container, sem HTTP, batch "roda e termina")
        │
        ▼
main.py → executar_pipeline()
        │
        ├─ 1. Garante tabela de controle (idempotência)
        ├─ 2. Calcula a competência alvo (mês anterior, ou override manual)
        ├─ 3. Verifica se a competência já foi processada com SUCCESS
        │       └─ se sim: encerra sem reprocessar
        ├─ 4. Gera os DataFrames (extract/generate_csv.py)
        ├─ 5. Salva CSV de staging local (extract/save_monthly_csv.py)
        ├─ 6. Carrega cada CSV no BigQuery via partition decorator (load/bigquery_load.py)
        └─ 7. Registra o resultado (SUCCESS/FAILED) na tabela de controle
        ▼
BigQuery (dataset particionado por dia, 4 tabelas fato + 1 tabela de controle)
        ▼
Power BI (pasta view/) — modelo semântico + relatório "Resumo Executivo"
```

O pipeline é **batch, mensal e idempotente**: mesmo que rode mais de uma vez no mesmo mês, ele não duplica dados, porque consulta a tabela de controle antes de processar.

---

## 2. Conceitos de engenharia de dados aplicados

### 2.1 Extração determinística com seed fixa (`extract/generate_csv.py`)
Os dados de origem, neste projeto, são **gerados sinteticamente** — substituindo, de forma intencional, o Lakehouse real da empresa (para não expor dados sensíveis de sinistralidade/custos/vidas e não ferir a LGPD) — usando `numpy.random.default_rng(42)` — uma seed fixa. Isso garante que o processo seja **reprodutível**: rodar duas vezes para a mesma competência produz os mesmos números, o que facilita testes e depuração. Cada função de geração (`geracao_sinistralidade`, `geracao_vidas`, `geracao_custo`, `geracao_risco`) recebe a competência como parâmetro explícito — não há estado global de "qual mês estamos processando", evitando duas fontes de verdade divergentes.

### 2.2 Staging em disco antes da carga (`extract/save_monthly_csv.py`)
Antes de ir para o BigQuery, cada DataFrame é persistido como CSV local (`;` como delimitador, `utf-8-sig`, um arquivo por dataset/competência). Esse é o padrão clássico de **zona de staging**: desacopla a geração dos dados da carga, permite inspecionar o arquivo intermediário caso algo dê errado, e é o formato que o `LoadJobConfig` do BigQuery client consome via `load_table_from_file`.

### 2.3 Carga incremental por partição (`load/bigquery_load.py`)
Este é o núcleo de engenharia de dados do projeto:

- **Partition Decorator**: cada carga é feita contra `tabela$YYYYMMDD` (ex.: `sinistralidade_operadora_pre_pgto$20260801`), não contra a tabela inteira. Isso significa que o `WRITE_TRUNCATE` (sobrescreve) afeta **apenas a partição do dia/competência sendo processada**, nunca o histórico completo. É o que torna o reprocessamento seguro.
- **Partição nativa por DIA** (`bigquery.TimePartitioningType.DAY`): todas as 4 tabelas fato são criadas com particionamento diário sobre uma coluna de data (`data_pagamento`, `Mes` ou `data_ref`, conforme `TABLE_MAP` em `config/settings.py`). Particionar reduz o volume de dados escaneado em queries que filtram por data — impacto direto em custo e performance no BigQuery, que cobra por bytes lidos.
- **Criação de tabela sob demanda (`_garantir_tabela`)**: o schema é definido em código (`SCHEMAS`, tipado com `bigquery.SchemaField`) e a tabela só é criada se ainda não existir — infraestrutura de dados como código, não como passo manual no console.
- **Schema explícito e validado**: a carga usa `schema=SCHEMAS[tabela]` no `LoadJobConfig`, então divergências de tipo/coluna entre o CSV e o schema esperado falham na carga, não silenciosamente.

### 2.4 Idempotência via tabela de controle (`utils/bigquery_control.py`)
Uma tabela dedicada (`pipeline_execution_control`) registra `competencia | status | executado_em | detalhes` para cada execução. Antes de processar, `ja_processado()` consulta se já existe um registro `SUCCESS` para a competência. Esse é o padrão de **watermark/checkpoint de processamento**: garante que o pipeline seja seguro para re-execução (re-run) — se o Cloud Scheduler disparar duas vezes, ou se alguém rodar manualmente, não há duplicação nem custo de reprocessamento desnecessário.

### 2.5 Orquestração sem orquestrador dedicado (Cloud Scheduler + Cloud Run Jobs)
Não há Airflow/Dagster neste projeto — a orquestração é feita com duas peças gerenciadas do GCP:
- **Cloud Scheduler**: dispara via HTTP/OIDC, com cron `0 6 5 * *` (todo dia 5, 06:00, `America/Sao_Paulo`).
- **Cloud Run Jobs**: execução batch, sem servidor HTTP exposto, sem ingress público — o container "roda e termina" (`ENTRYPOINT ["python", "main.py"]`).

Para a cadência mensal e volume deste pipeline, essa combinação é suficiente e evita o overhead operacional de manter um orquestrador dedicado.

### 2.6 Infraestrutura como código (`terraform/`)
Toda a infraestrutura do GCP é declarada em Terraform, não criada manualmente:
- APIs habilitadas (`google_project_service`), Artifact Registry, dataset do BigQuery, Cloud Run Job, Cloud Scheduler.
- **Segurança por least privilege / separação de responsabilidades**: existem *três* service accounts distintas, cada uma com o mínimo de permissão necessária:
  - `sa-pipeline-runner`: identidade do container em runtime, só tem `dataEditor` no dataset (não no projeto) + `jobUser` no projeto (necessário para rodar load/query jobs, mas isso não concede acesso a dados por si só).
  - `sa-pipeline-scheduler`: identidade do Cloud Scheduler, só pode invocar (`run.invoker`) o Job — não tem nenhum acesso a BigQuery.
  - `sa-github-deployer`: usada só pelo CI/CD para build/push de imagem e atualização do Cloud Run Job.
- **Workload Identity Federation (WIF)**: o GitHub Actions autentica no GCP trocando o token OIDC do próprio workflow por credenciais temporárias — sem chave JSON estática armazenada como secret. O `attribute_condition` restringe a troca a um repositório específico.
- `lifecycle { ignore_changes = [...image] }` no Cloud Run Job evita que um `terraform apply` reverta a imagem para o placeholder inicial, já que quem atualiza a imagem em produção é o pipeline de CI/CD.

### 2.7 Containerização enxuta e não-root (`Dockerfile`)
Build em dois estágios (*multi-stage build*):
1. `builder`: instala as dependências Python.
2. Imagem final: copia só as dependências já instaladas e o código necessário (`config/`, `extract/`, `load/`, `utils/`, `main.py`) — sem cache de build, sem ferramentas de desenvolvimento.

A imagem final roda com um usuário não-root dedicado (`appuser`), reduzindo a superfície de ataque em caso de comprometimento do container. Não expõe porta HTTP, condizente com o modelo de execução batch do Cloud Run Jobs.

### 2.8 Observabilidade estruturada (`utils/logger.py`)
Logs são emitidos em **JSON estruturado** (`severity`, `message`, `logger`, `exception` quando aplicável) via `StreamHandler` no stdout. Esse formato é o esperado pelo Cloud Logging do GCP para indexação e alertas automáticos — logs de texto livre dificultariam consultas e alertas por severidade.

### 2.9 CI/CD com dois pipelines separados (`.github/workflows/`)
- `ci.yml`: lint (`ruff`), testes (`pytest --cov`) e build de validação da imagem Docker — roda em todo PR/push para branches que não sejam `main`.
- `.deploy.yml`: reaproveita o `ci.yml` como gate (`uses: ./.github/workflows/ci.yml`) antes de autenticar via WIF, buildar, publicar a imagem no Artifact Registry e atualizar o Cloud Run Job — roda em push para `main`, ignorando mudanças que só tocam `docs/`, `terraform/` ou arquivos `.md` (essas mudanças não precisam de novo deploy de container).

Isso implementa o princípio de **"nunca fazer deploy de código não testado"**: o job de deploy depende explicitamente do job de teste.

### 2.10 Testes automatizados (`tests/`)
Cada camada tem teste isolado, com fixtures compartilhadas (`tests/conftest.py`, incluindo um `fake_bq_client` mockado e uma `competencia` fixa para reprodutibilidade):
- `test_generate_csv.py`: valida colunas, ausência de nulos, invariantes de negócio (ex.: `VPP >= VPG`) dos dados gerados.
- `test_bigquery_load.py`: valida o partition decorator (`tabela$YYYYMMDD`) e `WRITE_TRUNCATE`, sem tocar num BigQuery real.
- `test_bigquery_control.py`: valida a lógica de idempotência (`ja_processado`/`registrar_execucao`).
- `test_main_flow.py`: valida o fluxo de orquestração ponta a ponta (com mocks).
- `test_save_monthly_csv.py`: valida a geração do CSV de staging.

---

## 3. Estrutura de pastas

```
.
├── main.py                      # orquestração: ponto de entrada do pipeline
├── config/
│   └── settings.py              # variáveis de ambiente + TABLE_MAP (dataset → tabela/partição)
├── extract/
│   ├── generate_csv.py          # geração dos DataFrames (sinistralidade, vidas, custo, risco)
│   └── save_monthly_csv.py      # staging em CSV local
├── load/
│   └── bigquery_load.py         # criação de tabela + carga incremental particionada
├── utils/
│   ├── bigquery_control.py      # tabela de controle / idempotência
│   └── logger.py                # logging JSON estruturado
├── tests/                       # pytest, um arquivo de teste por módulo
├── terraform/                   # infraestrutura como código (GCP)
│   ├── main.tf                  # recursos: APIs, IAM, BigQuery, Cloud Run Job, Scheduler, WIF
│   ├── variables.tf             # inputs configuráveis (projeto, região, cron, timezone, etc.)
│   ├── outputs.tf                # outputs úteis (nomes de recursos, service accounts, WIF)
│   └── versions.tf              # versão do Terraform e do provider google
├── .github/workflows/
│   ├── ci.yml                    # lint + testes + build de validação
│   └── .deploy.yml               # build, push e atualização do Cloud Run Job
├── Dockerfile                    # build multi-stage, imagem final não-root
└── view/                         # modelo semântico + relatório Power BI ("Resumo Executivo")
```

---

## 4. Modelo de dados (BigQuery)

Dataset: `health_care_lifes` (configurável via `bq_dataset_id`), localização `US`.

| Tabela | Origem (DataFrame) | Coluna de partição | Granularidade |
|---|---|---|---|
| `sinistralidade_operadora_pre_pgto` | `sinistralidade` | `data_pagamento` | dia |
| `vidas_operadoras` | `vidas` | `Mes` | dia |
| `custo_operadora_pos_pgto` | `custo` | `data_pagamento` | dia |
| `custo_por_risco_todas_operadoras` | `risco` | `data_ref` | dia |
| `pipeline_execution_control` | — (controle interno) | — | — |

O mapeamento dataframe → tabela/coluna de partição vive em um único lugar: `TABLE_MAP` em `config/settings.py`. Isso evita hardcode espalhado pelo código e é o ponto único de verdade para "onde cada dado gerado deve ser carregado".

---

## 5. Como rodar localmente

```bash
pip install -r requirements.txt -r requirements-dev.txt

export GCP_PROJECT_ID=meu-projeto-gcp
export BQ_DATASET=health_care_lifes        # opcional, tem default
export BQ_LOCATION=US                       # opcional, tem default

# processa o mês anterior ao atual (comportamento padrão)
python main.py

# ou força uma competência específica (formato AAAA-MM)
COMPETENCIA=2026-07 python main.py
```

Rodar os testes:

```bash
GCP_PROJECT_ID=ci-dummy-project pytest -q --cov=. --cov-report=term-missing
```

---

## 6. Deploy

O deploy é automático via GitHub Actions (`.deploy.yml`) a cada push em `main` (exceto mudanças só em `docs/`, `terraform/` ou `.md`). A infraestrutura em si (Terraform) **não** é aplicada automaticamente pelo workflow — é gerenciada separadamente, via `terraform apply` manual ou pipeline dedicado, usando os outputs de `terraform/outputs.tf` (nomes de recursos, service accounts, WIF) para configurar as variáveis de ambiente/secrets do GitHub Actions.

Variáveis/secrets esperados no GitHub Actions (repository variables): `GCP_REGION`, `GCP_PROJECT_ID`, `AR_REPO`, `CLOUD_RUN_JOB_NAME`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`.

---

## 7. Camada de visualização

A pasta `view/` contém o projeto Power BI (`.pbip`) "Sinistralidade e Custos - Resumo Executivo": modelo semântico (tabelas fato/dimensão, medidas DAX) e relatório com os visuais consumindo as tabelas do BigQuery carregadas por este pipeline.
