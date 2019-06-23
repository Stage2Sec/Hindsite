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
        stats = database.getScanStats(projectId)

        return response_formatter.formatSuccessfulResponse(stats)

    except Exception as e:
        error_handler.handleError(e)