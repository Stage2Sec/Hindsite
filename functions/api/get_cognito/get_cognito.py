import os
import error_handler
import database


def lambda_handler(event, context):
    print(event)
    try:
        cognito_params = {}
        cognito_params['userPoolId'] = os.environ['userPoolId']
        cognito_params['region'] = os.environ['region']
        cognito_params['userPoolWebClientId'] = os.environ['userPoolWebClientId']

        return cognito_params

    except Exception as e:
        error_handler.handleError(e)

