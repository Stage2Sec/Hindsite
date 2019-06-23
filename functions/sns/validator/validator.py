import boto3
import json
import socket
import os
import error_handler
import database


def lambda_handler(event, context):
    print(event)
    try:
        message = json.loads(event['Records'][0]["Sns"]["Message"])
        target_record = message['target_record']
        target = get_target(target_record)
        project_id = message['project_id']

        if is_valid_target(target):
            queue_target(target_record, project_id)
        else:
            database.mark_target_invalid(cur, target)
    except Exception as e:
        error_handler.handleError(e)

def get_target(target_record):
    return target_record['host'] if target_record['host'] is not '' else target_record['ip']

def is_valid_target(target):
    #need to validate if domain or IP is given
    #check if host is actually reachable to help timeout issues?
    try:
        socket.gethostbyname(target)
        return True
    except socket.gaierror:
        return False

def queue_target(target_record, project_id):
    arn = os.environ["ValidatedTargetsArn"]
    message = {"target_record": target_record, "project_id": project_id, 'scan_type': 'port', "additional_params":[]}
    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')