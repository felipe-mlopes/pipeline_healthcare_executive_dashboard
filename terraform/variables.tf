variable "project_id" {
    description = "ID do projeto GCP"
    type = string
}

variable "region" {
    description = "Região para Cloud Run Job / Artifact Registry"
    type = string
    default = "us-east4"
}

variable "bq_dataset_id" {
    description = "Dataset do BigQuery onde as tabelas do dashboard vivem"
    type = string
    default = "health_care_lifes"
}

variable "bq_location" {
    description = "Localização do dataset BigQuery"
    type = string
    default = "US"
}

variable "artifact_repo_name" {
    description = "Nome do repositório no Artifact Registry"
    type = string
    default = "pipeline-healthcare"
}

variable "job_name" {
    description = "Nome do Cloud Run Job"
    type = string
    default = "pipeline-healthcare-monthly"
}

variable "image_url" {
    description = "Imagem inicial do container (substituída depois pelo pipeline de CI/CD a cada deploy)"
    type = string
    default = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "scheduler_cron" {
    description = "Expressão cron do Cloud Scheduler (dia 05 de cada mês, 06:00)"
    type = string
    default = "0 6 5 * *"
}

variable "scheduler_timezone" {
    description = "Timezone do Cloud Scheduler"
    type = string
    default = "America/Sao_Paulo"
}

variable "job_max_retries" {
    description = "Número de retentativas do Cloud Run Job em caso de falha"
    type = number
    default = 1
}

variable "job_timeout_seconds" {
    description = "Timeout máximo de cada execução do Job"
    type = string
    default = "1800s"
}

variable "github_repository" {
    # ATENÇÃO: este default concede à identidade de deploy (WIF) confiança
    # explícita neste repositório específico. Se este projeto for usado como
    # base/fork por outra pessoa/organização, sobrescreva este valor — caso
    # contrário, o repositório abaixo continuaria autorizado a assumir a
    # identidade de deploy no projeto GCP de quem aplicar o Terraform.
    description = "Repositório GitHub autorizado a assumir a identidade de deploy via Workload Identity Federation, no formato owner/repo"
    type = string
    default = "felipe-mlopes/pipeline_healthcare_executive_dashboard"
}