import json
import boto3
import os
import error_handler
import database
import response_formatter

def lambda_handler(event, context):
    print(event)
    try:
        projectId = event['pathParameters']['projectId']
        scans = database.getProjectScans(projectId)

        return response_formatter.formatSuccessfulResponse(scans)

    except Exception as e:
        error_handler.handleError(e)