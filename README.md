```markdown
# **Eat-express-pipeline**

A data ingestion and processing pipeline for food-order records. This repository contains:
- An interactive exploration notebook (exp.ipynb) that inspects and cleans sample data (food_daily.csv) using pandas.
- An Apache Beam pipeline (beam.py) intended to run on Google Cloud Dataflow (the Beam pipeline file should be present at gs://eats-express-bucket/beam.py for Dataflow use).
- An Airflow DAG (pipeline.py) that detects new files on GCS, moves them to a processed prefix, and triggers the Beam pipeline on Dataflow.

Goal: provide a reproducible ETL flow — ingest CSV order files, clean/normalize fields, split delivered vs. undelivered orders, persist outputs — and orchestrate the flow via Airflow + Google Dataflow.

Table of contents
- Project Overview
- What I inspected
- Architecture and flow
- Tools & main dependencies
- Files in this repo
- Quick start (local + cloud)
- Beam pipeline expectations (contract)
- Airflow DAG details
- Deployment notes (GCP / Dataflow / Airflow)
- Troubleshooting
- Next steps / TODOs
- Contributing / License

---

Project overview
---------------
This project reads daily food-order CSV files, performs text cleaning and normalization, and writes processed outputs (for example: delivered and undelivered files). The notebook (exp.ipynb) demonstrates exploratory data analysis and a simple Beam pipeline prototype. The Airflow DAG (pipeline.py) watches a Google Cloud Storage bucket, moves the new file into a processed/ prefix, and triggers the Beam pipeline on Google Dataflow.

What I inspected
----------------
- exp.ipynb — A Jupyter notebook that:
  - Loads `food_daily.csv` with pandas (shape: 891 rows × 11 columns).
  - Shows initial EDA: df.head(), df.tail(), df.describe(), df.info().
  - Includes helper functions to remove trailing `:` characters and to strip non-alphanumeric characters.
  - Uses Apache Beam in a notebook cell to demonstrate a pipeline that:
    - Reads CSV lines, applies `process_row`, lowercase conversion, removes special characters
    - Filters delivered vs. undelivered rows and writes to `outputs/processed/delivered*` and `outputs/processed/undelivered*`
- pipeline.py — An Airflow DAG that:
  - Uses a GCS sensor (`GCSObjectsWithPrefixExistenceSensor`) to detect new objects with prefix `food_daily` in `eats-express-bucket`.
  - A PythonOperator copies the first matching object into `processed/` on the same bucket and deletes original.
  - A `BeamRunPythonPipelineOperator` configured to run a Beam pipeline script located at `gs://eats-express-bucket/beam.py` on Dataflow.

Architecture & flow
-------------------
1. Producer uploads daily CSVs to gs://eats-express-bucket with prefix `food_daily`.
2. Airflow DAG `orders_pipeline` periodically polls the bucket.
3. When a file is found: the `check_file` task copies it to `processed/` and deletes the original, then returns the processed object path.
4. The DAG triggers the Beam pipeline (DataflowRunner) with the processed file path as the `input` parameter.
5. Beam pipeline reads the CSV, cleans lines, filters delivered/undelivered, and writes outputs (back to GCS or to chosen sink).

Tools & dependencies
--------------------
Primary tools used in the repo:
- Python (notebook kernel metadata shows Python 3.13.7)
- pandas — EDA and CSV inspection in the notebook
- Apache Beam — pipeline implementation (local DirectRunner for prototyping; DataflowRunner for production on GCP)
- Google Cloud Dataflow — managed runner for Beam (via `DataflowRunner`)
- Google Cloud Storage — storage for raw and processed files (gs://eats-express-bucket)
- Apache Airflow — DAG orchestration with providers:
  - apache-airflow-providers-apache-beam (BeamRunPythonPipelineOperator)
  - apache-airflow-providers-google (GCS sensor/hooks)
- Jupyter Notebook

Typical Python packages:
- apache-beam[gcp]
- pandas
- google-cloud-storage
- apache-airflow
- airflow-provider-google (or the matching provider package version)
- Note: exact pinned versions should be recorded in requirements.txt (not included yet).

Files in this repository
------------------------
- exp.ipynb — exploratory notebook that also contains a small Beam example executed in the notebook (DirectRunner).
- pipeline.py — Airflow DAG that sensors GCS and triggers the Beam pipeline via Dataflow.
- beam.py — expected Beam pipeline file (should accept CLI args like `--input` and `--output`); make sure this file exists at the GCS path referenced by the DAG (gs://eats-express-bucket/beam.py). If you want I can generate a canonical beam.py skeleton for your pipeline.

Quick start — locally
---------------------
1. Clone the repo:
   ```bash
   git clone https://github.com/dibanga2800/eat-express-pipeline.git
   cd eat-express-pipeline
   ```

2. Create a Python environment and install dependencies (example):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install pandas apache-beam jupyter google-cloud-storage
   # If you plan to run the notebook cell that uses interactive Beam visualization:
   pip install "apache-beam[interactive]"
   ```

3. Run the notebook:
   ```bash
   jupyter lab  # or jupyter notebook
   ```
   Open `exp.ipynb` and run cells in order. The notebook demonstrates:
   - Loading `food_daily.csv` (make sure the CSV is present in repo root or change path).
   - Data cleaning helper functions.
   - A small Beam pipeline executed in the notebook cells using the DirectRunner.

Run Beam pipeline locally (DirectRunner)
- Ensure beam.py accepts `--input` and `--output` arguments (see "Beam pipeline expectations" below).
- Example:
  ```bash
  python beam.py --input data/food_daily.csv --output outputs/processed
  ```
  Using DirectRunner will allow you to test transforms locally.

Airflow (local) — testing the DAG
- Install Airflow (pin versions appropriate for your environment). Example minimal steps (use constraints from Apache Airflow docs):
  ```bash
  pip install apache-airflow
  ```
- Place `pipeline.py` in your Airflow `dags/` folder.
- Configure Airflow to run with Google provider packages and authentication (GCP credentials for GCS access).
- Start Airflow webserver/scheduler and trigger the DAG.

Beam pipeline expectations (contract)
------------------------------------
Your `beam.py` should:
- Accept CLI args that Apache Beam expects (e.g., `--input`, `--output`, plus dataflow staging/temp/region flags when running on Dataflow).
- Support both DirectRunner (for local prototyping) and DataflowRunner (for production):
  - Example minimal CLI signature:
    ```
    python beam.py --input gs://eats-express-bucket/processed/food_daily-2025-10-01.csv --output gs://eats-express-bucket/outputs/processed
    ```
- Read CSV lines, apply the same cleaning functions as in the notebook:
  - remove trailing `:` on items
  - remove special characters (non-alphanumeric)
  - lowercase normalization
- Split or route results (e.g., delivered vs undelivered) as required and write outputs.
- When targeting Dataflow, the Beam job should use argparse to accept pipeline options forwarded by `BeamRunPythonPipelineOperator`.

Example skeleton for `beam.py` (adapt and expand in your repo):
```python
# beam.py (skeleton)
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, StandardOptions
import argparse
import re

def process_row(line):
    # implement cleaning steps, similar to notebook functions
    # line is a CSV string; consider using csv module for robust parsing
    columns = line.split(',')
    # example: remove trailing colon on column 4
    if len(columns) > 4 and columns[4].endswith(':'):
        columns[4] = columns[4][:-1]
    # remove non-alphanumeric, lowercase, etc.
    cleaned = [re.sub(r'[^a-zA-Z0-9 ]', '', c).lower() for c in columns]
    return ','.join(cleaned)

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)
    with beam.Pipeline(options=pipeline_options) as p:
        lines = p | 'Read' >> beam.io.ReadFromText(known_args.input, skip_header_lines=1)
        cleaned = lines | 'Clean' >> beam.Map(process_row)

        delivered = (cleaned
                     | 'FilterDelivered' >> beam.Filter(lambda r: r.split(',')[8].strip() == 'delivered')
                     | 'WriteDelivered' >> beam.io.WriteToText(known_args.output + '/delivered'))
        undelivered = (cleaned
                       | 'FilterUndelivered' >> beam.Filter(lambda r: r.split(',')[8].strip() != 'delivered')
                       | 'WriteUndelivered' >> beam.io.WriteToText(known_args.output + '/undelivered'))

if __name__ == '__main__':
    run()
```

Airflow DAG details (pipeline.py)
--------------------------------
- DAG id: `orders_pipeline`
- Schedule: `@daily`
- Tasks:
  - `gcs_sensor` — waits for objects with prefix `food_daily` in bucket `eats-express-bucket`
  - `check_file` — PythonOperator that:
    - lists the objects with the prefix
    - copies the first object to `processed/{filename}` and deletes the source
    - returns the destination object path (XCom)
  - `beam_task` — BeamRunPythonPipelineOperator configured to run `gs://eats-express-bucket/beam.py` via DataflowRunner, with pipeline_options containing `'input': "gs://eats-express-bucket/{{task_instance.xcom_pull('check_file')}}"`

Important Airflow / GCP notes:
- The Airflow worker must have permissions to:
  - list/read/write/delete objects in the GCS bucket (use a service account or GCP credentials).
  - submit Dataflow jobs (Dataflow API enabled, appropriate IAM).
- The DAG uses `BeamRunPythonPipelineOperator` and `DataflowConfiguration`. The `py_file` points at `gs://.../beam.py` — ensure beam.py is uploaded there and readable by Dataflow worker service account.
- The `pipeline_options` dictionary in `BeamRunPythonPipelineOperator` should typically include staging_location, temp_location, region/project, and other Dataflow options. In the current DAG they supply `input` only — you will likely want to expand this to include staging/temp GCS locations and other options or pass them via operator arguments.

Deployment notes (GCP / Dataflow / Airflow)
------------------------------------------
1. GCP setup
   - Create/choose a GCP project and enable:
     - Dataflow API
     - Cloud Storage
   - Create `gs://eats-express-bucket` or update bucket references in `pipeline.py`.
   - Upload `beam.py` to `gs://eats-express-bucket/beam.py` or update DAG to point to actual path.
2. Airflow setup
   - Ensure Airflow includes Google provider packages and the Apache Beam provider.
   - Configure GCP connection credentials in Airflow (Connections > Google Cloud).
   - Put `pipeline.py` in your Airflow `dags/` directory.
3. Dataflow job options
   - Provide `staging_location` and `temp_location` in pipeline options or operator configuration.
   - Ensure the service account used to run Dataflow jobs has permission to read/write the specified GCS buckets and to run Dataflow.

Environment variables / configuration examples
----------------------------------------------
- GCP project:
  - `GCP_PROJECT=eats-express-472311` (example in pipeline.py)
- Bucket:
  - `GCS_BUCKET=eats-express-bucket`
- Dataflow region / location:
  - `DATAFLOW_REGION=us-central1`
- Airflow connections:
  - `google_cloud_default` with JSON key file or workload identity

Troubleshooting
---------------
- "No beam.py found at gs://..." — upload beam.py or update DAG.
- Permissions errors reading/writing GCS — verify service account and IAM permissions.
- Dataflow job fails — check logs in Dataflow UI; ensure pipeline options (staging/temp) are set.
- Airflow sensor times out — increase `timeout` or ensure files arrive in the bucket.

Next steps / TODOs
------------------
- Add or confirm `beam.py` in repository and upload to the GCS path referenced by the DAG.
- Add a `requirements.txt` with pinned versions for reproducibility.
- Add unit tests and CI (GitHub Actions) to lint and run pipeline unit tests.
- Consider adding (or clarifying) an Express service if you intend to serve pipeline results via a Node/Express API (current repo files don't contain an Express app).

Contributing
------------
- Fork, create a branch, add features or fixes, open a pull request. Include tests and update documentation.

License
-------
Add your license (e.g., MIT). If none is present, repository is currently unlicensed.

Contact
-------
Repository owner: @dibanga2800

Acknowledgements
----------------
- Apache Beam, Google Cloud Dataflow, Apache Airflow and pandas for tooling used in this repo.

```
