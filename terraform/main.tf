# ---------------------------------------------------------------------------
# APIs necessárias
# ---------------------------------------------------------------------------
locals {
    required_apis = [
    "run.googleapis.com",
    "cloudscheduler.googleapis.com",
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    ]
}

resource "google_project_service" "apis" {
    for_each = toset(local.required_apis)
    project = var.project_id
    service = each.value

    disable_dependent_services = false
    disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry — repositório privado da imagem do pipeline
# ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "pipeline_repo" {
    project = var.project_id
    location = var.region
    repository_id = var.artifact_repo_name
    format = "DOCKER"
    description = "Imagens do pipeline mensal do dashboard executivo de saúde"

    depends_on = [ google_project_service.apis ]
}

# ---------------------------------------------------------------------------
# Service Accounts — separação de responsabilidades (least privilege)
#   1. job_runner        -> identidade do CONTAINER em execução (acesso a dados)
#   2. scheduler_invoker  -> identidade do SCHEDULER, só pode "invocar" o Job
#      (não tem NENHUM acesso a BigQuery)
# ---------------------------------------------------------------------------
resource "google_service_account" "job_runner" {
    project = var.project_id
    account_id = "sa-pipeline-runner"
    display_name = "Pipeline Healthcare - Job Runner (container)"
}

resource "google_service_account" "scheduler_invoker" {
    project = var.project_id
    account_id = "sa-pipeline-scheduler"
    display_name = "Pipeline Healthcare - Cloud Scheduler invoker"
}

# ---------------------------------------------------------------------------
# BigQuery — dataset (as tabelas são criadas em runtime pelo próprio código,
# já particionadas por dia; aqui garantimos apenas o dataset)
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "health_care_lifes" {
    project = var.project_id
    dataset_id = var.bq_dataset_id
    location = var.bq_location

    depends_on = [ google_project_service.apis ]
}

# Acesso de dados restrito AO DATASET (não ao projeto inteiro) — least privilege
resource "google_bigquery_dataset_iam_member" "job_runner_data_editor" {
    project = var.project_id
    dataset_id = google_bigquery_dataset.health_care_lifes.dataset_id
    role = "roles/bigquery.dataEditor"
    member = "serviceAccount:${google_service_account.job_runner.email}"
}

# roles/bigquery.jobUser é necessário para RODAR load/query jobs — é uma
# permissão de projeto (não existe no nível de dataset), mas não concede
# acesso a dados de nenhum dataset por si só.
resource "google_project_iam_member" "job_runner_job_user" {
    project = var.project_id
    role = "roles/bigquery.jobUser"
    member = "serviceAccount:${google_service_account.job_runner.email}"
}

# ---------------------------------------------------------------------------
# Cloud Run Job — execução batch mensal (sem HTTP, sem ingress público)
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_job" "pipeline_job" {
    project = var.project_id
    name = var.job_name
    location = var.region

    template {
        template {
            service_account = google_service_account.job_runner.email
            max_retries = var.job_max_retries
            timeout = var.job_timeout_seconds

            containers {
                image = var.image_url

                env {
                    name = "CGP_PROJECT_ID"
                    value = var.project_id
                }
                env {
                    name = "BQ_DATASET"
                    value = var.bq_dataset_id
                }
                env {
                    name = "BQ_LOCATION"
                    value = var.bq_location
                }

                resources {
                    limits = {
                        cpu = "1"
                        memory = "1Gi"
                    }
                }
            }
        }
    }

    # A imagem é atualizada pelo pipeline de CI/CD (gcloud run jobs update);
    # não queremos que `terraform apply` reverta para o placeholder inicial.
    lifecycle {
        ignore_changes = [ template[0].template[0].containers[0].image ]
    }

    depends_on = [ google_project_service.apis ]
}

# Só a identidade do Scheduler pode invocar o Job — nada de acesso público/unauthenticated.
resource "google_cloud_run_v2_job_iam_member" "scheduler_can_invoker" {
    project = var.project_id
    location = var.region
    name = google_cloud_run_v2_job.pipeline_job.name
    role = "roles/run.invoker"
    member = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

# ---------------------------------------------------------------------------
# Cloud Scheduler — dispara o Job todo dia 5 de cada mês
# ---------------------------------------------------------------------------
resource "google_cloud_scheduler_job" "monthly_trigger" {
    project = var.project_id
    region = var.region
    name = "pipeline-healthcare-monthly-trigger"
    schedule = var.scheduler_cron
    time_zone = var.scheduler_timezone

    http_target {
        http_method = "POST"
        uri = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"

        oidc_token {
            service_account_email = google_service_account.scheduler_invoker.email
        }
    }

    depends_on = [ 
        google_project_service.apis,
        google_cloud_run_v2_job_iam_member.scheduler_can_invoker
    ]
}

# ---------------------------------------------------------------------------
# Workload Identity Federation — permite o GitHub Actions autenticar no GCP
# sem chave JSON estática, trocando o token OIDC do próprio workflow por
# credenciais temporárias de uma service account dedicada ao deploy.
# ---------------------------------------------------------------------------
data "google_project" "current" {
    project_id = var.project_id
}

resource "google_iam_workload_identity_pool" "github_pool" {
    project = var.project_id
    workload_identity_pool_id = "github-actions-pool"
    display_name = "GitHub Actions"
    description = "Pool de identidade federada para deploys via GitHub Actions"

    depends_on = [ google_project_service.apis ]
}

resource "google_iam_workload_identity_pool_provider" "github_provider" {
    project = var.project_id
    workload_identity_pool_id = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
    workload_identity_pool_provider_id = "github-actions-provider"
    display_name = "GitHub Actions OIDC"

    attribute_mapping = {
        "google.subject" = "assertion.sub"
        "attribute.repository" = "assertion.repository"
        "attribute.repository_owner" = "assertion.repository_owner"
    }

    # Restringe QUAL repositório pode trocar o token OIDC por credenciais do GCP.
    # Sem isso, qualquer repositório do GitHub (de qualquer usuário) que soubesse
    # o resource name do provider poderia tentar se autenticar.
    attribute_condition = "assertion.repository == \"${var.github_repository}\""

    oidc {
        issuer_uri = "https://token.actions.githubusercontent.com"
    }
}

# Service account dedicada ao pipeline de deploy (não confundir com job_runner,
# que é a identidade do CONTAINER em runtime). Esta SA só existe pro GitHub
# Actions fazer push de imagem e atualizar o Cloud Run Job.
resource "google_service_account" "github_deployer" {
    project = var.project_id
    account_id = "sa-github-deployer"
    display_name = "GitHub Actions - Deploy pipeline"
}

# Permite push de imagens no Artifact Registry
resource "google_project_iam_member" "deployer_artifact_writer" {
    project = var.project_id
    role = "roles/artifactregistry.writer"
    member = "serviceAccount:${google_service_account.github_deployer.email}"
}

# Permite atualizar/gerenciar o Cloud Run Job (gcloud run jobs update)
resource "google_project_iam_member" "deployer_run_developer" {
    project = var.project_id
    role = "roles/run.developer"
    member = "serviceAccount:${google_service_account.github_deployer.email}"
}

# O Cloud Run exige que quem atualiza um Job também tenha permissão de "agir
# como" a service account que o Job vai usar em runtime (job_runner) — sem
# isso, o deploy falha com "iam.serviceaccounts.actAs" negado.
resource "google_service_account_iam_member" "deployer_can_act_as_job_runner" {
    service_account_id = google_service_account.job_runner.name
    role = "roles/iam.serviceAccountUser"
    member = "serviceAccount:${google_service_account.github_deployer.email}"
}

# Vincula o repositório GitHub (via WIF) à permissão de impersonar a SA de
# deploy — só workflows rodando DENTRO desse repositório específico podem
# assumir essa identidade.
resource "google_service_account_iam_member" "github_can_impersonate_deployer" {
    service_account_id = google_service_account.github_deployer.name
    role = "roles/iam.workloadIdentityUser"
    member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_repository}"
}