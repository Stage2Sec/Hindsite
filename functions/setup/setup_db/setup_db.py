import boto3
import json
from botocore.vendored import requests
from urllib.request import urlopen
import pymysql
import database

def lambda_handler(event, context):
    print(event)
    try:
        if event['RequestType'] == "Create":
            dbEndpoint = event['ResourceProperties']['DbEndpoint']
            dbSecret = event['ResourceProperties']['DbSecret']
            dbId = dbEndpoint.split('.')[0]
            enable_data_api(dbId )
            deploy_rds_schema(dbEndpoint, dbSecret)
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

def enable_data_api(dbId):
    client = boto3.client('rds')

    return client.modify_db_cluster(
        DBClusterIdentifier=dbId,
        EnableHttpEndpoint=True
    )

def deploy_rds_schema(dbEndpoint, dbSecret):
    data = urlopen('https://s3.us-east-2.amazonaws.com/hindsite-code-repo/schema/1.0/hs.sql', timeout=1).read()
    schema = parse_sql(data.decode('utf-8').split('\n'))
    for stmt in schema:
        database.executeQuery(stmt,resourceArn=dbEndpoint, secretArn=dbSecret)

def parse_sql(schema):
    stmts = []
    DELIMITER = ';'
    stmt = ''
    for line in schema:
        if not line.strip():
            continue
        if line.startswith('--'):
            continue
        if 'DELIMITER' in line:
            DELIMITER = line.split()[1]
            continue
        if (DELIMITER not in line):
            stmt += line.replace(DELIMITER, ';')
            continue
        if stmt:
            stmt += line
            stmts.append(stmt.strip())
            stmt = ''
        else:
            stmts.append(line.strip())
    return stmts
