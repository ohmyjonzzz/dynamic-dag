terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "6.8.0"
    }
  }
}

provider "google" {
  credentials = file(var.google_credentials)
  project = var.project
  region = var.region
}

resource "google_storage_bucket" "simple_bucket" {
  name = var.gcs_bucket_name
  location = var.location
  force_destroy = true
}

resource "google_bigquery_dataset" "simple_dataset" {
  dataset_id = var.bq_dataset_name
  location = var.location
}