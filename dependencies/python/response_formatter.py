import json

def formatSuccessfulResponse(data=None):

    return {
        "statusCode": 200,
        "body": json.dumps(data)
    }