import csv
import re
import apache_beam as beam
import argparse
from apache_beam.options.pipeline_options import PipelineOptions


#Define Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--input', dest='input', required=True, help = 'Input file to process')
parser.add_argument('--output', dest='output', default='outputs/', help = 'Output directory')
paths_args, pipelines_args = parser.parse_known_args()

#Define Variables
input_file = paths_args.input
output_dir = paths_args.output

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

def to_json_string(row):
    fields = row.split(',')
    # CSV has 11 columns + 1 added count column = 12 total
    result = {
        'Customer_id': fields[0],
        'date': fields[1],
        'timestamp': fields[2],
        'order_id': fields[3],
        'items': fields[4],
        'amount': fields[5],
        'mode': fields[6],
        'restaurant': fields[7],
        'Status': fields[8],
        'ratings': fields[9],
        'feedback': fields[10],
        'count': fields[11] if len(fields) > 11 else '1'
    }
    return str(result)

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
     | 'Delivered to String' >> beam.Map(to_json_string)
     | 'Write Delivered orders to file' >> beam.io.WriteToText(output_dir + 'delivered', file_name_suffix='.txt')
    )
    
    (undelivered_orders
     | 'Undelivered to String' >> beam.Map(to_json_string)
     | 'Write Undelivered orders to file' >> beam.io.WriteToText(output_dir + 'undelivered', file_name_suffix='.txt')
    )