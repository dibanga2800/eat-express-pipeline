from airflow import DAG
from datetime import datetime, timedelta
from airflow.providers.apache.beam.operators.beam import BeamRunPythonPipelineOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowConfiguration
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.standard.operators.python import PythonOperator
from google.cloud.storage import Client

default_args={
    'owner': 'airflow',
    'start_date': datetime(2024, 10, 1),
    'retries': 3,
    'retry_delay': timedelta(seconds=60),
}

def check_file_existence(bucket_name, prefix, processed_prefix='processed/'):
    gcs_hook = GCSHook()
    files = gcs_hook.list(bucket_name, prefix=prefix)

    if files:
        source_object = files[0]
        file_name = source_object.split('/')[-1]
        destination_object = processed_prefix.rstrip('/') + '/' + file_name

        storage_client = Client()
        bucket = storage_client.get_bucket(bucket_name)
        source_blob = bucket.blob(source_object)

        destination_blob = bucket.blob(destination_object)
        destination_blob.upload_from_string(source_blob.download_as_text())

        #Delete the source blob
        source_blob.delete()
        return destination_object
    else:
        return None
    
with DAG(
    'orders_pipeline',
    default_args=default_args,
    schedule='@daily',
    catchup=False,
    max_active_runs=1) as dag:

    gcs_sensor = GCSObjectsWithPrefixExistenceSensor(
        task_id='gcs_sensor',
        bucket='eats-express-bucket',
        prefix ='food_daily',
        poke_interval=60,
        timeout=300,
    )

    check_file = PythonOperator(
        task_id='check_file',
        python_callable=check_file_existence,
        op_kwargs={
            'bucket_name': 'eats-express-bucket',
            'prefix': 'food_daily',
        },
        do_xcom_push=True,
    )
    beam_task = BeamRunPythonPipelineOperator(
        task_id='beam_task',
        runner='DataflowRunner',
        py_file='gs://eats-express-bucket/beam.py',
        pipeline_options={
            'input': "gs://eats-express-bucket/{{task_instance.xcom_pull('check_file')}}",
           
        },
        py_options=[],
        py_interpreter='python3',
        py_system_site_packages=False,
        dataflow_config=DataflowConfiguration(
            job_name='food-orders-pipeline',
            location='us-central1',
            project_id='eats-express-472311',

        )
)    
    gcs_sensor >> check_file >> beam_task