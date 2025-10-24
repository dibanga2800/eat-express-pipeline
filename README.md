
# Eat-express-pipeline

eat-express-pipeline is a small, production-oriented ETL orchestration that ingests daily food-order CSVs, performs cleaning and normalization, and runs scalable processing using Apache Beam on Google Cloud Dataflow. The pipeline is orchestrated with Apache Airflow and prototyped in a Jupyter notebook for exploration.

Why this project exists
-----------------------
Retail/food-order datasets are messy: inconsistent casing, punctuation inside item lists, stray separators, and inconsistent status labels. This project demonstrates a simple pattern for:
- validating and cleaning raw CSV order files,
- splitting or routing records (e.g., delivered vs. undelivered),
- running the transforms at scale with Beam/Dataflow,
- scheduling and operationalizing the workflow using Airflow.

Core components (what each piece does)
--------------------------------------
- exp.ipynb (notebook)
  - Purpose: explore sample data, confirm column meanings and distributions, and prototype the text-cleaning transforms.
  - Role: serves as the human-first design stage for the pipeline logic (what to clean and why).
- beam.py (Beam pipeline script — expected)
  - Purpose: implement the production Beam pipeline that reads raw CSV lines, applies the cleaning transforms derived from the notebook, and writes results (for example, separate outputs for delivered vs. undelivered).
  - Role: production executable run locally with DirectRunner or on Dataflow with DataflowRunner.
- pipeline.py (Airflow DAG)
  - Purpose: watch a GCS prefix for incoming daily files, move the discovered file into a processed/ prefix, and trigger the Beam job on Dataflow with the processed file as input.
  - Role: orchestration and scheduling (retries, dependencies, pluggable operators).

High-level data flow
--------------------
1. Raw CSV uploaded to GCS under the configured bucket/prefix (e.g., gs://eats-express-bucket/food_daily...).
2. Airflow sensor detects a new file.
3. A DAG task copies the file to `processed/` and returns the new path.
4. Airflow submits the Beam job (DataflowRunner) pointing at the processed file.
5. Beam reads lines, cleans and normalizes fields, and writes outputs (cleaned files or partitioned sinks).

Key cleaning/normalization steps (from the notebook)
----------------------------------------------------
- Remove trailing/leading separators in item lists (e.g., trailing colons).
- Strip non-alphanumeric characters that corrupt parsing.
- Normalize casing (lowercase canonicalization).
- Robust CSV parsing to avoid splitting item lists that contain separators.

Important design notes
----------------------
- The notebook is the single source for the data transformation intent; Beam must faithfully implement those exact transforms for consistency.
- When running on Dataflow, the Beam job needs proper pipeline options (staging/temp locations, project, region) and the script must accept CLI args like `--input` and `--output`.
- Airflow must be configured with GCP credentials that have permissions to access GCS and submit Dataflow jobs.

Required tools & environment (overview)
---------------------------------------
- Python (notebook and pipeline code)
- Jupyter for exploration
- pandas for EDA
- Apache Beam (local DirectRunner for dev; DataflowRunner for production)
- Google Cloud Platform: Storage (GCS) and Dataflow
- Apache Airflow with Google & Beam providers installed
- A service account with GCS and Dataflow permissions for Airflow to use

Operational considerations
--------------------------
- Ensure beam.py is uploaded to the GCS location referenced by the DAG or adjust the DAG to point to the correct path.
- Confirm Airflow’s connection/credentials to GCP—Airflow workers and the Dataflow job must have appropriate IAM roles.
- Add staging and temp locations to your Dataflow options to avoid runtime failures.
- Use the notebook to add unit tests for small cleaning functions; test those with DirectRunner before submitting to Dataflow.

Where to look in this repository
-------------------------------
- exp.ipynb — open and run the notebook to see the data and the prototype transforms.
- pipeline.py — review the Airflow DAG to understand scheduling, sensor settings, and the Dataflow submission logic.
- beam.py — if present, confirm it implements the notebook cleaning logic and accepts pipeline options; if missing, create it based on the notebook.

Next recommended actions
------------------------
- Add (or confirm) a production-ready beam.py that implements the notebook’s transforms and accepts standard pipeline args.
- Add a short requirements.txt with pinned package versions and a minimal README (this document) in the repo root.
- Configure Airflow with GCP credentials and test the DAG end-to-end using a small sample file (DirectRunner for early testing, then Dataflow).

Contact
-------
Owner: @dibanga2800

License
-------
No license specified. Add a LICENSE file if you want to clarify reuse terms.
