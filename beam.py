
import csv
import re
import apache_beam as beam
import argparse
from google.cloud import bigquery
from apache_beam.options.pipeline_options import PipelineOptions


#Define Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--input', dest='input', required=True, help = 'Input file to process')
paths_args, pipelines_args = parser.parse_known_args()

#Define Variables
input_file = paths_args.input


delivered_table_spec ='eats-express-472311:eats_express_dataset.delivered_orders'
others_table_spec ='eats-express-472311:eats_express_dataset.other_status_orders'

# Dataset creation will be handled by BigQuery when using CREATE_IF_NEEDED


Schema =[
    "STRING", "STRING", "STRING", "STRING", "STRING", "FLOAT", "STRING", "STRING", "STRING", "FLOAT", "STRING"
]

class ProcessRowFn(beam.DoFn):
    def remove_last_column(self, item):
        if item.endswith(':'):
            return item[:-1]
        return item

    def process(self, row):
        columns = row.split(',')
        if len(columns) > 4:
            columns[4] = self.remove_last_column(columns[4])
        yield ','.join(columns)



class RemoveSpecialCharactersFn(beam.DoFn):
    def __init__(self, schema):
        self.schema = schema

    def remove_special_characters(self, row):
        columns =row.split(',')
        ret = ''
        for col in columns:
            ret+= re.sub(r'[^a-zA-Z0-9]', '', col) + ','
        return ret[:-1]
    
    def process(self, row):
        cols = row.split(',')
        cleaned_cols = []
        for i, (col, col_type) in enumerate(zip(cols, self.schema)):
            if col_type == 'STRING':
                col = re.sub(r'[^a-zA-Z0-9 .]', '', col)  # Keep spaces and dots for readability
            elif col_type == 'FLOAT':
                # Ensure numeric values are clean
                col = re.sub(r'[^0-9.]', '', col) if col else '0'
            cleaned_cols.append(col)
        yield ','.join(cleaned_cols)

        

def print_row(row):
    print(row)

def to_json(row):
    fields = row.split(',')
    # Handle empty or missing values gracefully
    def safe_float(val, default=0.0):
        try:
            return float(val) if val and val.strip() else default
        except ValueError:
            return default
    
    def safe_int(val, default=1):
        try:
            return int(val) if val and val.strip() else default
        except ValueError:
            return default
    
    return {
        'Customer_id': fields[0] if len(fields) > 0 else '',
        'date': fields[1] if len(fields) > 1 else '',
        'timestamp': fields[2] if len(fields) > 2 else '',
        'order_id': fields[3] if len(fields) > 3 else '',
        'items': fields[4] if len(fields) > 4 else '',
        'amount': safe_float(fields[5] if len(fields) > 5 else '0'),
        'mode': fields[6] if len(fields) > 6 else '',
        'restaurant': fields[7] if len(fields) > 7 else '',
        'Status': fields[8] if len(fields) > 8 else '',
        'ratings': safe_float(fields[9] if len(fields) > 9 else '0'),
        'feedback': fields[10] if len(fields) > 10 else '',
        'count': safe_int(fields[11] if len(fields) > 11 else '1')
    }


table_schema = '''
    Customer_id:STRING,
    date:STRING,
    timestamp:STRING,
    order_id:STRING,
    items:STRING,
    amount:FLOAT,
    mode:STRING,
    restaurant:STRING,
    Status:STRING,
    ratings:FLOAT,
    feedback:STRING,
    count:INTEGER
'''

options=PipelineOptions(pipelines_args)

with beam.Pipeline(options=options) as p:
    cleaned_data = (
        p
        | 'Read Input file' >> beam.io.ReadFromText(input_file, skip_header_lines=1)
        | 'Process Items Column' >> beam.ParDo(ProcessRowFn())
        | 'Convert to lowercase' >> beam.Map(lambda row: row.lower())
        | 'Remove Special Characters' >> beam.ParDo(RemoveSpecialCharactersFn(Schema))
        | 'Add Count Column' >> beam.Map(lambda row: row + ',1')
    )

    delivered_orders = (
        cleaned_data
        | 'Filter delivered data' >> beam.Filter(lambda row: row and row.split(',')[8].lower() == 'delivered')
    )
    undelivered_orders = (
        cleaned_data
        | 'Filter undelivered data' >> beam.Filter(lambda row: row and row.split(',')[8].lower() != 'delivered')
    )
    (delivered_orders
     | 'Delivered to JSON' >> beam.Map(to_json)
     | 'Write Delivered order to BigQuery' >> beam.io.WriteToBigQuery(
         delivered_table_spec, 
         schema=table_schema,
         create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
         write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
         additional_bq_parameters={'timePartitioning': {'type': 'DAY'}}
         )
    )
    (undelivered_orders
     | 'Undelivered to JSON' >> beam.Map(to_json)
     | 'Write Undelivered order to BigQuery' >> beam.io.WriteToBigQuery(
         others_table_spec, 
         schema=table_schema,
         create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
         write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
         additional_bq_parameters={'timePartitioning': {'type': 'DAY'}}
         )
    )