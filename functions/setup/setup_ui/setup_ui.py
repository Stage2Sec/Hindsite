import boto3
import json
from botocore.vendored import requests

def lambda_handler(event, context):
    print(event)
    try:
        ui_bucket_name = event['ResourceProperties']['UiBucketName']
        core_bucket_name = event['ResourceProperties']['CoreBucketName']
        if event['RequestType'] in ["Create","Update"]:
            deploy_static_ui(ui_bucket_name)
            deploy_default_scan_lists(core_bucket_name)
        elif event['RequestType'] == "Delete":
            empty_bucket(ui_bucket_name)
            empty_bucket(core_bucket_name)

    except Exception as e:
        print(e)
    finally:
        response_url = event['ResponseURL']
        response_body = dict()
        response_body['Status'] = "SUCCESS"
        response_body['Reason'] = ""
        response_body['PhysicalResourceId'] = 'NONE'
        response_body['StackId'] = event['StackId']
        response_body['RequestId'] = event['RequestId']
        response_body['LogicalResourceId'] = event['LogicalResourceId']
        json_response_body = json.dumps(response_body)
        print(json_response_body)

        headers = {
            'content-type': '',
            'content-length': str(len(json_response_body))
        }

        response = requests.put(response_url,
                                data=json_response_body,
                                headers=headers)

def deploy_static_ui(ui_bucket_name):
    s3 = boto3.client("s3")

    objects = []
    prefixes = [{'Prefix': "static/"}]
    while prefixes:
        objects,prefixes = list_prefixes(s3,prefixes,objects)

    for object in objects:
        s3.copy_object(
            ACL="public-read", Bucket=ui_bucket_name, Key=object["key"], CopySource=object["source"])

def deploy_default_scan_lists(core_bucket_name):
    s3 = boto3.client("s3")

    objects = []
    prefixes = [{'Prefix': "scan-lists/"}]
    while prefixes:
        objects, prefixes = list_prefixes(s3, prefixes, objects)

    for object in objects:
        s3.copy_object(
            ACL="public-read", Bucket=core_bucket_name, Key=object["key"], CopySource=object["source"])

def empty_bucket(ui_bucket_name):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(ui_bucket_name)
    bucket.objects.all().delete()


def list_prefixes(s3, prefixes, objects):
    additional_prefixes = []
    for prefix in prefixes:
        response = s3.list_objects_v2(
            Bucket="hindsite-code-repo",
            Prefix=prefix['Prefix'],
            Delimiter="/")
        if "Contents" in response:
            for source in response["Contents"]:
                object = {}
                object["source"] = '/'.join(["hindsite-code-repo", source["Key"]])
                object["key"] = source["Key"]
                objects.append(object)
        if "CommonPrefixes" in response:
            for prefix in response["CommonPrefixes"]:
                additional_prefixes.append(prefix)

    return objects,additional_prefixes