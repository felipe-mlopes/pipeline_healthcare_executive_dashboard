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
# já particionadas por mês; aqui garantimos apenas o dataset)
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
# Cloud Scheduler — dispara o Job todo dia 1 de cada mês
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