import boto3
import json
import os
import error_handler
import database

def lambda_handler(event, context):
    print(event)
    try:
        message = json.loads(event['Records'][0]["Sns"]["Message"])
        project_id = message['project_id']
        scan_id = message['scan_id']
        target_records = database.getProjectScanTargets(project_id, scan_id)
        for record in target_records:
            notify_unvalidated_target(project_id, record)
    except Exception as e:
        error_handler.handleError(e)

def notify_unvalidated_target(project_id, record):
    arn = os.environ["UnValidatedTargetsArn"]
    message = {"target_record": record, "project_id": project_id}
    client = boto3.client('sns')
    return client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json')