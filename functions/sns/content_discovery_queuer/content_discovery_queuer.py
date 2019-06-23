import boto3
import json
import os
import error_handler

def lambda_handler(event, context):
    print(event)
    try:
        message = json.loads(event  ['Records'][0]["Sns"]["Message"])
        print(message)
        target_record = message['target_record']
        project_id = message["project_id"]
        scan_type = message['scan_type']
        additional_params = message['additional_params']

        scan_list = get_scan_list(scan_type)
        chunks = get_chunks(scan_list)
        task_num = 1
        for chunk in chunks:
            message = format_message(project_id, target_record, chunk, task_num, additional_params)
            queue_message(scan_type, message)
            task_num += 1
    except Exception as e:
        error_handler.handleError(e)

def get_scan_list(scan_type):
    s3 = boto3.resource('s3')
    obj = s3.Object(os.environ["CoreBucketRef"], 'scan-lists/hs_' + scan_type + '.txt')
    return obj.get()['Body'].read().decode('utf-8').split('\n')


def get_chunks(l):
    for i in range(0, len(l), 100):
        yield l[i:i + 100]


def format_message(project_id, target_record, scan_list, task_num, additional_params):
    return {
        'project_id': project_id,
        'target_record': target_record,
        'scan_list': scan_list,
        'task_number': task_num,
        'additional_params':additional_params
    }

def queue_message(scan_type, message):
    arn = os.environ[scan_type.capitalize() + "ScanArn"]
    print(arn)
    client = boto3.client('sns')
    response = client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')
