# Eat Express Pipeline

A data pipeline for processing food delivery orders, reviews, and analytics — powered by Apache Beam, Airflow, and Google Cloud Platform.

---

## Tech Stack

- **Python**: Main programming language for all pipeline logic and scripting.
- **Apache Beam**: Data processing and transformation framework.
- **Apache Airflow**: Orchestration and scheduling of pipeline tasks.
- **Google Cloud Storage (GCS)**: Storage for input and output data files.
- **Google BigQuery**: Data warehouse for analytics and reporting.
- **Google Dataflow**: Managed Apache Beam runner for scalable processing.
- **Pandas**: Data analysis and exploration in Jupyter Notebooks.
- **Jupyter Notebook**: Exploration, visualizations, and reporting.

---

## Features

- Automated ingestion and processing of daily food order files.
- Cleans and transforms order data (removes special characters, formats columns).
- Loads processed data into BigQuery for analytics.
- Orchestrates workflow using Airflow DAGs and operators.
- Supports exploratory analysis and reporting in Jupyter Notebook.

---

## Getting Started

1. **Clone the repository**
    ```bash
    git clone https://github.com/dibanga2800/eat-express-pipeline.git
    cd eat-express-pipeline
    ```
2. **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Set up your GCP credentials**  
   Ensure your environment is authenticated for Google Cloud (BigQuery, GCS, Dataflow).

4. **Configure Airflow**  
   Add your DAG and connection configuration as documented in your Airflow setup.
   
5. **Run the pipeline**
    - Trigger via Airflow scheduler or manually using Airflow UI.
    - For direct Beam jobs, run:
      ```bash
      python beam.py --input <your-input-file> --output <your-output-dir>
      ```

---

## Example Workflow

![Workflow Diagram](assets/architecture.png)

---

## Contributing

Pull requests, feature ideas, and bug reports are welcome!  
Open an issue, fork the repo, and submit your changes.

---

## License

Licensed under the MIT License.

---

## Contact

Questions? Reach out via [GitHub Issues](https://github.com/dibanga2800/eat-express-pipeline/issues).
