import json
import boto3
import os
import base64
import error_handler
import database

def lambda_handler(event, context):
    try:
        print(event)
        key = event['path'].split('/screenshot/')[1]
        url = get_signed_url(key)

        return {
            'statusCode': 200,
            'headers': {
                'Content-type': 'text/plain',
                'Access-Control-Allow-Origin': '*'
            },
            'body': url
        }

    except Exception as e:
        error_handler.handleError(e)

def get_signed_url(s3_key):
    s3Client = boto3.client('s3')
    url = s3Client.generate_presigned_url('get_object', Params={'Bucket': os.environ['CoreBucketRef'], 'Key': s3_key},
                                          ExpiresIn=100)
    print(url)

    return url
