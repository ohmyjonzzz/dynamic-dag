# Dynamic DAGs in Apache Airflow

This repository demonstrates a Dynamic DAG implementation in Apache Airflow, designed to simplify the management of multiple ETL tasks by leveraging a configuration file. This setup enables automatic generation of DAGs based on the tables and schemas defined in a config.json file, making it highly scalable and adaptable for complex data workflows.

## Features
- Dynamic DAG Generation: Automatically creates DAGs for multiple tables based on configurations.
- Configurable Schema: Supports schema definitions in config.json to customize data processing per table.
- Simplified ETL Process: Automates and standardizes ETL pipelines for tables in the same workflow.
- Scalable & Maintainable: Streamlines setup and maintenance of DAGs in a multi-table environment.

## Prerequisites
- Apache Airflow
- Python
- Database Connections (PostgreSQL, BigQuery, or other sources)
- Docker (optional)
