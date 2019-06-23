import boto3
import json
from botocore.vendored import requests

def lambda_handler(event, context):
    print(event)
    domain = ''
    try:
        if event['RequestType'] == "Create":
            domain_name = event['ResourceProperties']['DomainName']
            user_pool_id = event['ResourceProperties']['UserPoolId']
            client_id = event['ResourceProperties']['ClientId']
            endpoint_url = event['ResourceProperties']['EndpointUrl']
            domain = create_domain(domain_name,user_pool_id)
            update_client_settings(user_pool_id,client_id, endpoint_url)
        elif event['RequestType'] == "Update":
            old_domain_name = event['OldResourceProperties']['DomainName']
            old_user_pool_id = event['OldResourceProperties']['UserPoolId']
            domain_name = event['ResourceProperties']['DomainName']
            user_pool_id = event['ResourceProperties']['UserPoolId']
            client_id = event['ResourceProperties']['ClientId']
            endpoint_url = event['ResourceProperties']['EndpointUrl']
            delete_domain(old_domain_name,old_user_pool_id)
            domain = create_domain(domain_name, user_pool_id)
            update_client_settings(user_pool_id,client_id, endpoint_url)
        elif event['RequestType'] == "Delete":
            domain_name = event['ResourceProperties']['DomainName']
            user_pool_id = event['ResourceProperties']['UserPoolId']
            delete_domain(domain_name, user_pool_id)

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

def create_domain(domain,user_pool_id):
    client = boto3.client("cognito-idp")
    response = client.create_user_pool_domain(
        Domain=domain,
        UserPoolId=user_pool_id
    )

def delete_domain(old_domain_name,old_user_pool_id):
    client = boto3.client("cognito-idp")
    response = client.delete_user_pool_domain(
        Domain=old_domain_name,
        UserPoolId=old_user_pool_id
    )

def update_client_settings(user_pool_id,client_id, endpoint_url):
    client = boto3.client("cognito-idp")
    client.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        CallbackURLs=[endpoint_url + "/index.html"],
        LogoutURLs=[endpoint_url + "/logout.html"],
        SupportedIdentityProviders=["COGNITO"],
        AllowedOAuthFlows=["implicit"],
        AllowedOAuthScopes=["email","openid"],
        AllowedOAuthFlowsUserPoolClient=True
    )
