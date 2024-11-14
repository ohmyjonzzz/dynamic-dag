import os
from datetime import timedelta, datetime
from dotenv import load_dotenv

import csv
import json
import psycopg2
from google.cloud import bigquery, storage
from airflow import DAG
from airflow.operators.python_operator import PythonOperator

load_dotenv()

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME")
PG_CONNECTION = os.getenv("PG_CONNECTION")
GCS_BUCKET = os.getenv("GCS_BUCKET")

# Function to read configuration
def load_config():
    
    with open(f"{AIRFLOW_HOME}/dags/config.json") as f:
        config = json.load(f)
    return config

# Function to create tables in BigQuery
def create_bq_table(bigquery_table, schema):
    
    bq_client = bigquery.Client()
    schema_fields = [bigquery.SchemaField(field["name"], field["type"]) for field in schema]
    table = bigquery.Table(bigquery_table, schema=schema_fields)
    bq_client.create_table(table, exists_ok=True)

# Function to extract data from PostgreSQL and save to CSV
def extract_data_to_csv(table_name, connection, csv_path):
    
    conn = psycopg2.connect(connection)
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name}"
    cursor.execute(query)
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()

    # Save rows to CSV
    with open(csv_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)  # Write headers
        writer.writerows(rows)    # Write data

# Function to upload CSV to Google Cloud Storage
def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    
    # Create GCS client
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

# Function to load data from GCS to BigQuery
def load_data_from_gcs_to_bq(gcs_uri, bigquery_table, schema):
    
    schema_fields = [bigquery.SchemaField(field["name"], field["type"]) for field in schema]
    # Create BigQuery client
    bq_client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Skip header row in CSV
        schema=schema_fields
    )
    load_job = bq_client.load_table_from_uri(gcs_uri, bigquery_table, job_config=job_config)
    load_job.result()  # Waits for the job to complete
    print(f"Data loaded into BigQuery table {bigquery_table}.")

# Load configuration
config = load_config()

# Define the default arguments for the DAG
default_args = {
    "owner": "ohmyjons",
    "start_date": datetime.now(),
    "retries": 1,  # Number of retries if a task fails
    "retry_delay": timedelta(minutes=1),  # Time between retries
}

# Define the Airflow DAG
with DAG(
    "dynamic_dag",
    description="Dynamic DAG pipeline from PostgreSQL to BigQuery",
    default_args=default_args,
    start_date=datetime.now(),
    schedule_interval=None, # Set the schedule interval (e.g., None for manual runs)
    catchup=False  # Do not backfill (run past dates) when starting the DAG
) as dag:

    # Create separate tasks for each table dynamically
    for table in config["tables"]:

        table_name = table["table_name"]
        schema = table["schema"]
        bigquery_table = table["bigquery_table"]

        csv_path = f"{AIRFLOW_HOME}/data/{table_name}_data.csv"
        gcs_blob_name = f"{table_name}_data.csv"
        gcs_uri = f"gs://{GCS_BUCKET}/{gcs_blob_name}"

        # Task to create BigQuery table
        create_bq_table_task = PythonOperator(
            task_id=f"create_bq_table_{table_name}",
            python_callable=create_bq_table,
            op_args=[bigquery_table, schema]
        )

        # Task to extract data from PostgreSQL and save to CSV
        extract_data_task = PythonOperator(
            task_id=f"extract_data_to_csv_{table_name}",
            python_callable=extract_data_to_csv,
            op_args=[table_name, PG_CONNECTION, csv_path]
        )

        # Task to upload CSV to GCS
        upload_to_gcs_task = PythonOperator(
            task_id=f"upload_to_gcs_{table_name}",
            python_callable=upload_to_gcs,
            op_args=[GCS_BUCKET, csv_path, gcs_blob_name]
        )

        # Task to load data from GCS to BigQuery
        load_data_task = PythonOperator(
            task_id=f"load_data_from_gcs_to_bq_table_{table_name}",
            python_callable=load_data_from_gcs_to_bq,
            op_args=[gcs_uri, bigquery_table, schema]
        )

        # Set task dependencies for each table
        create_bq_table_task >> extract_data_task >> upload_to_gcs_task >> load_data_task