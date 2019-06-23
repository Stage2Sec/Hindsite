import json
import boto3
import os
import error_handler
import database
import response_formatter

def lambda_handler(event, context):
    print(event)
    try:
        scanId = event['pathParameters']['scanId']
        results = database.getScanResults(scanId)

        return response_formatter.formatSuccessfulResponse(results)

    except Exception as e:
        error_handler.handleError(e)