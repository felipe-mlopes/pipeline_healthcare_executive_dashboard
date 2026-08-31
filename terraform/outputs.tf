output "artifact_registry_repo" {
    value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repo_name}"
}

output "cloud_run_job_name" {
    value = google_cloud_run_v2_job.pipeline_job.name
}

output "job_runner_service_account" {
    value = google_service_account.job_runner.email
}

output "scheduler_invoker_service_account" {
    value = google_service_account.scheduler_invoker.email
}

output "bigquery_dataset" {
    value = google_bigquery_dataset.health_care_lifes.dataset_id
}

output "scheduler_job_name" {
    value = google_cloud_scheduler_job.monthly_trigger.name
}